"""
Drawdown Analysis: how far indices and mutual funds fell, how long they
stayed down, and whether they have recovered, in the FBI Intelligence style.

  Controls   up to 10 series in any mix: Nifty indices (multiselect) and
             mutual funds (search, then add); a period
  Headline   the worst fall and recovery; with several series, who fell
             most, who held up best, who stayed down longest
  Summary    cards for up to 3 series, a ranked table beyond that
  Chart      fall from previous high (interactive)
  Episodes   the worst falls of whichever series you pick

Indices are total return levels cut at the last complete month; funds use
their NAV. All series share one window (the period, starting once every
series has data, ending on the last date they all have).
"""

import pandas as pd
import streamlit as st

from charts import fbi_vega as fv
from core import fbi_metrics as fm
from core.data import fetch_fund_history, search_funds
from core.index_analytics import find_drawdown_episodes
from views.factor_indexes import CSS as FBI_CSS

DEFAULT_INDICES = ["NIFTY MIDCAP 150", "NIFTY 50"]
MAX_SERIES = 10
PERIODS = {"3Y": 3, "5Y": 5, "10Y": 10, "Max": None}

CSS = """
<style>
.dd-table {width:100%; border-collapse:collapse; font-size:0.92rem; margin-top:0.4rem;}
.dd-table th {text-align:left; font-weight:500; color:#8A939E; font-size:0.76rem;
  letter-spacing:0.04em; text-transform:uppercase; padding:8px 10px; border-bottom:1px solid #E6E9ED;}
.dd-table td {padding:10px 10px; border-bottom:1px solid #F0F2F5; color:#1B2533;
  font-variant-numeric:tabular-nums; vertical-align:middle;}
.dd-table td.muted {color:#8A939E;}
.dd-depth {display:flex; align-items:center; gap:10px;}
.dd-depth b {min-width:3.6rem; font-weight:600; color:#B54A3C;}
.dd-bar {flex:1; height:6px; background:#F3F4F6; border-radius:3px; min-width:44px; max-width:160px; overflow:hidden;}
.dd-bar i {display:block; height:100%; background:#D9826F; border-radius:3px;}
.dd-open {display:inline-block; font-size:0.74rem; font-weight:600; color:#9A6B1E;
  background:#FBF3E4; padding:2px 8px; border-radius:999px;}
.dd-dot {display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; vertical-align:0;}
.dd-legend {display:flex; flex-wrap:wrap; gap:6px 16px; margin:0.5rem 0 0 0; font-size:0.86rem; color:#4A5562;}
.dd-legend span {display:inline-flex; align-items:center;}
.dd-tag {font-size:0.7rem; font-weight:600; color:#8A939E; letter-spacing:0.04em; margin-left:6px;}
.dd-funds-label {font-size:0.875rem; color:#31333F; margin:0.6rem 0 0.25rem 0;}
.dd-count {font-size:0.82rem; color:#8A939E; margin:0.4rem 0 0 0;}
</style>
"""


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def _dur(days):
    months = int(round(days / 30.44))
    y, m = divmod(months, 12)
    if y == 0:
        return f"{m} mo"
    return f"{y} yr{'s' if y > 1 else ''}" + (f" {m} mo" if m else "")


def _fund_label(name):
    """'XYZ Small Cap Fund - Direct Plan - Growth' -> 'XYZ Small Cap Fund (Direct)'."""
    short = name.split(" - ")[0].strip()
    low = name.lower()
    plan = " (Direct)" if "direct" in low else " (Regular)" if "regular" in low else ""
    return short + plan


def _label(key):
    """Index names come in capitals and get NSE's casing; fund labels are kept."""
    return fm.pretty_name(key) if key.isupper() else key


def _episodes(series, as_of):
    eps = find_drawdown_episodes(series.to_frame("x"), "x", top_n=10_000)
    for e in eps:
        e["fall_days"] = (e["trough_date"] - e["peak_date"]).days
        end = e["recovery_date"] if e["recovery_date"] is not None else as_of
        e["under_days"] = (end - e["peak_date"]).days
    return eps


def _stats(series, as_of):
    s = series.dropna()
    s = s[s.index.dayofweek < 5]          # trading days only (the index file has weekend rows)
    dd = s / s.cummax() - 1
    eps = _episodes(s, as_of)
    return {
        "worst": eps[0] if eps else None,
        "now": dd.iloc[-1] * 100,
        "longest": max((e["under_days"] for e in eps), default=0),
        "big_falls": sum(1 for e in eps if e["depth_pct"] <= -20),
        "below10": (dd <= -0.10).mean() * 100,
        "episodes": eps,
    }


# ---------------------------------------------------------------------
# page
# ---------------------------------------------------------------------

def render():
    st.markdown(FBI_CSS + CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='fbi-eyebrow'>Drawdown Analysis</div>"
        "<div class='fbi-title'>How far did it fall, and how long did it take to recover?</div>"
        "<div class='fbi-sub'>Compare every fall from a previous high for up to ten Nifty indices "
        "and mutual funds: how deep, how long they stayed down, and whether they have climbed back.</div>",
        unsafe_allow_html=True,
    )

    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    display = dict(zip(universe["indexName"], universe["display"]))
    funds = st.session_state.setdefault("dd_funds", [])      # [{"code", "name"}]

    with st.container(border=True):
        c1, c2 = st.columns([5, 2.2], vertical_alignment="bottom")
        with c1:
            indices = st.multiselect(
                "Indices", names, default=[n for n in DEFAULT_INDICES if n in names],
                format_func=display.get, max_selections=MAX_SERIES,   # fixed: changing it would reset the box
                key="dd_indices", placeholder="Add Nifty indices")
        with c2:
            period = st.segmented_control("Period", list(PERIODS), default="Max",
                                          key="dd_period", width="stretch") or "Max"
        if len(indices) + len(funds) > MAX_SERIES:
            keep = MAX_SERIES - len(funds)
            st.caption(f"Up to {MAX_SERIES} in total, so only the first {keep} indices are used. "
                       "Remove a fund or an index to fit more.")
            indices = indices[:keep]
        _fund_picker(funds, room=MAX_SERIES - len(indices) - len(funds))
        st.markdown(f"<p class='dd-count'>{len(indices) + len(funds)} of {MAX_SERIES} selected</p>",
                    unsafe_allow_html=True)

    levels, kinds, missing = _load(indices, funds)
    for m in missing:
        st.caption(f"Couldn't load the NAV history for {m} just now; it's left out. Try again in a minute.")
    if levels is None:
        st.markdown("<p class='fbi-headline'>Pick at least one index or fund above.</p>",
                    unsafe_allow_html=True)
        return

    picks = list(levels.columns)
    as_of = levels.index.max()
    years = PERIODS[period]
    window, start, shortened = fm.common_window(levels, years)
    phrase = fm.period_phrase(years, start, shortened)
    stats = {n: _stats(window[n], as_of) for n in picks}
    colours = dict(zip(picks, fv.SERIES_COLORS))

    _headline(picks, stats, phrase)
    firsts = {n: levels[n].first_valid_index() for n in picks}
    if len(picks) > 1 and len(set(firsts.values())) > 1 and (years is None or shortened):
        late = max(picks, key=firsts.get)
        _note(f"All are shown since {start:%b %Y}, when {_label(late)} history begins.")

    if len(picks) <= 3:
        _cards(picks, stats, colours)
    else:
        _summary_table(picks, stats, colours, kinds)

    _lab("Fall from previous high")
    many = len(picks) > 5
    chart = fv.drawdown_chart(window, picks, "", end_labels=not many).to_dict()
    st.vega_lite_chart(chart, theme=None, width="stretch")
    if many:
        st.markdown("<div class='dd-legend'>" + "".join(
            f"<span><i class='dd-dot' style='background:{colours[n]}'></i>{_label(n)}</span>" for n in picks)
            + "</div>", unsafe_allow_html=True)

    _section()
    _headline_plain("The worst falls, and how long the way back took.")
    who = picks[0]
    if len(picks) > 1:
        who = st.selectbox("Show the falls for", picks, format_func=_label, key="dd_episodes_for")
    _episode_table(stats[who]["episodes"])

    st.markdown(
        f"<p class='fbi-source'>Indices: NSE Indices via FinAPI, total return in INR. Funds: NAV from "
        f"mfapi.in. Daily data to {as_of:%d %b %Y}. A fall runs from a closing high to the day the "
        f"series first closes back above it.</p>",
        unsafe_allow_html=True,
    )


def _fund_picker(funds, room):
    """Search for a fund, add it; added funds are listed with a remove button."""
    st.markdown("<p class='dd-funds-label'>Mutual funds</p>", unsafe_allow_html=True)
    a, b, c = st.columns([2.2, 4.2, 1.2], vertical_alignment="bottom")
    with a:
        term = st.text_input("Search funds", key="dd_fund_q", placeholder="Search a fund",
                             label_visibility="collapsed", disabled=room <= 0)
    matches = search_funds(term) if term else []
    have = {f["code"] for f in funds}
    opts = {f"{m['name']}  ·  {m['code']}": m for m in matches if m["code"] not in have}
    with b:
        pick = st.selectbox("Fund", list(opts) or ["—"], key="dd_fund_pick",
                            label_visibility="collapsed", disabled=not opts or room <= 0)
    with c:
        if st.button("Add", key="dd_fund_add", icon=":material/add:", width="stretch",
                     disabled=not opts or room <= 0):
            funds.append({"code": opts[pick]["code"], "name": opts[pick]["name"]})
            st.rerun()
    if term and len(term.strip()) >= 3 and not matches:
        st.caption("No funds found. Try another name.")
    if room <= 0:
        st.caption(f"That's the maximum of {MAX_SERIES}. Remove one to add another.")
    for i, f in enumerate(list(funds)):
        x, y = st.columns([12, 1], vertical_alignment="center")
        with x:
            st.markdown(f"<span style='font-size:0.92rem'>{_fund_label(f['name'])}</span>"
                        f"<span class='dd-tag'>FUND</span>", unsafe_allow_html=True)
        with y:
            if st.button("", key=f"dd_rm_{f['code']}", icon=":material/close:", help="Remove"):
                funds.pop(i)
                st.rerun()


def _load(indices, funds):
    """One frame of levels, cut to the last date every series has."""
    cols, kinds, missing = {}, {}, []
    if indices:
        lv = fm.levels_to_as_of(indices)
        for n in indices:
            cols[n] = lv[n]
            kinds[n] = "Index"
    for f in funds:
        df = fetch_fund_history(f["code"])
        label = _fund_label(f["name"])
        if label in cols:                                    # two plans with the same short name
            label = f"{label} {f['code']}"
        if df.empty:
            missing.append(label)
            continue
        cols[label] = df.set_index("date")["nav"].astype(float)
        kinds[label] = "Fund"
    if not cols:
        return None, kinds, missing
    levels = pd.concat(cols, axis=1).sort_index()
    levels = levels.where(levels > 0)
    end = min(levels[c].last_valid_index() for c in levels.columns)
    return levels.loc[:end], kinds, missing


# ---------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------

def _headline(picks, stats, phrase):
    lead = phrase[0].upper() + phrase[1:]
    a = picks[0]
    w = stats[a]["worst"]
    if len(picks) <= 2:
        if w is None:
            text = f"{lead}, <b>{_label(a)}</b> never fell below a previous high."
        else:
            text = (f"{lead}, <b>{_label(a)}</b>'s worst fall was {fm.fmt_pct(w['depth_pct'], decimals=0)}, "
                    f"from {w['peak_date']:%b %Y} to {w['trough_date']:%b %Y}. ")
            text += (f"It took {_dur(w['under_days'])} from that peak to get back above it."
                     if w["recovery_date"] is not None
                     else f"It still hasn't recovered, {_dur(w['under_days'])} later.")
        if len(picks) == 2:
            b = picks[1]
            wb = stats[b]["worst"]
            if wb is not None:
                same = w is not None and abs((wb["peak_date"] - w["peak_date"]).days) < 120
                text += (f" {_label(b)}'s worst was {fm.fmt_pct(wb['depth_pct'], decimals=0)}"
                         f"{' in the same fall' if same else ''}"
                         + (f", back in {_dur(wb['under_days'])}." if wb["recovery_date"] is not None
                            else ", and it hasn't recovered yet."))
    else:
        withw = [n for n in picks if stats[n]["worst"] is not None]
        deep = min(withw, key=lambda n: stats[n]["worst"]["depth_pct"])
        mild = max(withw, key=lambda n: stats[n]["worst"]["depth_pct"])
        long_ = max(picks, key=lambda n: stats[n]["longest"])
        text = (f"{lead}, <b>{_label(deep)}</b> fell the furthest of these {len(picks)}, "
                f"{fm.fmt_pct(stats[deep]['worst']['depth_pct'], decimals=0)} at its worst. "
                f"<b>{_label(mild)}</b> held up best ({fm.fmt_pct(stats[mild]['worst']['depth_pct'], decimals=0)})")
        text += (f", and <b>{_label(long_)}</b> stayed underwater longest, {_dur(stats[long_]['longest'])}."
                 if long_ != deep else f". {_label(deep)} also stayed underwater longest, "
                 f"{_dur(stats[long_]['longest'])}.")
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _headline_plain(text):
    st.markdown(f"<p class='fbi-headline'>{text}</p>", unsafe_allow_html=True)


def _lab(text):
    st.markdown(f"<p class='fbi-label'>{text}</p>", unsafe_allow_html=True)


def _note(text):
    st.markdown(f"<p class='fbi-note'>{text}</p>", unsafe_allow_html=True)


def _section():
    st.markdown("<div class='fbi-section'></div>", unsafe_allow_html=True)


def _today(now):
    return ("<div class='kpi-delta pos'>At its high today</div>" if now > -0.5
            else f"<div class='kpi-delta neg'>{abs(now):.0f}% below its high today</div>")


def _cards(picks, stats, colours):
    cards = []
    for n in picks:
        s = stats[n]
        w = s["worst"]
        big = fm.fmt_pct(w["depth_pct"], decimals=0) if w else "0%"
        cards.append(
            f"<div class='kpi' style='--c:{colours[n]}'>"
            f"<div class='kpi-name'>{_label(n)}</div>"
            f"<div class='kpi-big'>{big}<span>worst fall</span></div>"
            f"{_today(s['now'])}"
            f"<div class='kpi-meta'>"
            f"<div><b>{_dur(s['longest']) if s['longest'] else 'None'}</b><small>Longest underwater</small></div>"
            f"<div><b>{s['big_falls']}</b><small>Falls of 20%+</small></div>"
            f"<div><b>{s['below10']:.0f}%</b><small>Of days 10%+ down</small></div>"
            f"</div></div>"
        )
    st.markdown(f"<div class='kpi-row'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _summary_table(picks, stats, colours, kinds):
    """With more than three series, one row each, deepest worst fall first."""
    order = sorted(picks, key=lambda n: stats[n]["worst"]["depth_pct"] if stats[n]["worst"] else 0)
    deepest = max((abs(stats[n]["worst"]["depth_pct"]) for n in picks if stats[n]["worst"]), default=1)
    rows = []
    for n in order:
        s, w = stats[n], stats[n]["worst"]
        depth = (f"<div class='dd-depth'><b>{fm.fmt_pct(w['depth_pct'], decimals=0)}</b>"
                 f"<div class='dd-bar'><i style='width:{abs(w['depth_pct']) / deepest * 100:.0f}%'></i></div></div>"
                 if w else "—")
        when = f"{w['peak_date']:%b %Y} to {w['trough_date']:%b %Y}" if w else "—"
        back = ((_dur(w["under_days"]) if w["recovery_date"] is not None else "<span class='dd-open'>Not yet</span>")
                if w else "—")
        now = "At its high" if s["now"] > -0.5 else fm.fmt_pct(s["now"], decimals=0)
        tag = "<span class='dd-tag'>FUND</span>" if kinds.get(n) == "Fund" else ""
        rows.append(
            f"<tr><td><i class='dd-dot' style='background:{colours[n]}'></i>{_label(n)}{tag}</td>"
            f"<td>{depth}</td><td class='muted'>{when}</td><td>{back}</td>"
            f"<td>{now}</td><td class='muted'>{_dur(s['longest']) if s['longest'] else 'None'}</td>"
            f"<td class='muted'>{s['big_falls']}</td></tr>")
    st.markdown(
        "<table class='dd-table' style='margin-top:1.4rem'><thead><tr><th>Name</th><th>Worst fall</th>"
        "<th>When</th><th>Back above the high in</th><th>Today</th><th>Longest underwater</th>"
        f"<th>Falls of 20%+</th></tr></thead><tbody>{''.join(rows)}</tbody></table>",
        unsafe_allow_html=True,
    )


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
