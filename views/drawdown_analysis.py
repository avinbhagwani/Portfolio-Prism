"""
Drawdown Analysis: how far an index fell, how long it stayed down, and
whether it has recovered, in the same style as FBI Intelligence.

  Headline   one sentence on the worst fall and the recovery
  Cards      worst fall, where it is today, longest time underwater,
             how often it fell 20% or more, share of time below its high
  Chart      fall from previous high (interactive)
  Episodes   the worst falls, with time to the bottom and back

Every figure uses total return levels cut at the last complete month,
and when two indices are compared, the same window for both.
"""

import pandas as pd
import streamlit as st

from charts import fbi_vega as fv
from core import fbi_metrics as fm
from core.index_analytics import find_drawdown_episodes
from views.factor_indexes import CSS as FBI_CSS

DEFAULT_A = "NIFTY MIDCAP 150"
DEFAULT_B = "NIFTY 50"
NONE = "None"
PERIODS = {"3Y": 3, "5Y": 5, "10Y": 10, "Max": None}

CSS = """
<style>
.dd-table {width:100%; border-collapse:collapse; font-size:0.92rem; margin-top:0.4rem;}
.dd-table th {text-align:left; font-weight:500; color:#8A939E; font-size:0.78rem;
  letter-spacing:0.04em; text-transform:uppercase; padding:8px 10px; border-bottom:1px solid #E6E9ED;}
.dd-table td {padding:11px 10px; border-bottom:1px solid #F0F2F5; color:#1B2533;
  font-variant-numeric:tabular-nums; vertical-align:middle;}
.dd-table td.muted {color:#8A939E;}
.dd-depth {display:flex; align-items:center; gap:10px;}
.dd-depth b {min-width:3.6rem; font-weight:600; color:#B54A3C;}
.dd-bar {flex:1; height:6px; background:#F3F4F6; border-radius:3px; max-width:160px; overflow:hidden;}
.dd-bar i {display:block; height:100%; background:#D9826F; border-radius:3px;}
.dd-open {display:inline-block; font-size:0.74rem; font-weight:600; color:#9A6B1E;
  background:#FBF3E4; padding:2px 8px; border-radius:999px;}
.dd-name {font-size:0.95rem; font-weight:600; color:#1B2533; margin:1.6rem 0 0 0;}
</style>
"""


def _dur(days):
    months = int(round(days / 30.44))
    y, m = divmod(months, 12)
    if y == 0:
        return f"{m} mo"
    return f"{y} yr{'s' if y > 1 else ''}" + (f" {m} mo" if m else "")


def _episodes(series, as_of):
    """Every distinct fall (peak to recovery), deepest first."""
    eps = find_drawdown_episodes(series.to_frame("x"), "x", top_n=10_000)
    for e in eps:
        e["fall_days"] = (e["trough_date"] - e["peak_date"]).days
        end = e["recovery_date"] if e["recovery_date"] is not None else as_of
        e["under_days"] = (end - e["peak_date"]).days
        e["recover_days"] = (e["recovery_date"] - e["trough_date"]).days if e["recovery_date"] is not None else None
    return eps


def _stats(series, as_of):
    s = series.dropna()
    s = s[s.index.dayofweek < 5]          # trading days only (the file has weekend rows)
    dd = s / s.cummax() - 1
    eps = _episodes(s, as_of)
    worst = eps[0] if eps else None
    return {
        "worst": worst,
        "now": dd.iloc[-1] * 100,
        "longest": max((e["under_days"] for e in eps), default=0),
        "big_falls": sum(1 for e in eps if e["depth_pct"] <= -20),
        "below10": (dd <= -0.10).mean() * 100,
        "episodes": eps,
    }


def render():
    st.markdown(FBI_CSS + CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='fbi-eyebrow'>Drawdown Analysis</div>"
        "<div class='fbi-title'>How far did it fall, and how long did it take to recover?</div>"
        "<div class='fbi-sub'>Every fall from a previous high for any Nifty index: how deep, "
        "how long it stayed down, and whether it has climbed back.</div>",
        unsafe_allow_html=True,
    )

    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    display = dict(zip(universe["indexName"], universe["display"]))

    with st.container(border=True):
        c1, c2, c3 = st.columns([2.6, 2.6, 2.4], vertical_alignment="bottom")
        with c1:
            a = st.selectbox("Index", names, index=names.index(DEFAULT_A),
                             format_func=display.get, key="dd_a")
        with c2:
            b_opts = [NONE] + names
            b = st.selectbox("Compare with", b_opts, index=b_opts.index(DEFAULT_B),
                             format_func=lambda n: "Nothing" if n == NONE else display.get(n, n),
                             key="dd_b")
        with c3:
            period = st.segmented_control("Period", list(PERIODS), default="Max",
                                          key="dd_period", width="stretch") or "Max"

    picks = [a] + ([b] if b not in (NONE, a) else [])
    levels = fm.levels_to_as_of(picks)
    as_of = levels.index.max()
    years = PERIODS[period]
    window, start, shortened = fm.common_window(levels, years)
    phrase = fm.period_phrase(years, start, shortened)
    stats = {n: _stats(window[n], as_of) for n in picks}

    _headline(a, b if len(picks) == 2 else None, stats, phrase)
    if shortened or (len(picks) == 2 and years is None):
        late = max(picks, key=lambda n: levels[n].first_valid_index())
        if len(picks) == 2 and levels[late].first_valid_index() > levels[[n for n in picks if n != late][0]].first_valid_index():
            _note(f"Both are shown since {start:%b %Y}, when {fm.pretty_name(late)} history begins.")

    _cards(picks, stats)

    _label("Fall from previous high")
    st.vega_lite_chart(fv.drawdown_chart(window, picks, "").to_dict(), theme=None, width="stretch")

    _section()
    _headline_plain("The worst falls, and how long the way back took.")
    for n in picks:
        if len(picks) > 1:
            st.markdown(f"<div class='dd-name'>{fm.pretty_name(n)}</div>", unsafe_allow_html=True)
        _episode_table(stats[n]["episodes"])

    st.markdown(
        f"<p class='fbi-source'>Source: NSE Indices via FinAPI. Total return indices in INR, "
        f"daily, to {as_of:%d %b %Y}. A fall runs from a closing high to the day the index "
        f"first closes back above it.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------

def _headline(a, b, stats, phrase):
    s = stats[a]
    w = s["worst"]
    name = fm.pretty_name(a)
    lead = phrase[0].upper() + phrase[1:]
    if w is None:
        text = f"{lead}, <b>{name}</b> never fell below a previous high."
    else:
        text = (f"{lead}, <b>{name}</b>'s worst fall was {fm.fmt_pct(w['depth_pct'], decimals=0)}, "
                f"from {w['peak_date']:%b %Y} to {w['trough_date']:%b %Y}. ")
        if w["recovery_date"] is not None:
            text += f"It took {_dur(w['under_days'])} from that peak to get back above it."
        else:
            text += f"It still hasn't recovered, {_dur(w['under_days'])} later."
        if b:
            wb = stats[b]["worst"]
            if wb is not None:
                same = abs((wb["peak_date"] - w["peak_date"]).days) < 120
                text += (f" {fm.pretty_name(b)}'s worst was {fm.fmt_pct(wb['depth_pct'], decimals=0)}"
                         f"{' in the same fall' if same else ''}"
                         + (f", back in {_dur(wb['under_days'])}." if wb["recovery_date"] is not None
                            else ", and it hasn't recovered yet."))
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _headline_plain(text):
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _label(text):
    st.markdown(f"<p class='fbi-label'>{text}</p>", unsafe_allow_html=True)


def _note(text):
    st.markdown(f"<p class='fbi-note'>{text}</p>", unsafe_allow_html=True)


def _section():
    st.markdown("<div class='fbi-section'></div>", unsafe_allow_html=True)


def _cards(picks, stats):
    cards = []
    for i, n in enumerate(picks):
        s = stats[n]
        w = s["worst"]
        now = s["now"]
        if now > -0.5:
            delta = "<div class='kpi-delta pos'>At its high today</div>"
        else:
            delta = f"<div class='kpi-delta neg'>{abs(now):.0f}% below its high today</div>"
        big = fm.fmt_pct(w["depth_pct"], decimals=0) if w else "0%"
        cards.append(
            f"<div class='kpi' style='--c:{fv.SERIES_COLORS[i]}'>"
            f"<div class='kpi-name'>{fm.pretty_name(n)}</div>"
            f"<div class='kpi-big'>{big}<span>worst fall</span></div>"
            f"{delta}"
            f"<div class='kpi-meta'>"
            f"<div><b>{_dur(s['longest']) if s['longest'] else 'None'}</b><small>Longest underwater</small></div>"
            f"<div><b>{s['big_falls']}</b><small>Falls of 20%+</small></div>"
            f"<div><b>{s['below10']:.0f}%</b><small>Of days 10%+ down</small></div>"
            f"</div></div>"
        )
    st.markdown(f"<div class='kpi-row'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _episode_table(eps, top=5):
    eps = [e for e in eps if e["depth_pct"] <= -5][:top]
    if not eps:
        _note("No falls of 5% or more in this period.")
        return
    deepest = abs(eps[0]["depth_pct"])
    rows = []
    for e in eps:
        width = abs(e["depth_pct"]) / deepest * 100
        back = (f"{e['recovery_date']:%b %Y}" if e["recovery_date"] is not None
                else "<span class='dd-open'>Not yet</span>")
        rows.append(
            "<tr>"
            f"<td><div class='dd-depth'><b>{fm.fmt_pct(e['depth_pct'], decimals=0)}</b>"
            f"<div class='dd-bar'><i style='width:{width:.0f}%'></i></div></div></td>"
            f"<td>{e['peak_date']:%b %Y}</td>"
            f"<td>{e['trough_date']:%b %Y}</td>"
            f"<td class='muted'>{_dur(e['fall_days'])}</td>"
            f"<td>{back}</td>"
            f"<td class='muted'>{_dur(e['under_days'])}{'' if e['recovery_date'] is not None else ' so far'}</td>"
            "</tr>"
        )
    st.markdown(
        "<table class='dd-table'><thead><tr><th>Fall</th><th>From the high</th><th>Bottom</th>"
        "<th>Time to bottom</th><th>Back above the high</th><th>Time underwater</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>",
        unsafe_allow_html=True,
    )
