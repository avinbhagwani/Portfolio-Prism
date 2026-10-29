"""
Calculations for the FBI Intelligence page.

Conventions, applied everywhere on the page so every number agrees:
  * Data is cut at the last complete month-end ("as-of date"), so no
    statistic includes a stray partial month.
  * Index levels are total return (dividends reinvested), in INR.
  * A comparison window only starts once every index being compared
    has data, so no figure mixes different time spans.
  * Upside/downside capture follows Morningstar: the ratio of
    annualised (not cumulative) returns in the benchmark's up and
    down months.
"""

import re

import pandas as pd
import streamlit as st

from core.index_data import load_catalogue, load_index_history

PERIODS = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10, "Max": None}

# Series that are not comparable with total-return equity indices:
# price-only variants, leveraged/inverse, futures, arbitrage, currency
# translated, and the dividend points accumulator.
_EXCLUDE_PATTERNS = [
    r"\bPR\b", "FUTURES", "LEVERAGE", "INVERSE", "ARBITRAGE",
    "DIVIDEND POINTS", r"\bUSD\b",
]

_KEEP_UPPER = {
    "IT", "PSU", "PSE", "CPSE", "FMCG", "MNC", "ESG", "EV", "SME", "REITS",
    "INVITS", "FPI", "MQVLV", "HTM", "SDL", "AAA", "G-SEC", "TR", "PR",
    "USD", "PSUS", "BFSI", "ETF", "IPO", "NBFC",
}


# ---------------------------------------------------------------------
# Names and universe
# ---------------------------------------------------------------------

def pretty_name(name):
    """'NIFTY200 MOMENTUM 30' -> 'Nifty200 Momentum 30' (NSE's own style)."""
    def fix(word):
        parts = word.split("-")
        out = []
        for p in parts:
            if p.upper() == "REITS":
                out.append("REITs")
            elif p.upper() == "INVITS":
                out.append("InvITs")
            elif p.upper() in _KEEP_UPPER or p.isdigit():
                out.append(p.upper())
            elif p.upper() == "&":
                out.append("&")
            else:
                out.append(p[:1].upper() + p[1:].lower())
        return "-".join(out)

    return " ".join(fix(w) for w in name.split())


@st.cache_data(show_spinner=False)
def equity_universe():
    """
    Catalogue rows for equity indices that are comparable on a total
    return basis, with a pretty display name.
    """
    cat = load_catalogue()
    cat = cat[cat["indexType"] == "Equity"].copy()
    pattern = "|".join(_EXCLUDE_PATTERNS)
    cat = cat[~cat["indexName"].str.contains(pattern, regex=True)]
    cat["display"] = cat["indexName"].map(pretty_name)
    return cat.sort_values("display").reset_index(drop=True)


def short_category(category):
    return category.replace(" Indices", "").replace(" Index", "")


# ---------------------------------------------------------------------
# Data window
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def as_of_date():
    """Last trading day of the last complete month in the data."""
    history = load_index_history()
    last = history.index.max()
    month_start = last.replace(day=1)
    # complete if the data reaches the month's last business day (a month
    # ending on a weekend used to be treated as unfinished and dropped)
    is_month_end = (last.normalize() + pd.offsets.BDay(1)).month != last.month
    cutoff = last if is_month_end else month_start - pd.Timedelta(days=1)
    return history.index[history.index <= cutoff].max()


def levels_to_as_of(names):
    """Daily levels for names, cut at the as-of date, non-positive -> NaN."""
    history = load_index_history()
    cols = [n for n in dict.fromkeys(names) if n in history.columns]
    levels = history.loc[:as_of_date(), cols]
    return levels.where(levels > 0)


def common_window(levels, years):
    """
    Slice levels to the trailing `years` (None = longest common history)
    such that every column has data at the start. Returns
    (window_levels, start_date, shortened) where shortened is True when
    the requested period was longer than the common history.
    """
    common_start = max(levels[c].first_valid_index() for c in levels.columns)
    end = levels.index.max()

    if years is None:
        start, shortened = common_start, False
    else:
        wanted = end - pd.DateOffset(years=years)
        start = max(wanted, common_start)
        shortened = start > wanted

    window = levels.ffill().loc[start:end]
    return window, window.index.min(), shortened


# ---------------------------------------------------------------------
# Core statistics
# ---------------------------------------------------------------------

def cagr(series):
    s = series.dropna()
    if len(s) < 2:
        return float("nan")
    years = (s.index[-1] - s.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100


def monthly_returns(levels):
    return levels.resample("ME").last().pct_change().iloc[1:]


def volatility(levels):
    m = monthly_returns(levels)
    return m.std() * (12 ** 0.5) * 100


def max_drawdown(series):
    s = series.dropna()
    return ((s / s.cummax()) - 1).min() * 100


def current_drawdown(series):
    s = series.dropna()
    return ((s / s.cummax()) - 1).iloc[-1] * 100


def worst_episode(series):
    """Peak, trough and recovery (None if not yet) of the deepest fall."""
    s = series.dropna()
    dd = s / s.cummax() - 1
    trough = dd.idxmin()
    peak = s.loc[:trough].idxmax()
    after = s.loc[trough:]
    recovered = after[after >= s.loc[peak]]
    recovery = recovered.index[0] if not recovered.empty else None
    return {
        "depth": dd.min() * 100,
        "peak": peak,
        "trough": trough,
        "recovery": recovery,
    }


def capture(levels, name, benchmark):
    """Morningstar upside/downside capture (%) of name vs benchmark."""
    m = monthly_returns(levels[[name, benchmark]]).dropna()
    up = m[m[benchmark] >= 0]
    down = m[m[benchmark] < 0]

    def ann(r):
        return (1 + r).prod() ** (12 / len(r)) - 1 if len(r) else float("nan")

    def ratio(part):
        if len(part) == 0:
            return float("nan")
        b = ann(part[benchmark])
        return ann(part[name]) / b * 100 if b else float("nan")

    return ratio(up), ratio(down), len(up), len(down)


def stats_table(window, names, benchmark):
    rows = {}
    for n in names:
        up, down, *_ = (
            capture(window, n, benchmark) if n != benchmark
            else (100.0, 100.0, 0, 0)
        )
        rows[n] = {
            "Annual return": cagr(window[n]),
            "Volatility": volatility(window[[n]]).iloc[0],
            "Worst fall": max_drawdown(window[n]),
            "Upside capture": up,
            "Downside capture": down,
        }
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Rolling and calendar
# ---------------------------------------------------------------------

def rolling_cagr(levels, window_years):
    monthly = levels.resample("ME").last()
    months = int(window_years * 12)
    out = ((monthly / monthly.shift(months)) ** (1 / window_years) - 1) * 100
    return out.dropna(how="all")


def hit_rate(rolling, a, b):
    paired = rolling[[a, b]].dropna()
    if paired.empty:
        return None
    diff = paired[a] - paired[b]
    return {
        "pct": (diff > 0).mean() * 100,
        "median": diff.median(),
        "n": len(diff),
        "since": paired.index[0],
    }


HIT_WINDOWS = (1, 3, 5, 7)


def strategy_names():
    """Comparable (total return) strategy indices, in display order."""
    u = equity_universe()
    return u.loc[u["indexCategory"] == "Strategy Indices", "indexName"].tolist()


# Parent index each strategy index is built from, matched on name prefix
# (longest first). Indices whose universe has no index of its own here
# (Alpha 50, High Beta 50, Low Volatility 50, Quality Low-Volatility 30,
# etc. draw from the top ~150-300 stocks) fall back to the Nifty 500.
PARENT_PREFIXES = [
    ("NIFTY MIDSMALLCAP400", "NIFTY MIDSMALLCAP 400"),
    ("NIFTY SMALLCAP250", "NIFTY SMALLCAP 250"),
    ("NIFTY MIDCAP150", "NIFTY MIDCAP 150"),
    ("NIFTY TOTAL MARKET", "NIFTY TOTAL MARKET"),
    ("NIFTY500", "NIFTY 500"),
    ("NIFTY200", "NIFTY 200"),
    ("NIFTY100", "NIFTY 100"),
    ("NIFTY50", "NIFTY 50"),
    ("NIFTY TOP ", "NIFTY 50"),
]
PARENT_ORDER = ["NIFTY 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
                "NIFTY TOTAL MARKET", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250",
                "NIFTY MIDSMALLCAP 400"]
OTHER_PARENT = "NIFTY 500"


def parent_index(name):
    """(parent benchmark, True if matched by name rather than fallback)."""
    for prefix, parent in PARENT_PREFIXES:
        if name.startswith(prefix):
            return parent, True
    return OTHER_PARENT, False


def hit_ratio_groups(years=None):
    """
    One hit-ratio table per parent index, each strategy index measured
    only against the index it is built from. Returns a list of dicts:
    bench, other (True for the fallback group), table, start, counts.
    """
    groups = {}
    for n in strategy_names():
        parent, matched = parent_index(n)
        groups.setdefault((parent, not matched), []).append(n)
    keys = sorted(groups, key=lambda k: (k[1], PARENT_ORDER.index(k[0])))
    out = []
    for parent, other in keys:
        table, start, counts = hit_ratio_table(tuple(groups[(parent, other)]),
                                               parent, years)
        out.append(dict(bench=parent, other=other, table=table,
                        start=start, counts=counts))
    return out


@st.cache_data(show_spinner=False)
def hit_ratio_table(names, benchmark, years=None, windows=HIT_WINDOWS):
    """
    Share of rolling periods (%) in which each index's annualised return
    beat the benchmark's, for each rolling window in `windows`.

    Every index is measured from the same start: the earliest month-end
    by which all of `names` and the benchmark have data. `years` keeps
    only rolling periods ending in the last `years` years (None = all).

    Returns (table, start, counts): table has one row per index and one
    column per window; counts gives the number of rolling periods behind
    each column (identical for every row, by construction).
    """
    levels = levels_to_as_of(list(names) + [benchmark])
    start = max(levels[c].first_valid_index() for c in levels.columns)
    monthly = levels.ffill().loc[start:].resample("ME").last()
    end = monthly.index.max()
    cutoff = end - pd.DateOffset(years=years) if years else None

    table, counts = {}, {}
    for w in windows:
        roll = ((monthly / monthly.shift(w * 12)) ** (1 / w) - 1).dropna(how="all")
        if cutoff is not None:
            roll = roll[roll.index > cutoff]
        counts[w] = len(roll)
        col = f"{w}Y"
        if roll.empty:
            table[col] = pd.Series(float("nan"), index=list(names))
            continue
        beat = roll[list(names)].gt(roll[benchmark], axis=0)
        table[col] = beat.mean() * 100
    return pd.DataFrame(table), start, counts


def calendar_returns(levels):
    """Calendar-year returns (%); the last year is flagged partial."""
    year_end = levels.resample("YE").last()
    first_valid = levels.apply(lambda s: s.first_valid_index())
    rets = year_end.pct_change() * 100
    # a year only counts for an index if it existed at the prior year-end
    for col in rets.columns:
        start_year = first_valid[col].year
        rets.loc[rets.index.year <= start_year, col] = float("nan")
    rets.index = rets.index.year
    rets = rets.dropna(how="all")
    as_of = levels.index.max()
    partial_year = as_of.year if as_of.month != 12 else None
    return rets, partial_year


# ---------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------

def period_phrase(years, start, shortened):
    if years is None or shortened:
        return f"since {start:%b %Y}"
    return "over the last year" if years == 1 else f"over the last {years} years"


def fmt_pct(x, signed=False, decimals=1):
    if pd.isna(x):
        return "n/a"
    s = f"{x:+.{decimals}f}%" if signed else f"{x:.{decimals}f}%"
    return s.replace("-", "−")


def fmt_pts(x):
    return f"{abs(x):.1f} points"


def fmt_rupees(x):
    if x >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    return f"₹{x / 1e5:.1f}L"


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def strip_category_word(name):
    return re.sub(r"\s+", " ", name).strip()
