"""
Data for the "Can You Handle It?" game.

The player picks an index (from the FinAPI history) or a mutual fund (NAV
from mfapi.in). We find the worst market peaks in that history, the moments
just before the deepest falls, and hand the browser:

  levels     closing levels on every week's last trading day, plus the
             exact days money goes in: each peak, and the first trading
             day of every month (when a SIP is paid), so purchases happen
             at the real price of that day, not a later weekly close
  scenarios  the deepest drawdown episodes: peak, trough, recovery
  cash       what the same money would have earned in cash, on the same
             weeks: RBI's repo rate until 2011, then NSE's Nifty 1D Rate
             index (the overnight rate), so the rate is the one of the time

Everything else (investing at the peak, the monthly SIP, XIRR, the
"sell" button) is simulated in the browser so playback is smooth.
"""

import json

import pandas as pd
import streamlit as st

from core import fbi_metrics as fm
from core.data import fetch_fund_history
from core.index_analytics import find_drawdown_episodes

MIN_DEPTH = -15        # only falls at least this deep (%) make a scenario
MAX_SCENARIOS = 4

# RBI repo rate changes (date, % a year) used for cash before the Nifty 1D
# Rate index starts in January 2011. Source: RBI policy announcements.
REPO = [
    ("1995-01-01", 9.0), ("2000-11-06", 10.0), ("2001-03-09", 9.0), ("2001-04-30", 8.75),
    ("2001-06-07", 8.5), ("2002-03-28", 8.0), ("2002-11-12", 7.5), ("2003-03-07", 7.1),
    ("2003-03-19", 7.0), ("2004-03-31", 6.0), ("2005-10-26", 6.25), ("2006-01-24", 6.5),
    ("2006-07-25", 7.0), ("2006-10-30", 7.25), ("2007-01-31", 7.5), ("2007-03-30", 7.75),
    ("2008-06-12", 8.0), ("2008-06-25", 8.5), ("2008-07-30", 9.0), ("2008-10-20", 8.0),
    ("2008-11-03", 7.5), ("2008-12-08", 6.5), ("2009-01-05", 5.5), ("2009-03-05", 5.0),
    ("2009-04-21", 4.75), ("2010-03-19", 5.0), ("2010-04-20", 5.25), ("2010-07-02", 5.5),
    ("2010-07-27", 5.75), ("2010-09-16", 6.0), ("2010-11-02", 6.25),
]
CASH_INDEX = "NIFTY 1D RATE INDEX"

PRESETS = [
    "NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY MICROCAP 250",
    "NIFTY200 MOMENTUM 30", "NIFTY500 VALUE 50",
]


def _clean(daily):
    s = daily.dropna()
    return s[s > 0].sort_index()


def _sample(daily, extra_days=()):
    """Week-end closes, plus the first trading day of each month and any
    extra days (the peaks), all at their real closing levels."""
    s = _clean(daily)
    days = s.index.to_series()
    week_ends = days.resample("W-FRI").last().dropna()
    month_starts = days.resample("MS").first().dropna()
    keep = pd.DatetimeIndex(week_ends.values).union(pd.DatetimeIndex(month_starts.values))
    keep = keep.union(pd.DatetimeIndex([d for d in extra_days if d in s.index]))
    return s.loc[keep]


def _scenarios(daily):
    allx = [e for e in find_drawdown_episodes(daily.to_frame("x"), "x", top_n=50)
            if e["depth_pct"] <= MIN_DEPTH]
    eps = allx[:MAX_SCENARIOS]
    latest = max(allx, key=lambda e: e["peak_date"], default=None)
    if latest is not None and latest not in eps:
        eps.append(latest)            # the most recent fall is the one people remember
    eps.sort(key=lambda e: e["peak_date"])
    out = []
    for e in eps:
        rec = e["recovery_date"]
        out.append({
            "peak": f"{e['peak_date']:%Y-%m-%d}",
            "trough": f"{e['trough_date']:%Y-%m-%d}",
            "recovery": f"{rec:%Y-%m-%d}" if rec is not None else None,
            "depth": round(float(e["depth_pct"]), 1),
        })
    return out


def _series_points(weekly):
    return [[f"{d:%Y-%m-%d}", float(f"{v:.6g}")] for d, v in weekly.items()]


@st.cache_data(show_spinner=False)
def cash_daily():
    """A daily 'cash' level: repo-rate accrual until the 1D Rate index
    starts, then that index, joined so the line is continuous."""
    from core.index_data import load_index_history
    one_d = load_index_history()[CASH_INDEX].dropna()
    days = pd.date_range("1995-01-01", one_d.index[0], freq="D")
    rate = pd.Series({pd.Timestamp(d): r for d, r in REPO}).reindex(days, method="ffill")
    early = (1 + rate / 100 / 365).cumprod()
    early = early / early.iloc[-1] * one_d.iloc[0]
    return pd.concat([early.iloc[:-1], one_d]).sort_index()


@st.cache_data(show_spinner=False)
def index_daily(name):
    return fm.levels_to_as_of([name])[name].dropna()


def fund_daily(code):
    df = fetch_fund_history(code)
    if df.empty:
        return pd.Series(dtype=float)
    return df.set_index("date")["nav"].astype(float)


@st.cache_data(show_spinner=False, ttl=3600)
def payload(kind, key, label):
    """kind 'index' (key = index name) or 'fund' (key = scheme code)."""
    daily = index_daily(key) if kind == "index" else fund_daily(key)
    if kind == "fund" and daily.empty:
        # a failed download: raise so the miss isn't cached, and the next try refetches
        raise LookupError(f"Couldn't load NAV history for scheme {key}")
    if daily.empty or len(daily) < 300:
        return None
    daily = _clean(daily)
    scenarios = _scenarios(daily)
    weekly = _sample(daily, [pd.Timestamp(x["peak"]) for x in scenarios])
    data = {
        "name": label,
        "kind": kind,
        "levels": _series_points(weekly),
        "scenarios": scenarios,
        "asOf": f"{daily.index.max():%d %b %Y}",
    }
    cash = cash_daily()
    cash_w = cash.reindex(cash.index.union(weekly.index)).interpolate("time").reindex(weekly.index).ffill().bfill()
    data["cash"] = [float(f"{v:.8g}") for v in cash_w.values]
    return json.dumps(data, separators=(",", ":"))
