"""
FBI Intelligence (Factor-Based Index Intelligence).

Built around one question a visitor arrives with: "how has this index
behaved, against the market and against the alternative I'm weighing?"

  Controls (top, shared by every tab): index, optional second index,
  benchmark, period.

  Overview    headline, five key numbers, growth of Rs 1 lakh
  Returns     rolling returns with hit rate, calendar years
  Risk        drawdowns with the worst episode, upside/downside capture
  Market map  every index in a category by risk and return, and the
              year-by-year quilt

Each chart leads with one sentence computed from the data, so the page
says what it shows instead of only labelling it.
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from charts import fbi_charts as fc
from charts.render import show_figure
from core import fbi_metrics as fm
from charts.quilt_chart import build_quilt_color_map, make_quilt_chart
from core.index_analytics import build_quilt

DEFAULT_A = "NIFTY200 MOMENTUM 30"
DEFAULT_B = "NIFTY500 VALUE 50"
DEFAULT_BENCH = "NIFTY 500"
BENCH_CHOICES = [
    "NIFTY 500", "NIFTY 50", "NIFTY 100", "NIFTY 200",
    "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY TOTAL MARKET",
]
NONE = "None"

QUILT_PRESETS = {
    "Factors, Nifty 500": [
        "NIFTY500 MOMENTUM 50", "NIFTY500 VALUE 50", "NIFTY500 QUALITY 50",
        "NIFTY500 LOW VOLATILITY 50", "NIFTY500 EQUAL WEIGHT", "NIFTY 500",
    ],
    "Factors, Nifty 200": [
        "NIFTY200 MOMENTUM 30", "NIFTY200 VALUE 30", "NIFTY200 QUALITY 30",
        "NIFTY100 LOW VOLATILITY 30", "NIFTY200 ALPHA 30", "NIFTY 200",
    ],
    "Size": [
        "NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250",
        "NIFTY MICROCAP 250", "NIFTY 500",
    ],
    "Custom": None,
}

CSS = """
<style>
.fbi-sub {color:#6B7480; font-size:0.95rem; margin:-0.6rem 0 1.4rem 0;}
.fbi-headline {font-size:1.22rem; line-height:1.5; font-weight:500;
  color:#1B2533; margin:0.4rem 0 0.2rem 0; max-width:52rem;}
.fbi-label {font-size:0.8rem; color:#6B7480; font-weight:500;
  margin:1.6rem 0 0.1rem 0; letter-spacing:0.01em;}
.fbi-note {font-size:0.82rem; color:#8A939E; margin-top:0.2rem;}
table.fbi-stats {border-collapse:collapse; width:100%; margin:1rem 0 0.4rem 0;
  font-size:0.92rem; border:none !important;}
table.fbi-stats th, table.fbi-stats td {border-left:none !important;
  border-right:none !important; border-top:none !important;}
table.fbi-stats th {font-weight:500; color:#6B7480; text-align:right;
  padding:0.45rem 0.6rem; border-bottom:1px solid #E3E7EC;}
table.fbi-stats th:first-child, table.fbi-stats td:first-child {text-align:left;}
table.fbi-stats td {padding:0.55rem 0.6rem; text-align:right;
  border-bottom:1px solid #F0F2F5; font-variant-numeric:tabular-nums;}
table.fbi-stats td:first-child {color:#6B7480;}
.dot {display:inline-block; width:0.6rem; height:0.6rem; border-radius:50%;
  margin-right:0.4rem; vertical-align:0.05rem;}
div[data-testid="stTabs"] button p {font-size:0.95rem;}
</style>
"""


# =====================================================================
# PAGE
# =====================================================================

def render():
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("FBI Intelligence")
    st.markdown(
        "<p class='fbi-sub'>Factor-based index intelligence. Compare Nifty "
        "factor and strategy indices on return, risk and consistency.</p>",
        unsafe_allow_html=True,
    )

    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    display = dict(zip(universe["indexName"], universe["display"]))

    c1, c2, c3, c4 = st.columns([2.6, 2.6, 1.9, 2.9], vertical_alignment="bottom")
    with c1:
        a = st.selectbox("Index", names, index=names.index(DEFAULT_A),
                         format_func=display.get, key="fbi_a")
    with c2:
        b_opts = [NONE] + names
        b = st.selectbox("Compare with", b_opts,
                         index=b_opts.index(DEFAULT_B),
                         format_func=lambda n: display.get(n, n), key="fbi_b")
    with c3:
        bench = st.selectbox("Benchmark", BENCH_CHOICES,
                             format_func=display.get, key="fbi_bench")
    with c4:
        period = st.segmented_control("Period", list(fm.PERIODS),
                                      default="5Y", key="fbi_period")
    period = period or "5Y"
    years = fm.PERIODS[period]

    picks = [a] + ([b] if b != NONE and b != a else [])
    picks = [p for p in picks if p != bench]
    if not picks:
        st.info(f"{display[a]} is also the benchmark. Pick a different "
                "index or benchmark to compare.")
        return
    names_all = list(dict.fromkeys(picks + [bench]))

    levels = fm.levels_to_as_of(names_all)
    as_of = levels.index.max()
    window, start, shortened = fm.common_window(levels, years)
    phrase = fm.period_phrase(years, start, shortened)

    ctx = dict(levels=levels, window=window, start=start, shortened=shortened,
               phrase=phrase, picks=picks, bench=bench, names=names_all,
               as_of=as_of, years=years, period=period)

    st.write("")
    t1, t2, t3, t4 = st.tabs(["Overview", "Returns", "Risk", "Market map"])
    with t1:
        _overview(ctx)
    with t2:
        _returns(ctx)
    with t3:
        _risk(ctx)
    with t4:
        _market_map(ctx, universe)


def _headline(text):
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _label(text):
    st.markdown(f"<p class='fbi-label'>{text}</p>", unsafe_allow_html=True)


def _note(text):
    st.markdown(f"<p class='fbi-note'>{text}</p>", unsafe_allow_html=True)


def _show(fig):
    show_figure(fig)
    plt.close(fig)


def _n(name):
    return fm.pretty_name(name)


def _color(ctx, name):
    if name == ctx["bench"]:
        return fc.COLOR_BENCH
    return fc.SERIES_COLORS[ctx["picks"].index(name)]


def _shortened_note(ctx):
    if ctx["shortened"]:
        late = max(ctx["names"], key=lambda n: ctx["levels"][n].first_valid_index())
        _note(f"Shown since {ctx['start']:%b %Y}, when {_n(late)} history begins.")


# =====================================================================
# OVERVIEW
# =====================================================================

def _overview(ctx):
    w, picks, bench = ctx["window"], ctx["picks"], ctx["bench"]
    stats = fm.stats_table(w, ctx["names"], bench)
    r = stats.loc["Annual return"]
    dd = stats.loc["Worst fall"]
    a = picks[0]
    phrase = ctx["phrase"][0].upper() + ctx["phrase"][1:]

    if len(picks) == 1:
        diff = r[a] - r[bench]
        better = diff >= 0
        deeper = dd[a] < dd[bench] - 1
        shallower = dd[a] > dd[bench] + 1
        text = (f"{phrase}, {_n(a)} returned {fm.fmt_pct(r[a])} a year, "
                f"{fm.fmt_pts(diff)} {'more' if better else 'less'} than the "
                f"{_n(bench)}")
        if deeper or shallower:
            joiner = "but" if better == deeper else "and"
            text += (f", {joiner} fell {'further' if deeper else 'less'} at its "
                     f"worst ({fm.fmt_pct(dd[a], decimals=0)} against "
                     f"{fm.fmt_pct(dd[bench], decimals=0)})")
        text += "."
    else:
        b = picks[1]
        lead, lag = (a, b) if r[a] >= r[b] else (b, a)
        beat = [p for p in picks if r[p] > r[bench]]
        text = (f"{phrase}, {_n(lead)} returned {fm.fmt_pct(r[lead])} a year "
                f"against {fm.fmt_pct(r[lag])} for {_n(lag)}")
        if len(beat) == 2:
            text += f". Both beat the {_n(bench)} ({fm.fmt_pct(r[bench])})."
        elif len(beat) == 1:
            text += (f", which trailed the {_n(bench)} "
                     f"({fm.fmt_pct(r[bench])}).")
        else:
            text += f". Neither beat the {_n(bench)} ({fm.fmt_pct(r[bench])})."
    _headline(text)
    _shortened_note(ctx)

    _stats_html(ctx, stats)

    _label("Growth of ₹1 lakh")
    _show(fc.growth_chart(w, ctx["names"], bench, ctx["as_of"]))


def _stats_html(ctx, stats):
    cols = ctx["names"]
    head = "".join(
        f"<th><span class='dot' style='background:{_color(ctx, n)}'></span>{_n(n)}</th>"
        for n in cols
    )
    rows = []
    fmt = {
        "Annual return": lambda v: fm.fmt_pct(v),
        "Volatility": lambda v: fm.fmt_pct(v),
        "Worst fall": lambda v: fm.fmt_pct(v),
        "Upside capture": lambda v: f"{v:.0f}%",
        "Downside capture": lambda v: f"{v:.0f}%",
    }
    for metric in stats.index:
        cells = "".join(f"<td>{fmt[metric](stats.loc[metric, n])}</td>" for n in cols)
        rows.append(f"<tr><td>{metric}</td>{cells}</tr>")
    st.markdown(
        f"<table class='fbi-stats'><tr><th></th>{head}</tr>{''.join(rows)}</table>",
        unsafe_allow_html=True,
    )
    _note("Annual return is compound (CAGR). Capture compares each month the "
          f"{_n(ctx['bench'])} rose or fell; above 100% upside and below 100% "
          "downside are better.")


# =====================================================================
# RETURNS
# =====================================================================

def _returns(ctx):
    levels, picks, bench = ctx["levels"], ctx["picks"], ctx["bench"]

    win_label = st.segmented_control("Rolling window", ["1Y", "3Y", "5Y"],
                                     default="3Y", key="fbi_roll")
    win = {"1Y": 1, "3Y": 3, "5Y": 5}[win_label or "3Y"]
    common = levels.loc[max(levels[c].first_valid_index() for c in levels.columns):]
    rolling = fm.rolling_cagr(common, win).dropna()

    if rolling.empty:
        _headline(f"Not enough shared history for {win}-year rolling returns.")
    else:
        hr = {p: fm.hit_rate(rolling, p, bench) for p in picks}
        a = picks[0]
        med = hr[a]["median"]
        text = (f"{_n(a)} beat the {_n(bench)} in {hr[a]['pct']:.0f}% of rolling "
                f"{win}-year periods since {hr[a]['since']:%Y}, "
                f"{'leading' if med >= 0 else 'trailing'} by a median of "
                f"{abs(med):.1f} points a year.")
        if len(picks) == 2:
            b = picks[1]
            vs = fm.hit_rate(rolling, a, b)
            text += (f" {_n(b)} did so {hr[b]['pct']:.0f}% of the time. Against "
                     f"each other, {_n(a)} led in {vs['pct']:.0f}% of periods.")
        _headline(text)
        _label(f"Rolling {win}-year return, annualised")
        _show(fc.rolling_chart(rolling, ctx["names"], bench, ctx["as_of"]))
        _note("Consecutive rolling periods overlap heavily, so read these "
              "percentages as a guide rather than proof.")

    cal, partial = fm.calendar_returns(common)
    full = cal[cal.index != partial]
    if ctx["years"]:
        full = full.tail(max(ctx["years"], 5))
    shown = cal.loc[full.index.min():]
    a = picks[0]
    wins = int((full[a] > full[bench]).sum())
    st.write("")
    _headline(f"{_n(a)} beat the {_n(bench)} in {wins} of the last "
              f"{len(full)} calendar years.")
    _label("Calendar-year return")
    _show(fc.calendar_chart(shown, ctx["names"], bench, partial, ctx["as_of"]))


# =====================================================================
# RISK
# =====================================================================

def _risk(ctx):
    w, picks, bench = ctx["window"], ctx["picks"], ctx["bench"]
    a = picks[0]
    ep = fm.worst_episode(w[a])
    text = (f"{_n(a)}'s worst fall {ctx['phrase']} was "
            f"{fm.fmt_pct(ep['depth'], decimals=0)}, from {ep['peak']:%b %Y} to "
            f"{ep['trough']:%b %Y}. ")
    if ep["recovery"] is not None:
        text += (f"It took {fm.months_between(ep['trough'], ep['recovery'])} "
                 f"months to get back to its old high.")
    else:
        cur = fm.current_drawdown(w[a])
        text += f"It has not recovered yet and is {abs(cur):.0f}% below that peak."
    _headline(text)
    _shortened_note(ctx)
    _label("Fall from previous high")
    _show(fc.drawdown_chart(w, ctx["names"], bench, ctx["as_of"]))

    pts = []
    for p in picks:
        up, down, n_up, n_down = fm.capture(w, p, bench)
        pts.append((p, down, up, _color(ctx, p)))
    name, down, up, _ = pts[0]
    text = (f"{_n(name)} captured {up:.0f}% of the {_n(bench)}'s gains and "
            f"{down:.0f}% of its losses.")
    if len(pts) == 2:
        n2, d2, u2, _ = pts[1]
        text += f" {_n(n2)}: {u2:.0f}% of gains, {d2:.0f}% of losses."
    st.write("")
    _headline(text)
    _label(f"Upside and downside capture against the {_n(bench)}")
    _show(fc.capture_chart(pts, bench, ctx["as_of"]))


# =====================================================================
# MARKET MAP
# =====================================================================

def _market_map(ctx, universe):
    view = st.segmented_control("View", ["Risk and return", "Year by year"],
                                default="Risk and return", key="fbi_map_view")
    if (view or "Risk and return") == "Risk and return":
        _scatter(ctx, universe)
    else:
        _quilt(ctx, universe)


def _scatter(ctx, universe):
    cats = sorted(universe["indexCategory"].unique())
    col, _ = st.columns([1, 2])
    with col:
        cat = st.selectbox("Category", cats, index=cats.index("Strategy Indices"),
                           format_func=fm.short_category, key="fbi_map_cat")
    bench, years = ctx["bench"], ctx["years"]
    members = universe.loc[universe["indexCategory"] == cat, "indexName"].tolist()
    names = list(dict.fromkeys(members + [bench] + ctx["picks"]))
    levels = fm.levels_to_as_of(names)
    as_of = levels.index.max()
    start = (as_of - pd.DateOffset(years=years)) if years else pd.Timestamp("2005-04-01")
    start = levels.index[levels.index >= start].min()

    rows = {}
    for n in names:
        s = levels[n]
        if s.first_valid_index() is None or s.first_valid_index() > start:
            continue
        seg = s.loc[start:].ffill()
        rows[n] = {"Return": fm.cagr(seg),
                   "Volatility": fm.volatility(seg.to_frame()).iloc[0]}
    pts = pd.DataFrame(rows).T
    if bench not in pts.index or len(pts) < 3:
        _headline("Not enough indices with the full history for this period.")
        return
    in_cat = [n for n in members if n in pts.index and n != bench]
    b = pts.loc[bench]
    beat = [n for n in in_cat if pts.loc[n, "Return"] > b["Return"]]
    calmer = [n for n in beat if pts.loc[n, "Volatility"] < b["Volatility"]]
    phrase = ("since Apr 2005" if years is None else fm.period_phrase(years, start, False))
    _headline(f"{len(beat)} of {len(in_cat)} {fm.short_category(cat).lower()} "
              f"indices beat the {_n(bench)} {phrase}; {len(calmer)} of them "
              f"did it with less volatility.")
    top = pts.loc[in_cat].sort_values("Return", ascending=False).index[:3].tolist()
    fig = fc.risk_return_chart(pts, bench, ctx["picks"], top, as_of)
    _label("Annualised return against volatility")
    _show(fig)
    missing = len([n for n in members if n not in pts.index])
    if missing:
        _note(f"{missing} newer indices without the full history are left out.")


def _quilt(ctx, universe):
    preset = st.segmented_control("Set", list(QUILT_PRESETS),
                                  default="Factors, Nifty 500", key="fbi_quilt_set")
    preset = preset or "Factors, Nifty 500"
    if QUILT_PRESETS[preset] is None:
        names = universe["indexName"].tolist()
        default = list(dict.fromkeys(ctx["picks"] + [ctx["bench"]]))
        chosen = st.multiselect("Indices (up to 7)", names, default=default,
                                max_selections=7, format_func=fm.pretty_name,
                                key="fbi_quilt_custom")
    else:
        chosen = QUILT_PRESETS[preset]
    if len(chosen) < 2:
        _headline("Pick at least two indices.")
        return

    levels = fm.levels_to_as_of(chosen)
    cal, partial = fm.calendar_returns(levels)
    last_full = [y for y in cal.index if y != partial][-10:]
    cols = last_full + ([partial] if partial else [])
    quilt = build_quilt(cal.loc[cols])
    leaders = quilt.iloc[0][[c for c in quilt.columns if c != partial]]
    unique = len({cell[0] for cell in leaders if cell})
    _headline(f"Leadership keeps changing: {unique} different indices topped "
              f"the table in the last {len(last_full)} years.")
    title_prefix = "Asset Allocation Quilt" if preset == "Custom" else preset
    with plt.rc_context({"font.family": "DejaVu Sans", "text.color": "black"}):
        fig = make_quilt_chart(
            quilt, build_quilt_color_map(chosen),
            title=f"{title_prefix} ({cols[0]}\u2013{cols[-1]})",
        )
    _show(fig)
    if partial:
        _note(f"{partial} is a partial year: the return shown is year to date, "
              f"to {levels.index.max():%d %b %Y}.")
