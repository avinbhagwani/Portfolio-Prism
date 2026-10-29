"""
Drawdown Analysis: how far indices and mutual funds fell, how long they
stayed down, and whether they have recovered, in the FBI Intelligence style.

  Controls   up to 10 picks in any mix, added from one picker (Index or
             Mutual fund, with quick-add buttons for common indices) and
             shown as removable chips in their chart colours; a period;
             same start for all, or each from its own start
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
from views import tutorial
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
.dd-head {display:flex; justify-content:space-between; align-items:baseline; margin:0 0 0.2rem 0;}
.dd-head b {font-size:0.95rem; font-weight:600; color:#1B2533;}
.dd-head span {font-size:0.82rem; color:#8A939E;}
.dd-hint {font-size:0.8rem; color:#8A939E; margin:0.1rem 0 0 0;}
/* chosen series as chips, each with its chart colour */
.st-key-dd_chips button {border-radius:999px !important; border:1px solid #E1E5EA !important; background:#fff !important;
  padding:0.2rem 0.55rem 0.2rem 0.7rem !important; min-height:0 !important; box-shadow:none !important;}
.st-key-dd_chips button:hover {border-color:#B54A3C !important; background:#FFF7F6 !important;}
.st-key-dd_chips button p {font-size:0.86rem !important; font-weight:500 !important; color:#1B2533 !important;}
.st-key-dd_chips button p::before {content:""; display:inline-block; width:9px; height:9px; border-radius:50%;
  margin-right:7px; vertical-align:0; background:var(--dot, #8A939E);}
.st-key-dd_chips [data-testid="stIconMaterial"] {color:#9AA3AE !important; font-size:16px !important;}
.st-key-dd_quick button {border-radius:999px !important; border:1px dashed #C9D2DC !important; background:transparent !important;
  padding:0.15rem 0.6rem !important; min-height:0 !important;}
.st-key-dd_quick button p {font-size:0.8rem !important; color:#4A5562 !important;}
.st-key-dd_quick button:hover {border-color:#1F4E79 !important;}
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
    tutorial.launcher("drawdown-analysis")

    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    display = dict(zip(universe["indexName"], universe["display"]))
    sel = st.session_state.setdefault(
        "dd_sel", [{"kind": "index", "key": n} for n in DEFAULT_INDICES if n in names])

    with st.container(key="controls_dd"):
        st.markdown(f"<div class='dd-head'><b>Compare</b><span>{len(sel)} of {MAX_SERIES}"
                    f"{' · that’s the most' if len(sel) >= MAX_SERIES else ''}</span></div>",
                    unsafe_allow_html=True)
        _picker(sel, names, display)
        _chips(sel)
        p1, p2 = st.columns([2.4, 3], vertical_alignment="bottom")
        with p1:
            period = st.segmented_control("Period", list(PERIODS), default="Max",
                                          key="dd_period", width="stretch") or "Max"
        with p2:
            align = st.segmented_control(
                "Start dates", ["Same for all", "Each from its own start"], default="Same for all",
                key="dd_align", help="Same for all compares everything over the same years, starting "
                "once every pick has data. Each from its own start shows every pick's full history.") \
                or "Same for all"

    levels, kinds, missing = _load(sel)
    for m in missing:
        st.caption(f"Couldn't load the NAV history for {m} just now; it's left out. Try again in a minute.")
    if levels is None:
        st.markdown("<p class='fbi-headline'>Pick at least one index or fund above.</p>",
                    unsafe_allow_html=True)
        return

    picks = list(levels.columns)
    as_of = levels.index.max()
    years = PERIODS[period]
    own = align != "Same for all" and len(picks) > 1
    if own:
        start = (as_of - pd.DateOffset(years=years)) if years else levels.index.min()
        window = levels.loc[start:].ffill()                 # leading gaps stay empty until each starts
        shortened = False
        phrase = fm.period_phrase(years, start, False) if years else "over each one's full history"
    else:
        window, start, shortened = fm.common_window(levels, years)
        phrase = fm.period_phrase(years, start, shortened)
    stats = {n: _stats(window[n], as_of) for n in picks if window[n].notna().sum() > 20}
    picks = [n for n in picks if n in stats]
    colours = {lab: fv.SERIES_COLORS[i] for i, lab in enumerate(_labels(sel)) if lab in picks}

    _headline(picks, stats, phrase)
    firsts = {n: levels[n].first_valid_index() for n in picks}
    if not own and len(picks) > 1 and len(set(firsts.values())) > 1 and (years is None or shortened):
        late = max(picks, key=firsts.get)
        _note(f"All are shown since {start:%b %Y}, when {_label(late)} history begins. Switch "
              f"<b>Start dates</b> to <b>Each from its own start</b> to see everything's full history.")
    if years:
        _note("Falls are measured from highs within this period.")

    if len(picks) <= 3:
        _cards(picks, stats, colours)
    else:
        _summary_table(picks, stats, colours, kinds)

    _lab("Fall from previous high")
    many = len(picks) > 3            # beyond three, line-end labels collide; use a colour key
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


QUICK = ["NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY 500",
         "NIFTY200 MOMENTUM 30", "NIFTY500 VALUE 50", "NIFTY100 LOW VOLATILITY 30"]


def _add(item):
    sel = st.session_state["dd_sel"]
    if len(sel) < MAX_SERIES and all(x["key"] != item["key"] for x in sel):
        sel.append(item)


def _add_index():
    key = st.session_state.get("dd_add_index")
    if key:
        _add({"kind": "index", "key": key})
    st.session_state["dd_add_index"] = None                 # ready for the next one


def _add_fund():
    pick = st.session_state.get("dd_add_fund")
    opts = st.session_state.get("_dd_fund_opts", {})
    if pick in opts:
        _add({"kind": "fund", "key": opts[pick]["code"], "name": opts[pick]["name"]})
        st.session_state["dd_fund_q"] = ""                 # clear the search for the next fund
    st.session_state["dd_add_fund"] = None


def _picker(sel, names, display):
    """One place to add either kind: choose Index or Mutual fund, pick, done."""
    full = len(sel) >= MAX_SERIES
    chosen = {x["key"] for x in sel}
    k1, k2 = st.columns([1.35, 5], vertical_alignment="bottom")
    with k1:
        kind = st.segmented_control("Add", ["Index", "Mutual fund"], default="Index",
                                    key="dd_add_kind", label_visibility="collapsed") or "Index"
    with k2:
        if kind == "Index":
            st.selectbox("Index", [n for n in names if n not in chosen], index=None,
                         format_func=display.get, key="dd_add_index", on_change=_add_index,
                         placeholder="Type to find a Nifty index, then pick it to add",
                         label_visibility="collapsed", disabled=full)
        else:
            f1, f2 = st.columns([1.3, 2.2], vertical_alignment="bottom")
            with f1:
                term = st.text_input("Fund", key="dd_fund_q", placeholder="Search a fund name",
                                     label_visibility="collapsed", disabled=full)
            matches = search_funds(term) if term else []
            opts = {f"{_fund_label(m['name'])}  ·  {m['code']}": m for m in matches if m["code"] not in chosen}
            st.session_state["_dd_fund_opts"] = opts
            with f2:
                st.selectbox("Plan", list(opts), index=None, key="dd_add_fund", on_change=_add_fund,
                             placeholder=("Pick a plan to add" if opts else
                                          "No funds found" if term and len(term.strip()) >= 3 else
                                          "Results appear here"),
                             label_visibility="collapsed", disabled=full or not opts)
    if kind == "Index" and not full:
        quick = [n for n in QUICK if n in names and n not in chosen][:6]
        if quick:
            with st.container(key="dd_quick", horizontal=True, gap="small"):
                for n in quick:
                    st.button(f"+ {display[n]}", key=f"dd_q_{n}", on_click=_add,
                              args=({"kind": "index", "key": n},))


def _remove(key):
    st.session_state["dd_sel"] = [x for x in st.session_state["dd_sel"] if x["key"] != key]


def _chips(sel):
    if not sel:
        st.markdown("<p class='dd-hint'>Nothing chosen yet. Add an index or a fund above.</p>",
                    unsafe_allow_html=True)
        return
    css = "".join(f".st-key-dd_chip_{i} button {{--dot:{fv.SERIES_COLORS[i]};}}" for i in range(len(sel)))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    with st.container(key="dd_chips", horizontal=True, gap="small"):
        for i, (x, lab) in enumerate(zip(sel, _labels(sel))):
            st.button(_label(lab) + (" · fund" if x["kind"] == "fund" else ""), key=f"dd_chip_{i}",
                      icon=":material/close:", icon_position="right",
                      on_click=_remove, args=(x["key"],))


def _labels(sel):
    """Display label per selection, unique even if two plans share a short name."""
    out = []
    for x in sel:
        # index keys stay in capitals (_label() gives them NSE's casing); funds get a short name
        lab = x["key"] if x["kind"] == "index" else _fund_label(x["name"])
        if lab in out:
            lab = f"{lab} {x['key']}"
        out.append(lab)
    return out


def _clean_nav(s):
    """Drop one-day NAV glitches (a jump of 25%+ that fully reverses the next
    day), which would otherwise show up as huge fake falls."""
    s = s.dropna()
    s = s[s > 0]
    jump = s.pct_change().abs() > 0.25
    back = (s.shift(-1) / s.shift(1) - 1).abs() < 0.05
    return s[~(jump & back)]


def _load(sel):
    """One frame of levels in selection order, cut to the last date every series has."""
    cols, kinds, missing = {}, {}, []
    idx = [x["key"] for x in sel if x["kind"] == "index"]
    lv = fm.levels_to_as_of(idx) if idx else None
    for x, lab in zip(sel, _labels(sel)):
        if x["kind"] == "index":
            cols[lab] = lv[x["key"]]
            kinds[lab] = "Index"
        else:
            df = fetch_fund_history(x["key"])
            if df.empty:
                missing.append(_fund_label(x["name"]))
                continue
            cols[lab] = _clean_nav(df.set_index("date")["nav"].astype(float))
            kinds[lab] = "Fund"
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
