"""
Index data for every tool that works with NSE indices.

Primary source: BigQuery table mutual-funds-data.mutual_fund_data.index_tri
(daily FinAPI Total Return Index values, refreshed every trading day).
    index_name, index_type, index_category, tri_date, tri, basis
basis is 'TRI' for equity indices and 'Index value' for fixed income /
multi asset, whose published value already follows a total-return method.

Fallback / top-up: the two FinAPI files shipped in data/
  data/finapi_index_catalogue.csv      indexName, displayName, indexType, indexCategory
  data/finapi_all_indices_history.csv  wide daily levels, one column per index
The CSV is used (a) for the few indices BigQuery doesn't carry (NIFTY50
leveraged/inverse, NIFTY 50 ARBITRAGE, NIFTY50 USD, DIVIDEND POINTS, ...)
and (b) for everything if BigQuery can't be reached, so the site never
breaks because of the warehouse. Both sources hold identical values on
overlapping dates.

Callers see one shape whatever the source: load_catalogue() returns the
catalogue frame and load_index_history() a wide frame indexed by Date,
one column per indexName. Sparse: most indices only have data from their
launch date onward, so NaNs before that are expected.

Both frames are held once per server process and shared read-only.
Callers must not modify them in place.

Loading never blocks a page: the app starts on the bundled CSV, and a
background thread (start_background_refresh, called from app.py) pulls
BigQuery and swaps it in when it succeeds, then refreshes every
REFRESH_HOURS (retrying every 30 min after a failure). Each swap clears
st.cache_data, because many derived results (hit ratios, game payloads,
frontier inputs) are cached without a TTL and would otherwise keep serving
the old numbers.

Configuration (environment variables, all optional):
  PRISM_INDEX_SOURCE     "bigquery" (default) or "csv" to skip BigQuery
  PRISM_BQ_TABLE         fully-qualified table, default below
  PRISM_BQ_PROJECT       project that runs and pays for the query job;
                         default = the project Cloud Run runs in
"""

import logging
import os
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOGUE_PATH = DATA_DIR / "finapi_index_catalogue.csv"
HISTORY_PATH = DATA_DIR / "finapi_all_indices_history.csv"

BQ_TABLE = os.environ.get("PRISM_BQ_TABLE",
                          "mutual-funds-data.mutual_fund_data.index_tri")
REFRESH_HOURS = 12
BQ_TIMEOUT_S = 120

_CAT_COLS = ["indexName", "displayName", "indexType", "indexCategory"]


# ---------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------

def _read_csv_sources():
    cat = pd.read_csv(CATALOGUE_PATH)
    hist = pd.read_csv(HISTORY_PATH, index_col=0, parse_dates=True)
    return cat, hist


def _fetch_bigquery():
    """Long frame from BigQuery: index_name, index_type, index_category, tri_date, tri."""
    from google.cloud import bigquery  # imported lazily: CSV-only runs don't need it

    project = os.environ.get("PRISM_BQ_PROJECT") or None
    client = bigquery.Client(project=project)
    sql = f"""
        SELECT index_name, index_type, index_category, tri_date, tri
        FROM `{BQ_TABLE}`
        WHERE tri > 0
    """
    job = client.query(sql, timeout=BQ_TIMEOUT_S)
    job.result(timeout=BQ_TIMEOUT_S)
    try:
        # fast path: BigQuery Storage Read API (needs bigquery.readsessions.create)
        return job.to_dataframe()
    except Exception as e:  # no Storage API permission -> plain REST paging
        log.warning("BigQuery Storage API unavailable (%s); using REST download", e)
        return job.to_dataframe(create_bqstorage_client=False)


def _combine(bq_long, csv_cat, csv_hist):
    """BigQuery for every index it has; CSV for the ones it doesn't."""
    bq_long = bq_long.copy()
    bq_long["tri_date"] = pd.to_datetime(bq_long["tri_date"])
    hist = (bq_long.pivot_table(index="tri_date", columns="index_name",
                                values="tri", aggfunc="last")
                   .astype("float64"))
    hist.index.name = "Date"
    hist.columns.name = None

    cat = (bq_long.drop_duplicates("index_name", keep="last")
                  .rename(columns={"index_name": "indexName",
                                   "index_type": "indexType",
                                   "index_category": "indexCategory"}))
    cat["displayName"] = cat["indexName"]
    cat = cat[_CAT_COLS]

    extra = [c for c in csv_hist.columns if c not in hist.columns]
    if extra:
        hist = hist.join(csv_hist[extra], how="outer")
        cat = pd.concat([cat, csv_cat[csv_cat["indexName"].isin(extra)][_CAT_COLS]],
                        ignore_index=True)
    return cat.reset_index(drop=True), hist.sort_index()


_lock = threading.Lock()
_state = None            # (catalogue, history, source, loaded_at)
_worker = None


def _set_state(cat, hist, source):
    global _state
    _state = (cat, hist.sort_index(), source, time.time())


def _current():
    """Current data; the bundled CSV until a BigQuery load has succeeded."""
    if _state is None:
        with _lock:
            if _state is None:
                cat, hist = _read_csv_sources()
                _set_state(cat, hist, "csv")
    return _state


def _try_bigquery():
    """One BigQuery load attempt; swaps the data in only if it succeeds."""
    try:
        t0 = time.time()
        csv_cat, csv_hist = _read_csv_sources()
        cat, hist = _combine(_fetch_bigquery(), csv_cat, csv_hist)
    except Exception as e:
        log.warning("BigQuery index load failed, keeping %s data: %r",
                    _current()[2], e)
        return False
    _set_state(cat, hist, "bigquery")
    st.cache_data.clear()   # derived results were built from the old data
    log.warning("Index data from BigQuery: %d indices to %s in %.1fs",
                hist.shape[1], hist.index.max().date(), time.time() - t0)
    return True


def _refresh_loop():
    while True:
        ok = _try_bigquery()
        # success: refresh every REFRESH_HOURS; failure: retry in 30 min
        time.sleep(REFRESH_HOURS * 3600 if ok else 1800)


def start_background_refresh():
    """
    Called from app.py on every run; never blocks. Pages always render from
    the data already in memory (bundled CSV at first); a daemon thread pulls
    BigQuery in the background and swaps it in when, and only if, it succeeds.
    """
    global _worker
    _current()
    if os.environ.get("PRISM_INDEX_SOURCE", "bigquery").lower() == "csv":
        return
    if _worker is None:
        with _lock:
            if _worker is None:
                _worker = threading.Thread(target=_refresh_loop, daemon=True,
                                           name="prism-bq-refresh")
                _worker.start()


def data_source():
    """'bigquery' or 'csv' — where the current index data came from."""
    return _current()[2]


def load_catalogue():
    """One row per index: indexName, displayName, indexType, indexCategory."""
    return _current()[0]


def load_index_history():
    """Daily levels for every index, wide format, indexed by Date."""
    return _current()[1]


def list_index_types():
    return sorted(load_catalogue()["indexType"].dropna().unique())


def list_categories(index_type=None):
    cat = load_catalogue()
    if index_type:
        cat = cat[cat["indexType"] == index_type]
    return sorted(cat["indexCategory"].dropna().unique())


def list_indices(index_type=None, category=None):
    """Index names (as used in the history file) matching the given filters."""
    cat = load_catalogue()

    if index_type:
        cat = cat[cat["indexType"] == index_type]
    if category:
        cat = cat[cat["indexCategory"] == category]

    return sorted(cat["indexName"].unique())


def get_index_levels(index_names, start_date=None, end_date=None):
    """
    Daily level series for the requested indices, restricted to rows
    where at least one selected index has data (drops the fully-empty
    pre-launch tail/head).

    Non-positive values are treated as missing rather than real levels
    — a handful of "points" style series (e.g. NIFTY50 DIVIDEND POINTS)
    legitimately hit zero, which is fine as a dividend accumulator but
    breaks every return/volatility/drawdown calculation downstream
    (division by zero, -100% "returns", etc). Masking them to NaN here
    means every caller gets protected for free instead of each one
    needing its own guard.
    """
    if not index_names:
        return pd.DataFrame()

    history = load_index_history()
    missing = [name for name in index_names if name not in history.columns]
    if missing:
        return pd.DataFrame()

    levels = history[index_names].copy()
    levels = levels.where(levels > 0)

    if start_date is not None:
        levels = levels[levels.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        levels = levels[levels.index <= pd.Timestamp(end_date)]

    return levels.dropna(how="all")


def get_index_returns(index_names, start_date=None, end_date=None, freq="ME"):
    """
    Period returns (%) for the requested indices, resampled to the given
    frequency ('D' daily, 'ME' month-end, 'W' weekly) before differencing,
    so indices with different history lengths still line up on a common
    calendar. Returns an empty frame if none of the indices have any
    overlapping data.
    """
    levels = get_index_levels(index_names, start_date, end_date)

    if levels.empty:
        return pd.DataFrame()

    if freq != "D":
        levels = levels.resample(freq).last()

    returns = levels.pct_change().dropna(how="all") * 100
    return returns
