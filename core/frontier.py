"""
Calculations for the Efficient Frontier page. No Streamlit calls apart
from caching, so everything can be tested on its own.

Conventions (shown on the page so the numbers can be checked):
  * Month-end total return levels, cut at the last complete month.
  * Expected return = average monthly return x 12; risk = monthly
    standard deviation x sqrt(12). Both annualised, in %.
  * Long only, fully invested, optional cap on any one index.
  * "Best risk-adjusted mix" = highest Sharpe ratio, using the Nifty 1D
    Rate index over the same window as the risk-free rate (a flat 6.5%
    a year before that index starts in 2011).
  * A mix is held at fixed weights, rebalanced monthly, when it is
    tested on the years that follow.
"""

import numpy as np
import pandas as pd
import streamlit as st
from scipy.optimize import minimize

from core import fbi_metrics as fm

BENCHMARK = "NIFTY 500"
RF_INDEX = "NIFTY 1D RATE INDEX"
RF_FALLBACK = 6.5
FACTOR_SET = [
    "NIFTY500 GROWTH 50", "NIFTY500 VALUE 50", "NIFTY500 QUALITY 50",
    "NIFTY500 LOW VOLATILITY 50", "NIFTY500 MOMENTUM 50", "NIFTY500 EQUAL WEIGHT",
]
FRONTIER_POINTS = 40


# ---------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def monthly_returns(names):
    """Month-end returns (as fractions) for names + benchmark, plus the
    monthly risk-free return (NaN before the rate index starts)."""
    cols = list(dict.fromkeys(list(names) + [BENCHMARK]))
    lv = fm.levels_to_as_of(cols + [RF_INDEX])
    m = lv.resample("ME").last()
    rets = m.pct_change().iloc[1:]
    rf = rets.pop(RF_INDEX) if RF_INDEX in rets else pd.Series(np.nan, index=rets.index)
    # a month only counts once every asset has a return for it
    rets = rets[cols].dropna()
    return rets, rf.reindex(rets.index)


def window_end_options(rets, lookback_years, step_months=3):
    """Month-ends where a full look-back window fits, every step_months,
    always including the latest month."""
    n = int(lookback_years * 12)
    ends = list(rets.index[n - 1:])
    if not ends:
        return []
    last = ends[-1]
    picked = [d for d in ends if (last.year * 12 + last.month - d.year * 12 - d.month) % step_months == 0]
    return picked


# ---------------------------------------------------------------------
# Optimiser
# ---------------------------------------------------------------------

def moments(r):
    mu = r.mean().to_numpy() * 12
    cov = r.cov().to_numpy() * 12
    return mu, cov


def rf_rate(rf):
    """Annualised risk-free rate (fraction) for a window of monthly rf returns."""
    if rf.notna().all() and len(rf):
        return float((1 + rf).prod() ** (12 / len(rf)) - 1)
    return RF_FALLBACK / 100


def _solve(fun, n, cap, extra=()):
    cap = 1.0 if cap is None else max(cap, 1.0 / n + 1e-9)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}] + list(extra)
    best = None
    starts = [np.full(n, 1 / n)] + [np.eye(n)[i] * 0.5 + 0.5 / n for i in range(min(n, 3))]
    for w0 in starts:
        w0 = np.clip(w0, 0, cap)
        w0 = w0 / w0.sum()
        res = minimize(fun, w0, method="SLSQP", bounds=[(0, cap)] * n,
                       constraints=cons, options={"ftol": 1e-10, "maxiter": 400})
        if res.success and (best is None or res.fun < best.fun):
            best = res
    w = best.x if best is not None else np.full(n, 1 / n)
    return _clean(w, n)


def _clean(w, n):
    """Valid long-only weights summing to 1, or equal weights if the
    optimiser handed back NaN/inf or nothing usable."""
    w = np.asarray(w, dtype=float)
    if not np.all(np.isfinite(w)):
        return np.full(n, 1 / n)
    w = np.clip(w, 0, None)
    tot = w.sum()
    return w / tot if tot > 0 else np.full(n, 1 / n)


def _risk(w, cov):
    return float(np.sqrt(max(float(w @ cov @ w), 0.0)))


def min_vol(mu, cov, cap=None):
    return _solve(lambda w: w @ cov @ w, len(mu), cap)


def max_sharpe(mu, cov, rf, cap=None):
    def neg(w):
        v = _risk(w, cov)
        return -(w @ mu - rf) / v if v > 1e-12 else 0.0
    return _solve(neg, len(mu), cap)


def frontier(mu, cov, cap=None, points=FRONTIER_POINTS):
    """Efficient (upper) half of the long-only frontier: list of
    (risk %, return %, weights) from the min-vol mix to the highest
    reachable return."""
    n = len(mu)
    w_min = min_vol(mu, cov, cap)
    r_min = float(w_min @ mu)
    # highest return reachable under the cap: fill the best assets first
    c = 1.0 if cap is None else max(cap, 1.0 / n)
    left, r_max = 1.0, 0.0
    for i in np.argsort(-mu):
        take = min(c, left)
        r_max += take * mu[i]
        left -= take
        if left <= 1e-12:
            break
    out = [(_risk(w_min, cov) * 100, r_min * 100, w_min)]
    if r_max - r_min < 1e-6:
        return out
    prev = w_min
    for t in np.linspace(r_min, r_max, points)[1:]:
        cons = [{"type": "eq", "fun": lambda w, t=t: w @ mu - t}]
        w = _solve_from(lambda w: w @ cov @ w, prev, c, cons)
        if w is None:
            continue
        prev = w
        r_, v_ = float(w @ mu) * 100, _risk(w, cov) * 100
        if np.isfinite(r_) and np.isfinite(v_):
            out.append((v_, r_, w))
    return out


def _solve_from(fun, w0, cap, extra):
    n = len(w0)
    res = minimize(fun, w0, method="SLSQP", bounds=[(0, cap)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}] + list(extra),
                   options={"ftol": 1e-12, "maxiter": 400})
    if not res.success or not np.all(np.isfinite(res.x)):
        return None
    return _clean(res.x, n)


def random_cloud(mu, cov, n=1500, seed=7, cap=None):
    """Random long-only mixes, for a faint 'everything you could hold'
    backdrop. Mixes of concentrated and spread-out weights, kept within
    the cap so the cloud never shows mixes the frontier isn't allowed."""
    rng = np.random.default_rng(seed)
    k = len(mu)
    w = np.vstack([rng.dirichlet(np.full(k, a), n * 4) for a in (0.25, 1.0, 4.0)])
    if cap is not None:
        w = w[(w <= max(cap, 1 / k) + 1e-9).all(axis=1)]
    w = w[rng.permutation(len(w))[:n]]
    risk = np.sqrt(np.clip(np.einsum("ij,jk,ik->i", w, cov, w), 0, None)) * 100
    ret = w @ mu * 100
    df = pd.DataFrame({"risk": risk, "ret": ret})
    return df[np.isfinite(df["risk"]) & np.isfinite(df["ret"])]


# ---------------------------------------------------------------------
# One window
# ---------------------------------------------------------------------

def point_stats(r):
    """Annualised average return and risk (%) of each column."""
    return pd.DataFrame({"ret": r.mean() * 12 * 100, "risk": r.std() * np.sqrt(12) * 100})


def mix_returns(r, w):
    return pd.Series(r.to_numpy() @ w, index=r.index)


def realised(m, rf_m=None):
    """Summary of a monthly return series over a test period."""
    growth = (1 + m).cumprod()
    years = len(m) / 12
    cagr = (growth.iloc[-1] ** (1 / years) - 1) * 100
    vol = m.std() * np.sqrt(12) * 100
    level = pd.concat([pd.Series([1.0]), growth.reset_index(drop=True)])
    worst = (level / level.cummax() - 1).min() * 100
    rf = rf_rate(rf_m) * 100 if rf_m is not None else RF_FALLBACK
    return {
        "cagr": cagr, "vol": vol, "worst": worst,
        "sharpe": (cagr - rf) / vol if vol else np.nan,
        "avg": m.mean() * 12 * 100, "growth": growth,
    }


@st.cache_data(show_spinner=False, max_entries=200)
def analyse_window(names, start, end, fwd_years, cap):
    """Everything the page shows for one look-back window [start, end]
    and the fwd_years that follow it (as far as data goes)."""
    rets, rf = monthly_returns(names)
    names = list(names)
    win = rets.loc[start:end]
    asset = win[names]
    mu, cov = moments(asset)
    rf_ann = rf_rate(rf.loc[win.index])

    fr = frontier(mu, cov, cap)
    w_best = max_sharpe(mu, cov, rf_ann, cap)
    w_low = min_vol(mu, cov, cap)
    w_eq = np.full(len(names), 1 / len(names))

    pts = point_stats(win)
    def mix_pt(w):
        return float(w @ mu * 100), _risk(w, cov) * 100

    out = {
        "start": win.index[0], "end": win.index[-1], "months": len(win),
        "rf": rf_ann * 100,
        "frontier": pd.DataFrame([{"risk": a, "ret": b} for a, b, _ in fr]),
        "frontier_w": [w for *_, w in fr],
        "points": pts,
        "cloud": random_cloud(mu, cov, cap=cap),
        "weights": {"best": w_best, "low": w_low, "equal": w_eq},
        "mix": {k: mix_pt(w) for k, w in (("best", w_best), ("low", w_low), ("equal", w_eq))},
        "sharpe_in": {},
    }
    for k, w in out["weights"].items():
        r_, v_ = out["mix"][k]
        out["sharpe_in"][k] = (r_ - rf_ann * 100) / v_ if v_ else np.nan
    b = pts.loc[BENCHMARK]
    out["sharpe_in"]["bench"] = (b["ret"] - rf_ann * 100) / b["risk"]

    # the test: the fwd_years after the window
    after = rets.loc[rets.index > win.index[-1]].iloc[: int(fwd_years * 12)]
    out["fwd_months"] = len(after)
    out["fwd_full"] = len(after) >= int(fwd_years * 12)
    if len(after) >= 12:
        rf_after = rf.loc[after.index]
        rf_after = rf_after if rf_after.notna().all() else None
        out["fwd"] = {
            "best": realised(mix_returns(after[names], w_best), rf_after),
            "low": realised(mix_returns(after[names], w_low), rf_after),
            "equal": realised(mix_returns(after[names], w_eq), rf_after),
            "bench": realised(after[BENCHMARK], rf_after),
        }
        out["fwd_start"], out["fwd_end"] = after.index[0], after.index[-1]
        # where each mix actually landed, on the same axes as the frontier
        fa = after[names]
        out["landed"] = {k: (float(mix_returns(fa, w).mean() * 1200),
                             float(mix_returns(fa, w).std() * np.sqrt(12) * 100))
                         for k, w in out["weights"].items()}
        out["landed"]["bench"] = (float(after[BENCHMARK].mean() * 1200),
                                  float(after[BENCHMARK].std() * np.sqrt(12) * 100))
        if len(after) >= 24:
            mu2, cov2 = moments(fa)
            out["fwd_frontier"] = pd.DataFrame(
                [{"risk": a, "ret": b} for a, b, _ in frontier(mu2, cov2, cap, points=25)])
            out["fwd_points"] = point_stats(after)
    return out


# ---------------------------------------------------------------------
# Every window: how the mix moved, and whether it worked
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False, max_entries=60)
def track_record(names, lookback_years, fwd_years, cap):
    """For every quarterly window end: the best and lowest-risk mixes
    from the look-back, and (where the future is in the data) how they
    did over the next fwd_years against the Nifty 500 and an equal mix."""
    rets, rf = monthly_returns(names)
    names = list(names)
    n_back, n_fwd = int(lookback_years * 12), int(fwd_years * 12)
    weights, tests = [], []
    for end in window_end_options(rets, lookback_years):
        i = rets.index.get_loc(end)
        win = rets.iloc[i - n_back + 1: i + 1]
        mu, cov = moments(win[names])
        w_best = max_sharpe(mu, cov, rf_rate(rf.loc[win.index]), cap)
        w_low = min_vol(mu, cov, cap)
        weights.append({"end": end, **dict(zip(names, w_best))})
        after = rets.iloc[i + 1: i + 1 + n_fwd]
        if len(after) < n_fwd:
            continue
        rf_after = rf.loc[after.index]
        rf_after = rf_after if rf_after.notna().all() else None
        best = realised(mix_returns(after[names], w_best), rf_after)
        low = realised(mix_returns(after[names], w_low), rf_after)
        eq = realised(after[names].mean(axis=1), rf_after)
        bench = realised(after[BENCHMARK], rf_after)
        tests.append({
            "end": end,
            "best": best["cagr"], "low": low["cagr"], "equal": eq["cagr"], "bench": bench["cagr"],
            "best_sharpe": best["sharpe"], "low_sharpe": low["sharpe"],
            "equal_sharpe": eq["sharpe"], "bench_sharpe": bench["sharpe"],
            "best_vol": best["vol"], "low_vol": low["vol"], "bench_vol": bench["vol"],
        })
    w = pd.DataFrame(weights).set_index("end") if weights else pd.DataFrame()
    t = pd.DataFrame(tests).set_index("end") if tests else pd.DataFrame()
    return w, t
