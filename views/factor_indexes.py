"""
FBI Intelligence (Factor-Based Index Intelligence).

Built around one question a visitor arrives with: "how has this index
behaved, against the market and against the alternative I'm weighing?"

  Controls card (shared by every tab): index, compare with, benchmark,
  period.

  Overview    headline finding, one number card per index, growth of
              Rs 1 lakh
  Returns     rolling returns with hit rate, calendar years
  Risk        drawdowns with the worst episode, upside/downside capture
  Hit ratio   share of rolling 1/3/5/7-year periods each strategy index
              beat its own parent index (Nifty200 X vs Nifty 200, etc.)
  Market map  every index in a category by risk and return, and the
              year-by-year quilt (original quilt style, by request)

Charts are interactive Vega-Lite (hover for exact values). Each one
leads with a sentence computed from the data.
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from charts import fbi_vega as fv
from charts.quilt_chart import build_quilt_color_map, make_quilt_chart
from charts.render import show_chart
from core import fbi_metrics as fm
from core.index_analytics import build_quilt

DEFAULT_A = "NIFTY200 MOMENTUM 30"
DEFAULT_B = "NIFTY500 VALUE 50"
BENCH_CHOICES = [
    "NIFTY 500", "NIFTY 50", "NIFTY 100", "NIFTY 200",
    "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY TOTAL MARKET",
]
NONE = "None"

QUILT_PRESETS = {
    "Factors, Nifty 500": [
        "NIFTY500 MOMENTUM 50", "NIFTY500 VALUE 50", "NIFTY500 QUALITY 50",
        "NIFTY500 LOW VOLATILITY 50", "NIFTY500 GROWTH 50",
        "NIFTY500 EQUAL WEIGHT", "NIFTY 500",
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
.kpi-row {display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
  gap:16px; margin:1.4rem 0 0.6rem 0;}
.kpi {border-radius:14px; padding:18px 20px 18px 20px; background:#F4F6F9;}
.kpi-name {font-size:0.9rem; color:#1B2533; font-weight:500; margin-bottom:10px;}
.kpi-big {font-size:2.3rem; font-weight:600; color:#1B2533; line-height:1.05;
  font-variant-numeric:tabular-nums; letter-spacing:-0.02em;}
.kpi-big span {font-size:0.9rem; font-weight:400; color:#8A939E; margin-left:6px;
  letter-spacing:0;}
.kpi-delta {font-size:0.86rem; font-weight:500; margin:6px 0 14px 0;}
.kpi-delta.pos {color:#1F4E79;} .kpi-delta.neg {color:#B54A3C;}
.kpi-delta.flat {color:#8A939E;}
.kpi-meta {display:flex; gap:22px; border-top:1px solid #E3E8EE; padding-top:12px;}
.kpi-meta b {display:block; font-size:0.98rem; font-weight:600; color:#1B2533;
  font-variant-numeric:tabular-nums;}
.kpi-meta small {font-size:0.76rem; color:#8A939E;}

</style>
"""


# =====================================================================
# PAGE
# =====================================================================

def render():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='fbi-eyebrow'>FBI Intelligence</div>"
        "<div class='fbi-title'>How has a factor index really behaved?</div>"
        "<div class='fbi-sub'>Compare Nifty factor and strategy indices against "
        "the market and each other: return, risk and how consistent they "
        "have been.</div>",
        unsafe_allow_html=True,
    )

    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    display = dict(zip(universe["indexName"], universe["display"]))

    with st.container(key="controls_fbi"):
        c1, c2, c3, c4 = st.columns([2.4, 2.4, 1.8, 3.4],
                                    vertical_alignment="bottom")
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
                                          default="5Y", key="fbi_period",
                                          width="stretch")
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

    t1, t2, t3, t4, t5 = st.tabs(["Overview", "Returns", "Risk", "Hit ratio",
                                  "Market map"])
    with t1:
        _overview(ctx)
    with t2:
        _returns(ctx)
    with t3:
        _risk(ctx)
    with t4:
        _hit_ratio(ctx)
    with t5:
        _market_map(ctx, universe)

    _methodology(as_of)


# =====================================================================
# Small helpers
# =====================================================================

def _headline(text):
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _label(text):
    st.markdown(f"<p class='fbi-label'>{text}</p>", unsafe_allow_html=True)


def _note(text):
    st.markdown(f"<p class='fbi-note'>{text}</p>", unsafe_allow_html=True)


def _section():
    st.markdown("<div class='fbi-section'></div>", unsafe_allow_html=True)


@st.cache_data(max_entries=300, ttl=6 * 3600, show_spinner=False)
def _chart_spec(builder_name, args):
    """Build an Altair chart and return its Vega-Lite spec, cached on the
    inputs. Building and validating a chart costs ~0.1 s; a cached spec
    costs nothing, so reruns from unrelated clicks are instant."""
    return getattr(fv, builder_name)(*args).to_dict()


def _chart(builder, *args):
    st.vega_lite_chart(_chart_spec(builder.__name__, args), theme=None,
                       width="stretch")


def _n(name):
    return fm.pretty_name(name)


def _color(ctx, name):
    if name == ctx["bench"]:
        return fv.COLOR_BENCH
    return fv.SERIES_COLORS[ctx["picks"].index(name)]


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
        text = (f"{phrase}, <b>{_n(a)}</b> returned {fm.fmt_pct(r[a])} a year, "
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
        text = (f"{phrase}, <b>{_n(lead)}</b> returned {fm.fmt_pct(r[lead])} a "
                f"year against {fm.fmt_pct(r[lag])} for {_n(lag)}")
        if len(beat) == 2:
            text += f". Both beat the {_n(bench)} ({fm.fmt_pct(r[bench])})."
        elif len(beat) == 1:
            text += f", which trailed the {_n(bench)} ({fm.fmt_pct(r[bench])})."
        else:
            text += f". Neither beat the {_n(bench)} ({fm.fmt_pct(r[bench])})."
    _headline(text)
    _shortened_note(ctx)

    _kpi_cards(ctx, stats)

    _label("Growth of ₹1 lakh")
    _chart(fv.growth_chart, w, ctx["names"], bench)


def _kpi_cards(ctx, stats):
    bench = ctx["bench"]
    cards = []
    for n in ctx["names"]:
        s = stats[n]
        if n == bench:
            delta = "<div class='kpi-delta flat'>Benchmark</div>"
            cap = "100 / 100"
        else:
            d = s["Annual return"] - stats[bench]["Annual return"]
            cls = "pos" if d > 0.05 else "neg" if d < -0.05 else "flat"
            sign = "+" if d >= 0 else "−"
            delta = (f"<div class='kpi-delta {cls}'>{sign}{abs(d):.1f} pts a year "
                     f"vs {_n(bench)}</div>")
            cap = f"{s['Upside capture']:.0f} / {s['Downside capture']:.0f}"
        cards.append(
            f"<div class='kpi' style='--c:{_color(ctx, n)}'>"
            f"<div class='kpi-name'>{_n(n)}</div>"
            f"<div class='kpi-big'>{fm.fmt_pct(s['Annual return'])}<span>a year</span></div>"
            f"{delta}"
            f"<div class='kpi-meta'>"
            f"<div><b>{fm.fmt_pct(s['Volatility'])}</b><small>Volatility</small></div>"
            f"<div><b>{fm.fmt_pct(s['Worst fall'])}</b><small>Worst fall</small></div>"
            f"<div><b>{cap}</b><small>Capture up / down</small></div>"
            f"</div></div>"
        )
    st.markdown(f"<div class='kpi-row'>{''.join(cards)}</div>",
                unsafe_allow_html=True)


# =====================================================================
# RETURNS
# =====================================================================

def _returns(ctx):
    levels, picks, bench = ctx["levels"], ctx["picks"], ctx["bench"]
    common = levels.loc[max(levels[c].first_valid_index() for c in levels.columns):]

    _label("Rolling window")
    win_label = st.segmented_control("Rolling window", ["1Y", "3Y", "5Y"],
                                     default="3Y", key="fbi_roll",
                                     label_visibility="collapsed")
    win = {"1Y": 1, "3Y": 3, "5Y": 5}[win_label or "3Y"]
    rolling = fm.rolling_cagr(common, win).dropna()

    if rolling.empty:
        _headline(f"Not enough shared history for {win}-year rolling returns.")
    else:
        hr = {p: fm.hit_rate(rolling, p, bench) for p in picks}
        a = picks[0]
        med = hr[a]["median"]
        text = (f"<b>{_n(a)}</b> beat the {_n(bench)} in {hr[a]['pct']:.0f}% of "
                f"rolling {win}-year periods since {hr[a]['since']:%Y}, "
                f"{'leading' if med >= 0 else 'trailing'} by a median of "
                f"{abs(med):.1f} points a year.")
        if len(picks) == 2:
            b = picks[1]
            vs = fm.hit_rate(rolling, a, b)
            text += (f" {_n(b)} did so {hr[b]['pct']:.0f}% of the time. Against "
                     f"each other, {_n(a)} led in {vs['pct']:.0f}% of periods.")
        _headline(text)
        _label(f"Rolling {win}-year return, annualised")
        _chart(fv.rolling_chart, rolling, ctx["names"], bench)
        _note("Consecutive rolling periods overlap heavily, so read these "
              "percentages as a guide rather than proof.")

    cal, partial = fm.calendar_returns(common)
    full = cal[cal.index != partial]
    if ctx["years"]:
        full = full.tail(max(ctx["years"], 5))
    shown = cal.loc[full.index.min():]
    a = picks[0]
    wins = int((full[a] > full[bench]).sum())
    _section()
    _headline(f"<b>{_n(a)}</b> beat the {_n(bench)} in {wins} of the last "
              f"{len(full)} calendar years.")
    _label("Calendar-year return")
    _chart(fv.calendar_chart, shown, ctx["names"], bench, partial)


# =====================================================================
# RISK
# =====================================================================

def _risk(ctx):
    w, picks, bench = ctx["window"], ctx["picks"], ctx["bench"]
    a = picks[0]
    ep = fm.worst_episode(w[a])
    text = (f"<b>{_n(a)}</b>'s worst fall {ctx['phrase']} was "
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
    _chart(fv.drawdown_chart, w, ctx["names"], bench)

    pts = []
    for p in picks:
        up, down, *_ = fm.capture(w, p, bench)
        pts.append((p, down, up, _color(ctx, p)))
    name, down, up, _ = pts[0]
    text = (f"<b>{_n(name)}</b> captured {up:.0f}% of the {_n(bench)}'s gains "
            f"and {down:.0f}% of its losses.")
    if len(pts) == 2:
        n2, d2, u2, _ = pts[1]
        text += f" {_n(n2)}: {u2:.0f}% of gains, {d2:.0f}% of losses."
    _section()
    _headline(text)
    _label(f"Upside and downside capture against the {_n(bench)}")
    _chart(fv.capture_chart, pts, bench)


# =====================================================================
# HIT RATIO
# =====================================================================

HIT_SPANS = {"All history": None, "Last 10 years": 10, "Last 5 years": 5}
_NAVY = (31, 78, 121)
_RUST = (181, 74, 60)


def _hit_cell(v):
    """Navy tint above 50%, rust below; stronger the further from 50."""
    if pd.isna(v):
        return "color:#B7BEC7"
    rgb = _NAVY if v >= 50 else _RUST
    alpha = min(abs(v - 50) / 50, 1) * 0.32 + 0.03
    return f"background-color:rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:.2f})"


def _hit_ratio(ctx):
    _label("Rolling periods ending in")
    span = st.segmented_control("Rolling periods ending in", list(HIT_SPANS),
                                default="All history", key="fbi_hit_span",
                                label_visibility="collapsed")
    years = HIT_SPANS[span or "All history"]

    groups = fm.hit_ratio_groups(years)
    t5 = pd.concat([g["table"]["5Y"] for g in groups]).dropna()
    if t5.empty:
        _headline("Not enough shared history for these rolling windows.")
        return
    majority = int((t5 > 50).sum())
    always = int((t5 >= 100).sum())
    when = ("over their full history" if years is None
            else f"in rolling periods ending in the last {years} years")
    text = (f"<b>{majority} of {len(t5)}</b> strategy indices beat the index "
            f"they are built from in more than half of rolling 5-year "
            f"periods {when}")
    text += (f"; {always} beat it in every one." if always
             else "; none beat it in every one.")
    _headline(text)
    _note("Each strategy index is measured only against its own parent "
          "index: Nifty200 Momentum 30 against the Nifty 200, Nifty Midcap150 "
          "Quality 50 against the Nifty Midcap 150, and so on. Each cell is the "
          "share of rolling periods in which the index's annualised return "
          "beat its parent's. Click any number to see the periods behind it.")

    picks = set(ctx["picks"])
    # Short tables sit two to a row; long ones get the full width.
    small = [g for g in groups if len(g["table"]) <= 5]
    large = [g for g in groups if len(g["table"]) > 5]
    _section()
    for i in range(0, len(small), 2):
        cols = st.columns(2, gap="large")
        for col, g in zip(cols, small[i:i + 2]):
            with col:
                _hit_group(g, years, picks)
    for g in large:
        _section()
        _hit_group(g, years, picks)


def _hit_group(g, years, picks):
    if g["other"]:
        _label(f"Other strategy indices, against the {_n(g['bench'])}")
        _note("These pick stocks from a wider universe with no index of its "
              f"own here, so the Nifty 500 stands in. From {g['start']:%b %Y}.")
    else:
        _label(f"Built from the {_n(g['bench'])}")
        _note(f"From {g['start']:%b %Y}, when every index here has data.")
    _hit_table(g, years, picks)


def _short_name(name):
    """Drop the parent from the name inside its own table:
    'NIFTY MIDCAP150 MOMENTUM 50' -> 'Momentum 50'."""
    for prefix, _ in fm.PARENT_PREFIXES:
        if name.startswith(prefix):
            cut = "NIFTY " if prefix == "NIFTY TOP " else prefix
            return _n(name[len(cut):].strip())
    return _n(name)


def _hit_table(g, years, picks):
    table, counts, bench = g["table"], g["counts"], g["bench"]
    t = table.sort_values(["5Y", "7Y", "3Y"], ascending=False)
    names = list(t.index)
    bold = [n in picks for n in names]
    t.index = [_n(n) if g["other"] else _short_name(n) for n in names]
    t.index.name = "Strategy index"
    styler = (t.style
              .map(_hit_cell)
              .format(lambda v: "–" if pd.isna(v) else f"{v:.0f}%")
              .apply(lambda col: ["font-weight:700" if b else "" for b in bold]))
    cfg = {c: st.column_config.Column(
               f"{c}", width=62,
               help=f"{counts[int(c[:-1])]} rolling {c[:-1]}-year periods. "
                    f"Click a number to see them.")
           for c in t.columns}
    key = f"fbi_hit_{bench}_{'other' if g['other'] else 'own'}"
    event = st.dataframe(styler, column_config=cfg, width="stretch",
                         height=35 * (len(t) + 1) + 3, key=key,
                         on_select="rerun", selection_mode="single-cell")

    # Open the popup only when the clicked cell changes, so it does not
    # pop up again on every unrelated rerun while the cell stays selected.
    cells = event.selection.cells if event else []
    picked = (cells[0][0], cells[0][1]) if cells else None
    seen = f"{key}_seen"
    if picked and picked != st.session_state.get(seen):
        st.session_state[seen] = picked
        row, col = picked
        if col in t.columns and not pd.isna(t.iloc[row][col]):
            _hit_popup(names[row], bench, int(col[:-1]), g["start"], years,
                       t.iloc[row][col])
    elif not picked:
        st.session_state.pop(seen, None)


@st.dialog("Hit ratio, period by period", width="large")
def _hit_popup(name, parent, window, start, years, pct):
    roll = fm.hit_ratio_detail(name, parent, window, start, years)
    gap = roll[name] - roll[parent]
    wins = int((gap > 0).sum())
    _headline(f"<b>{_n(name)}</b> beat the {_n(parent)} in {wins} of "
              f"{len(gap)} rolling {window}-year periods ({pct:.0f}%), "
              f"{'leading' if gap.median() >= 0 else 'trailing'} by a median "
              f"of {abs(gap.median()):.1f} points a year.")
    worst = gap.idxmin()
    best = gap.idxmax()
    _note(f"Periods ending {roll.index[0]:%b %Y} to {roll.index[-1]:%b %Y}. "
          f"Best: {gap[best]:+.1f} pts a year to {best:%b %Y}. "
          f"Worst: {gap[worst]:+.1f} pts a year to {worst:%b %Y}.".replace("-", "−"))
    _label(f"Lead over the {_n(parent)}, each rolling {window}-year period "
           f"(navy = beat, rust = lagged). Hover a bar for dates.")
    _chart(fv.hit_gap_chart, roll, name, parent, window)
    _label(f"Rolling {window}-year return, annualised")
    _chart(fv.rolling_chart, roll, [name, parent], parent)


# =====================================================================
# MARKET MAP
# =====================================================================

def _market_map(ctx, universe):
    c1, c2 = st.columns([1.2, 2], vertical_alignment="bottom")
    with c1:
        view = st.segmented_control("View", ["Risk and return", "Year by year"],
                                    default="Risk and return", key="fbi_map_view")
    if (view or "Risk and return") == "Risk and return":
        _scatter(ctx, universe, c2)
    else:
        _quilt(ctx, universe, c2)


def _scatter(ctx, universe, slot):
    cats = sorted(universe["indexCategory"].unique())
    with slot:
        cat = st.selectbox("Category", cats, index=cats.index("Strategy Indices"),
                           format_func=fm.short_category, key="fbi_map_cat")
    bench, years = ctx["bench"], ctx["years"]
    members = universe.loc[universe["indexCategory"] == cat, "indexName"].tolist()
    names = tuple(dict.fromkeys(members + [bench] + ctx["picks"]))
    pts, start = _risk_return_points(names, years)
    if bench not in pts.index or len(pts) < 3:
        _headline("Not enough indices with the full history for this period.")
        return
    in_cat = [n for n in members if n in pts.index and n != bench]
    b = pts.loc[bench]
    beat = [n for n in in_cat if pts.loc[n, "Return"] > b["Return"]]
    calmer = [n for n in beat if pts.loc[n, "Volatility"] < b["Volatility"]]
    phrase = ("since Apr 2005" if years is None
              else fm.period_phrase(years, start, False))
    _headline(f"<b>{len(beat)} of {len(in_cat)}</b> "
              f"{fm.short_category(cat).lower()} indices beat the {_n(bench)} "
              f"{phrase}; {len(calmer)} of them did it with less volatility.")
    top = pts.loc[in_cat].sort_values("Return", ascending=False).index[:2].tolist()
    _label("Annualised return against volatility. Hover any dot for its name.")
    _chart(fv.risk_return_chart, pts, bench, ctx["picks"], top)
    missing = len([n for n in members if n not in pts.index])
    if missing:
        _note(f"{missing} newer indices without the full history are left out.")


@st.cache_data(max_entries=200, ttl=6 * 3600, show_spinner=False)
def _risk_return_points(names, years):
    """Annualised return and volatility for every index with the full window."""
    levels = fm.levels_to_as_of(list(names))
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
    return pd.DataFrame(rows).T, start


def _quilt(ctx, universe, slot):
    with slot:
        preset = st.segmented_control("Set", list(QUILT_PRESETS),
                                      default="Factors, Nifty 500",
                                      key="fbi_quilt_set")
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
    _headline(f"Leadership keeps changing: <b>{unique} different indices</b> "
              f"topped the table in the last {len(last_full)} years.")
    title_prefix = "Asset Allocation Quilt" if preset == "Custom" else preset
    show_chart(
        _quilt_figure, quilt, build_quilt_color_map(chosen),
        f"{title_prefix} ({cols[0]}\u2013{cols[-1]})",
    )
    if partial:
        _note(f"{partial} is a partial year: the return shown is year to date, "
              f"to {levels.index.max():%d %b %Y}.")


def _quilt_figure(quilt, color_map, title):
    """Original quilt style, in its original font."""
    with plt.rc_context({"font.family": "DejaVu Sans", "text.color": "black"}):
        return make_quilt_chart(quilt, color_map, title=title)


# =====================================================================
# METHODOLOGY
# =====================================================================

def _methodology(as_of):
    st.markdown(
        f"<p class='fbi-source'>Source: NSE Indices via FinAPI. Total return "
        f"indices in INR. Data to {as_of:%d %b %Y}.</p>",
        unsafe_allow_html=True,
    )
    with st.expander("How these numbers are calculated"):
        st.markdown(
            "- **Total return.** Index levels include reinvested dividends. "
            "Price-only, leveraged, inverse, futures and dollar versions are "
            "left out so every comparison is like for like.\n"
            "- **Complete months only.** Figures run to the last complete "
            "month-end, so no statistic includes a partial month.\n"
            "- **Same window for everyone.** A comparison starts only once "
            "every index in it has data.\n"
            "- **Annual return** is compound annual growth (CAGR). "
            "**Volatility** is the standard deviation of monthly returns, "
            "annualised. **Worst fall** is the largest drop from a previous "
            "high, using daily data.\n"
            "- **Upside and downside capture** follow Morningstar: the "
            "annualised return in months the benchmark rose (or fell), "
            "divided by the benchmark's annualised return in those months.\n"
            "- **Rolling returns** overlap month to month, so hit rates "
            "describe history rather than prove an edge.\n"
            "- **Hit ratio** is the share of rolling 1, 3, 5 and 7-year "
            "periods (month-end to month-end) in which an index's annualised "
            "return beat its parent index (the index it selects stocks from). "
            "Within each table every index starts from the same month.\n"
            "- **Backtested history.** NSE calculates many factor indices "
            "back to April 2005, before they launched. Returns before an "
            "index's launch date are back-calculated, not live.\n"
            "- Past performance does not guarantee future results. This is "
            "not investment advice."
        )
