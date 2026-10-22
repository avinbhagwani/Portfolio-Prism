"""
Data for the "Try to Time" game.

Five Nifty 500 factor indices (total return) compete every calendar year.
Before each year the player sees only what was knowable at the previous
year-end, and picks the index they think will finish first:

  last year     calendar-year return and rank
  3 / 5 years   annual return (CAGR), risk (annualised volatility of
                monthly returns) and worst fall (max drawdown on
                month-end levels) over the trailing window
  times #1      how often each index has topped a full year so far

Windows that reach back before the data starts (April 2005) are cut to
the available history and flagged, so nothing uses future data. The game
itself runs in the browser; this module just packs the numbers as JSON.
"""

import json
import math

import numpy as np
import pandas as pd
import streamlit as st

from core import fbi_metrics as fm

CONTESTANTS = [
    # key, index name, short label, colour
    ("mom", "NIFTY500 MOMENTUM 50", "Momentum", "#2F6FB0"),
    ("val", "NIFTY500 VALUE 50", "Value", "#C08A2E"),
    ("qual", "NIFTY500 QUALITY 50", "Quality", "#5E9A62"),
    ("lowvol", "NIFTY500 LOW VOLATILITY 50", "Low Vol", "#2F8F9D"),
    ("growth", "NIFTY500 GROWTH 50", "Growth", "#8E5B9F"),
]
MARKET = ("mkt", "NIFTY 500", "Nifty 500", "#A3ABB5")

FIRST_ROUND = 2008      # first year the player picks (2005-2007 are shown)
QUICK_FIRST_ROUND = 2016


def _r(x, nd=1):
    return None if x is None or not math.isfinite(x) else round(float(x), nd)


def _window_stats(monthly, end, years, data_start):
    """CAGR, volatility and max drawdown (all %) for the `years` ending at
    `end` (a year-end). Cut to the data start if needed."""
    start = pd.Timestamp(year=end.year - years, month=12, day=31)
    truncated = start < data_start
    if truncated:
        start = data_start
    w = monthly.loc[start:end].dropna()
    if len(w) < 13:
        return None
    span = (w.index[-1] - w.index[0]).days / 365.25
    cagr = (w.iloc[-1] / w.iloc[0]) ** (1 / span) - 1
    vol = w.pct_change().dropna().std() * math.sqrt(12)
    dd = (w / w.cummax() - 1).min()
    return {"c": _r(cagr * 100), "v": _r(vol * 100), "d": _r(dd * 100),
            "cut": bool(truncated)}


@st.cache_data(show_spinner=False)
def game_payload():
    """Everything the browser game needs, as a JSON string."""
    entries = CONTESTANTS + [MARKET]
    names = [e[1] for e in entries]
    daily = fm.levels_to_as_of(names)
    # common start: every contestant has data from here
    data_start = max(daily[n].first_valid_index() for n in names)
    daily = daily.loc[data_start:]
    monthly = daily.resample("ME").last()
    monthly.iloc[0] = daily.iloc[0]          # anchor at the very first day
    monthly.index = monthly.index.where(monthly.index != monthly.index[0], data_start)

    year_end = daily.resample("YE").last()
    last_full = year_end.index[-1].year - (0 if daily.index.max().month == 12
                                           and daily.index.max().day >= 28 else 1)
    years = list(range(data_start.year, last_full + 1))

    returns = {}
    for key, name, *_ in entries:
        out = []
        for y in years:
            prev = daily[name].iloc[0] if y == data_start.year else \
                year_end[name][year_end.index.year == y - 1].iloc[0]
            cur = year_end[name][year_end.index.year == y].iloc[0]
            out.append(_r((cur / prev - 1) * 100))
        returns[key] = out

    rounds = {}
    for y in range(FIRST_ROUND, last_full + 1):
        end = pd.Timestamp(year=y - 1, month=12, day=31)
        info = {}
        for key, name, *_ in entries:
            s3 = _window_stats(monthly[name], end, 3, data_start)
            s5 = _window_stats(monthly[name], end, 5, data_start)
            if s5 and s3 and s5["cut"] and s3["cut"]:
                s5 = None                    # same as the 3-year view; don't repeat it
            info[key] = {"y3": s3, "y5": s5}
        rounds[str(y)] = info

    payload = {
        "indices": [{"key": k, "name": fm.pretty_name(n), "short": s, "color": c}
                    for k, n, s, c in CONTESTANTS],
        "market": {"key": MARKET[0], "name": fm.pretty_name(MARKET[1]),
                   "short": MARKET[2], "color": MARKET[3]},
        "years": years,
        "partialFirst": f"{data_start:%b}–Dec {data_start.year}"
        if data_start.month != 1 else None,
        "dataStart": f"{data_start:%b %Y}",
        "returns": returns,
        "rounds": rounds,
        "firstRound": FIRST_ROUND,
        "quickFirstRound": QUICK_FIRST_ROUND,
        "lastYear": last_full,
    }
    return json.dumps(payload, separators=(",", ":"))
