"""
Live examples for the page tutorials (views/tutorial.py).

Each function computes the numbers a tutorial shows with the same code
the pages use, so the lessons stay current as data updates. Nothing here
raises: a failure returns a clearly flagged fallback (fund example) or
None (index examples), and the tutorial words itself around that.

  fund_example()       HDFC Flexi Cap (the fund from the PRISM launch post
                       on my Substack): six-factor fit plus 3-year rolling
                       value and momentum exposures
  fbi_example()        Nifty200 Momentum 30 vs Nifty 200, full history
  drawdown_example()   Nifty Smallcap 250 and Nifty 50, worst falls
  frontier_example()   how often the best past mix beat the Nifty 500
                       over the next five years
"""

import pandas as pd
import streamlit as st

from core.config import FACTOR_LABELS

FUND_QUERY = "hdfc flexi cap"
FUND_MODEL = "ff6"
JAIN_EXIT = pd.Timestamp("2022-06-30")   # Prashant Jain left HDFC AMC in mid-2022


# ---------------------------------------------------------------------
# Factor Analysis: HDFC Flexi Cap
# ---------------------------------------------------------------------

def _pick_plan(matches):
    """The Direct Plan, Growth option, if mfapi lists one."""
    def score(m):
        n = m["name"].lower()
        return (("direct" in n) * 2 + ("growth" in n)
                - 5 * any(w in n for w in ("idcw", "dividend", "bonus", "payout")))
    return max(matches, key=score) if matches else None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _fund_example():
    from core.analysis import fit, rolling
    from core.data import fetch_fund_history, get_monthly_returns, month_end_dates, search_funds

    fund = _pick_plan(search_funds(FUND_QUERY))
    if fund is None:
        raise LookupError("fund not found")
    dates = month_end_dates(fetch_fund_history(fund["code"]))
    if len(dates) < 48:
        raise LookupError("not enough history")
    res = fit(get_monthly_returns(fund["code"], dates[0], dates[-1]), FUND_MODEL)
    if res is None:
        raise LookupError("regression failed")
    m, factors = res["model"], res["factors"]

    rows = []
    for f in factors:
        c, se = float(m.params[f]), float(m.bse[f])
        rows.append({"key": f, "label": FACTOR_LABELS[f], "coef": c, "se": se,
                     "lo": c - 1.96 * se, "hi": c + 1.96 * se, "p": float(m.pvalues[f])})

    path, windows, specs = {}, {}, {}
    for label, months in (("1Y", 12), ("3Y", 36), ("5Y", 60)):
        roll = rolling(res["data"], tuple(factors), months)
        if roll is None or roll.empty:
            continue
        s = roll["HML"].dropna()
        from core.tutorial_charts import rolling_spec
        specs[label] = rolling_spec(roll, "HML", "Value")
        windows[label] = [(d.strftime("%Y-%m-%d"), float(v), float(roll.loc[d, "HML_P"])) for d, v in s.items()]
        if label == "3Y":
            at_exit = s.loc[:JAIN_EXIT]
            path["HML"] = {
                "series": windows[label],
                "first": (s.index[0], float(s.iloc[0])),
                "exit": (at_exit.index[-1], float(at_exit.iloc[-1])) if not at_exit.empty else None,
                "last": (s.index[-1], float(s.iloc[-1])),
                "peak": (s.idxmax(), float(s.max())),
            }
    a, a_se = float(m.params["const"]), float(m.bse["const"])

    return {
        "example": False,
        "name": fund["name"].split(" - ")[0].strip(),
        "plan": fund["name"],
        "start": res["data"].index.min(), "end": res["data"].index.max(),
        "months": len(res["data"]),
        "r2": float(m.rsquared) * 100,
        "beta": float(m.params["MKT_RF"]),
        "alpha": a * 12, "alpha_p": float(m.pvalues["const"]),
        "alpha_lo": (a - 1.96 * a_se) * 12, "alpha_hi": (a + 1.96 * a_se) * 12,
        "alpha_se": a_se,
        "factors": rows,
        "rolling": path,
        "windows": windows,
        "roll_specs": {k: v for k, v in specs.items() if v},
    }


def _fund_fallback():
    """Shown only if the live data can't be loaded. Illustrative numbers,
    flagged as such on every slide that uses them."""
    def row(k, c, half, p):
        return {"key": k, "label": FACTOR_LABELS[k], "coef": c, "se": half / 1.96,
                "lo": c - half, "hi": c + half, "p": p}
    s = pd.date_range("2016-01-31", "2026-08-31", freq="ME")
    hml = [0.45 - 0.35 * max(0, (d - JAIN_EXIT).days) / 1500 for d in s]
    return {
        "example": True,
        "name": "HDFC Flexi Cap Fund", "plan": "HDFC Flexi Cap Fund (illustrative numbers)",
        "start": pd.Timestamp("2013-01-31"), "end": pd.Timestamp("2026-08-31"), "months": 163,
        "r2": 90.0, "beta": 0.92, "alpha": 1.1, "alpha_p": 0.40,
        "alpha_lo": -1.5, "alpha_hi": 3.7, "alpha_se": 0.11,
        "factors": [row("MKT_RF", 0.92, 0.06, 0.0001), row("SMB", -0.05, 0.10, 0.40),
                    row("HML", 0.32, 0.12, 0.0001), row("RMW", 0.02, 0.15, 0.80),
                    row("CMA", 0.06, 0.15, 0.45), row("WML", -0.14, 0.09, 0.004)],
        "rolling": {"HML": {
            "series": [(d.strftime("%Y-%m-%d"), v, 0.01 if v > 0.2 else 0.3) for d, v in zip(s, hml)],
            "first": (s[0], hml[0]), "exit": (JAIN_EXIT, 0.45), "last": (s[-1], hml[-1]),
            "peak": (s[0], hml[0])}},
        "windows": {"3Y": [(d.strftime("%Y-%m-%d"), v, 0.01 if v > 0.2 else 0.3) for d, v in zip(s, hml)]},
    }


def fund_example():
    try:
        return _fund_example()
    except Exception:
        return _fund_fallback()


# ---------------------------------------------------------------------
# Index pages (local index history, so these rarely fail)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _fbi_example():
    from core import fbi_metrics as fm
    a, b = "NIFTY200 MOMENTUM 30", "NIFTY 200"
    levels = fm.levels_to_as_of([a, b])
    window, start, _ = fm.common_window(levels, None)
    hit = fm.hit_rate(fm.rolling_cagr(window, 3), a, b)
    hits = {}
    for yrs in (1, 3, 5, 7):
        h = fm.hit_rate(fm.rolling_cagr(window, yrs), a, b)
        if h:
            hits[yrs] = float(h["pct"])
    up, down, *_ = fm.capture(window, a, b)
    ep = {n: fm.worst_episode(window[n]) for n in (a, b)}
    return {
        "a": fm.pretty_name(a), "b": fm.pretty_name(b), "start": start, "end": window.index.max(),
        "cagr": {"a": fm.cagr(window[a]), "b": fm.cagr(window[b])},
        "worst": {"a": ep[a], "b": ep[b]},
        "hit3": hit, "hits": hits, "up": up, "down": down,
    }


@st.cache_data(show_spinner=False)
def _drawdown_example():
    from core import fbi_metrics as fm
    out = {}
    for n in ("NIFTY SMALLCAP 250", "NIFTY 50"):
        s = fm.levels_to_as_of([n])[n].dropna()
        out[n] = {"name": fm.pretty_name(n), **fm.worst_episode(s)}
    return out


@st.cache_data(show_spinner=False)
def _frontier_example():
    from core import frontier as F
    _, t = F.track_record(tuple(F.FACTOR_SET), 5, 5, (None, None))
    if t.empty:
        return None
    return {
        "n": len(t),
        "beat_bench": float((t["best"] > t["bench"]).mean() * 100),
        "beat_equal": float((t["best"] > t["equal"]).mean() * 100),
        "first": t.index.min(), "last": t.index.max(),
    }


@st.cache_data(show_spinner=False)
def _quilt_example(years=8):
    """Real calendar-year ranking of the five Nifty 500 factor indices."""
    from core import fbi_metrics as fm
    names = ["NIFTY500 MOMENTUM 50", "NIFTY500 VALUE 50", "NIFTY500 QUALITY 50",
             "NIFTY500 LOW VOLATILITY 50", "NIFTY500 GROWTH 50"]
    rets, partial = fm.calendar_returns(fm.levels_to_as_of(names))
    rets = rets.loc[[y for y in rets.index if y != partial]].dropna().tail(years)
    short = {n: fm.pretty_name(n).replace("Nifty500 ", "").replace(" 50", "") for n in names}
    cols = []
    for y, row in rets.iterrows():
        ranked = row.sort_values(ascending=False)
        cols.append({"year": int(y), "ranked": [{"name": short[n], "ret": float(v)} for n, v in ranked.items()]})
    return {"names": [short[n] for n in names], "years": cols}


def quilt_example():
    return _safe(_quilt_example)


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def fbi_example():
    return _safe(_fbi_example)


def drawdown_example():
    return _safe(_drawdown_example)


def frontier_example():
    return _safe(_frontier_example)
