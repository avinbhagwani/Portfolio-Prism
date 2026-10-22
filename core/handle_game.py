"""
Data for the "Can You Handle It?" game.

The player picks an index (from the FinAPI history) or a mutual fund (NAV
from mfapi.in). We find the worst market peaks in that history, the moments
just before the deepest falls, and hand the browser:

  levels     weekly closing levels (Friday, or the last trading day)
  scenarios  the deepest drawdown episodes: peak, trough, recovery
  compare    an optional second series (an index) on the same weeks

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

PRESETS = [
    "NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY MICROCAP 250",
    "NIFTY200 MOMENTUM 30", "NIFTY500 VALUE 50",
]


def _weekly(daily):
    s = daily.dropna()
    s = s[s > 0]
    w = s.resample("W-FRI").last().dropna()
    # stamp each week with its real last trading day, not the Friday
    last_day = s.index.to_series().resample("W-FRI").last().dropna()
    w.index = pd.DatetimeIndex(last_day.loc[w.index].values)
    return w


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
def index_daily(name):
    return fm.levels_to_as_of([name])[name].dropna()


def fund_daily(code):
    df = fetch_fund_history(code)
    if df.empty:
        return pd.Series(dtype=float)
    return df.set_index("date")["nav"].astype(float)


@st.cache_data(show_spinner=False, ttl=3600)
def payload(kind, key, label, compare_name=None):
    """kind 'index' (key = index name) or 'fund' (key = scheme code)."""
    daily = index_daily(key) if kind == "index" else fund_daily(key)
    if daily.empty or len(daily) < 300:
        return None
    weekly = _weekly(daily)
    data = {
        "name": label,
        "kind": kind,
        "levels": _series_points(weekly),
        "scenarios": _scenarios(daily),
        "asOf": f"{daily.index.max():%d %b %Y}",
        "compare": None,
    }
    if compare_name:
        cmp_daily = index_daily(compare_name)
        cmp_weekly = _weekly(cmp_daily).reindex(weekly.index, method="ffill")
        cmp_weekly = cmp_weekly.where(cmp_weekly.index >= cmp_daily.index.min())
        data["compare"] = {
            "name": fm.pretty_name(compare_name),
            "levels": [None if pd.isna(v) else float(f"{v:.6g}") for v in cmp_weekly.values],
        }
    return json.dumps(data, separators=(",", ":"))
