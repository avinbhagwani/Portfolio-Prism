"""
Real PRISM charts for the page tours.

Every chart here is built with the same chart functions and arguments the
pages use (charts/factor_vega.py, charts/fbi_vega.py,
charts/frontier_vega.py, charts/quilt_chart.py), so the tours show the
tool's own chart style. Vega-Lite charts are returned as specs (rendered
in the tour by the vendored vega-embed); the quilt, a matplotlib figure
on the page, is returned as a base64 PNG.

Each function returns None if its data can't be built, and the tour
words itself around a missing chart.
"""

import base64
import math

import pandas as pd
import streamlit as st

TOUR_HEIGHT = 290        # charts are drawn a little shorter to fit a slide


def _clean(x):
    """NaN/inf -> None, and tall charts trimmed to fit a slide."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _spec(chart, height=TOUR_HEIGHT, label_room=0):
    """label_room: extra right padding so line-end labels fit the slide's
    narrower column (on the page the column is wider)."""
    spec = _clean(chart.to_dict())
    if isinstance(spec.get("height"), (int, float)) and spec["height"] > height:
        spec["height"] = height
    if label_room:
        spec["padding"] = {"left": 5, "top": 5, "bottom": 5, "right": label_room}
    return spec


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Factor Analysis (same rows and calls as views/factor_analysis.py)
# ---------------------------------------------------------------------

def exposure_rows(terms):
    """terms: list of (label, coef, se, p) -> rows for exposure_chart."""
    from core.regression_stats import significance_stars, significance_text
    return [{"label": lab, "coef": c, "lo": c - 1.96 * se, "hi": c + 1.96 * se, "sig": p < 0.05,
             "stars": significance_stars(p), "sig_text": significance_text(p)}
            for lab, c, se, p in terms]


def exposure_spec(terms, height=TOUR_HEIGHT):
    from charts import factor_vega as fvc
    return _safe(lambda: _spec(fvc.exposure_chart(exposure_rows(terms)), height))


def rolling_spec(rdf, col, label):
    from charts import factor_vega as fvc
    return _safe(lambda: _spec(fvc.rolling_chart(rdf, [(col, label)])))


# ---------------------------------------------------------------------
# FBI Intelligence and Drawdown (same calls as the pages)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _fbi_specs(a, bench):
    from charts import fbi_vega as fv
    from core import fbi_metrics as fm
    names = [a, bench]
    levels = fm.levels_to_as_of(names)
    window, start, _ = fm.common_window(levels, None)
    out = {"growth": _spec(fv.growth_chart(window, names, bench), label_room=70)}
    monthly = window.resample("ME").last()
    common = monthly.loc[monthly.notna().all(axis=1).idxmax():]
    roll3 = fm.rolling_cagr(common, 3).dropna()
    out["rolling"] = _spec(fv.rolling_chart(roll3, names, bench), label_room=70)
    out["drawdown"] = _spec(fv.drawdown_chart(window, names, bench), label_room=70)
    up, down, *_ = fm.capture(window, a, bench)
    out["capture"] = _spec(fv.capture_chart([(a, down, up, fv.SERIES_COLORS[0])], bench))
    out["hit_gap"] = _spec(fv.hit_gap_chart(roll3, a, bench, 3))
    return out


def fbi_specs(a="NIFTY200 MOMENTUM 30", bench="NIFTY 200"):
    return _safe(_fbi_specs, a, bench) or {}


@st.cache_data(show_spinner=False)
def _drawdown_spec(names):
    from charts import fbi_vega as fv
    from core import fbi_metrics as fm
    levels = fm.levels_to_as_of(list(names))
    window, _, _ = fm.common_window(levels, None)
    return _spec(fv.drawdown_chart(window, list(names), "", end_labels=True), label_room=70)


def drawdown_spec(names=("NIFTY SMALLCAP 250", "NIFTY 50")):
    return _safe(_drawdown_spec, tuple(names))


@st.cache_data(show_spinner=False)
def _quilt_png(names, title):
    import matplotlib.pyplot as plt
    from charts.quilt_chart import build_quilt_color_map, make_quilt_chart
    from charts.render import _to_png
    from core import fbi_metrics as fm
    from core.index_analytics import build_quilt
    levels = fm.levels_to_as_of(list(names))
    cal, partial = fm.calendar_returns(levels)
    last_full = [y for y in cal.index if y != partial][-8:]
    quilt = build_quilt(cal.loc[last_full])
    with plt.rc_context({"font.family": "DejaVu Sans", "text.color": "black"}):
        fig = make_quilt_chart(quilt, build_quilt_color_map(list(names)),
                               title=f"{title} ({last_full[0]}–{last_full[-1]})")
    try:
        png, _ = _to_png(fig, 160)
    finally:
        plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(png).decode()


def quilt_png():
    """The page's 'Factors, Nifty 500' quilt preset, last eight full years."""
    from views.factor_indexes import QUILT_PRESETS
    return _safe(_quilt_png, tuple(QUILT_PRESETS["Factors, Nifty 500"]), "Factors, Nifty 500")


# ---------------------------------------------------------------------
# Efficient Frontier (same calls as views/efficient_frontier.py defaults)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _frontier_specs():
    from charts import frontier_vega as fc
    from core import fbi_metrics as fm
    from core import frontier as F
    from views.efficient_frontier import _label, _weight_text_fn
    universe = fm.equity_universe()["indexName"].tolist()
    names = [n for n in F.FACTOR_SET if n in universe]
    names_t = tuple(names)
    rets, _ = F.monthly_returns(names_t)
    end = rets.index[-1]
    start = rets.index[-60]
    o = F.analyse_window(names_t, start, end, 5, (None, None))
    xd, yd = fc.shared_domains(o, names, False)
    out = {"frontier": _spec(fc.frontier_chart(o, names, _label, _weight_text_fn(names), xd, yd), 265),
           "span": f"{o['start']:%b %Y} to {o['end']:%b %Y}"}
    _, t = F.track_record(names_t, 5, 5, (None, None))
    if not t.empty:
        out["track"] = _spec(fc.track_chart(t, t.index[-1]), 250)
    return out


def frontier_specs():
    return _safe(_frontier_specs) or {}
