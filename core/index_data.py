"""
Loads the two FinAPI index data files shipped in data/:

  data/finapi_index_catalogue.csv
      One row per index: indexName, displayName, indexType
      (Equity / Fixed Income / Multi Asset), indexCategory (Broad Market,
      Sectoral, Strategy, Thematic, Target Maturity, etc).

  data/finapi_all_indices_history.csv
      Daily index levels, wide format: one Date column + one column per
      index (column name == catalogue's indexName). Sparse — most indices
      only have data from their launch date onward, so NaNs before that
      are expected, not a data error.

Both are cached with st.cache_data since they're read from disk on every
call otherwise. Swap the file paths here if you move to a live feed later
— nothing outside this module needs to know where the data comes from.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOGUE_PATH = DATA_DIR / "finapi_index_catalogue.csv"
HISTORY_PATH = DATA_DIR / "finapi_all_indices_history.csv"


@st.cache_data(ttl=3600, show_spinner=False)
def load_catalogue():
    """One row per index: indexName, displayName, indexType, indexCategory."""
    return pd.read_csv(CATALOGUE_PATH)


@st.cache_data(ttl=3600, show_spinner=False)
def load_index_history():
    """Daily levels for every index, wide format, indexed by Date."""
    df = pd.read_csv(HISTORY_PATH, index_col=0, parse_dates=True)
    return df.sort_index()


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


def get_index_returns(index_names, start_date=None, end_date=None, freq="M"):
    """
    Period returns (%) for the requested indices, resampled to the given
    frequency ('D' daily, 'M' month-end, 'W' weekly) before differencing,
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
