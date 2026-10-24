"""
Efficient Frontier: which mix of indices gave the most return for the
risk taken over a look-back window, and did that mix keep working over
the years that followed?

  Controls   the set (Nifty 500 factor indices by default, or a custom
             set of up to 10 indices), a look-back (3/5/7/10 years, Max
             or a custom date range), how many years to test on, an
             optional cap per index, and a slider that moves the
             look-back window through history
  Headline   the best risk-adjusted mix for that window vs the Nifty 500
  Chart      the frontier, every index, the Nifty 500, the best and
             lowest-risk mixes, and where they landed next (dashed)
  Mixes      weights and numbers for the two mixes and the Nifty 500
  Next       how the mixes did over the following years, as a table and
             as ₹1 lakh grown
  Track      every window tested the same way, and how the best mix's
             weights have moved over time

Calculations live in core/frontier.py.
"""

import numpy as np
import pandas as pd
import streamlit as st

from charts import frontier_vega as fc
from core import fbi_metrics as fm
from core import frontier as F
from views.factor_indexes import CSS as FBI_CSS

LOOKBACKS = {"3Y": 3, "5Y": 5, "7Y": 7, "10Y": 10, "Max": None, "Custom": "custom"}
FORWARDS = {"3Y": 3, "5Y": 5, "7Y": 7}
CAPS = {"No cap": None, "50%": 0.5, "35%": 0.35}
MAX_CUSTOM = 10
SHORT = {
    "NIFTY500 GROWTH 50": "Growth", "NIFTY500 VALUE 50": "Value",
    "NIFTY500 QUALITY 50": "Quality", "NIFTY500 LOW VOLATILITY 50": "Low Vol",
    "NIFTY500 MOMENTUM 50": "Momentum", "NIFTY500 EQUAL WEIGHT": "Equal Weight",
    "NIFTY 500": "Nifty 500",
}

CSS = """
<style>
.ef-mixes {display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:16px; margin:1.2rem 0 0.4rem 0;}
.ef-card {border:1px solid #E6E9ED; border-top:3px solid var(--c); border-radius:10px; padding:16px 18px 14px 18px;}
.ef-card h4 {font-size:0.9rem; font-weight:600; color:var(--c); margin:0 0 10px 0; padding:0;}
.ef-nums {display:flex; gap:22px; margin-bottom:12px;}
.ef-nums b {display:block; font-size:1.35rem; font-weight:600; color:#1B2533; line-height:1.15; font-variant-numeric:tabular-nums;}
.ef-nums small {font-size:0.75rem; color:#8A939E;}
.ef-bar {display:flex; height:10px; border-radius:5px; overflow:hidden; background:#F3F4F6; margin:2px 0 8px 0;}
.ef-bar i {display:block; height:100%;}
.ef-w {display:flex; flex-wrap:wrap; gap:3px 12px; font-size:0.8rem; color:#4A5562;}
.ef-w span {display:inline-flex; align-items:center; font-variant-numeric:tabular-nums;}
.ef-w i {display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:5px;}
.ef-w b {font-weight:600; margin-left:4px; color:#1B2533;}
.ef-table {width:100%; border-collapse:collapse; font-size:0.92rem; margin-top:0.8rem;}
.ef-table th {text-align:right; font-weight:500; color:#8A939E; font-size:0.74rem; letter-spacing:0.04em;
  text-transform:uppercase; padding:8px 10px; border-bottom:1px solid #E6E9ED;}
.ef-table th:first-child, .ef-table td:first-child {text-align:left;}
.ef-table td {padding:10px 10px; border-bottom:1px solid #F0F2F5; color:#1B2533; text-align:right;
  font-variant-numeric:tabular-nums;}
.ef-table td.muted {color:#8A939E;}
.ef-table .dot {display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px;}
.ef-table .was {display:block; font-size:0.74rem; color:#9AA3AE;}
.ef-verdict {display:inline-block; font-size:0.76rem; font-weight:600; padding:2px 9px; border-radius:999px;
  margin-left:8px; vertical-align:2px; letter-spacing:0.02em;}
.ef-verdict.yes {background:#EEF5EA; color:#4E7A43;} .ef-verdict.no {background:#FBEDEA; color:#A5443A;}
.ef-verdict.wait {background:#FBF3E4; color:#9A6B1E;}
.ef-window {font-size:0.82rem; color:#6B7480; margin:0.1rem 0 0 0;}
.ef-window b {color:#1B2533; font-weight:600;}
.ef-stat {display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin:1rem 0 0.6rem 0;}
.ef-stat div {background:#F7F8FA; border-radius:10px; padding:12px 14px;}
.ef-stat b {display:block; font-size:1.5rem; font-weight:600; color:#1B2533; line-height:1.1;}
.ef-stat small {font-size:0.78rem; color:#6B7480;}
.st-key-ef_steps button {border-radius:999px !important; min-height:0 !important; padding:0.15rem 0.55rem !important;}
</style>
"""


# ---------------------------------------------------------------------
# labels and formatting
# ---------------------------------------------------------------------

def _label(name):
    return SHORT.get(name, fm.pretty_name(name))


def _pct(x, d=1):
    return fm.fmt_pct(x, decimals=d)


def _weights_list(names, w, min_w=0.005):
    order = np.argsort(-w)
    return [(names[i], w[i]) for i in order if w[i] >= min_w]


def _mix_phrase(names, w):
    parts = _weights_list(names, w, 0.02)
    if len(parts) == 1:
        return f"all in <b>{_label(parts[0][0])}</b>"
    txt = [f"{v * 100:.0f}% {_label(n)}" for n, v in parts]
    return "<b>" + (", ".join(txt[:-1]) + " and " + txt[-1]) + "</b>"


def _weight_text_fn(names):
    def fn(ws):
        return [" · ".join(f"{_label(n)} {v * 100:.0f}%" for n, v in _weights_list(names, w, 0.02))
                for w in ws]
    return fn


def _months(a, b):
    return (b.year - a.year) * 12 + b.month - a.month + 1


def _span(a, b):
    return f"{a:%b %Y} to {b:%b %Y}"


def _finite(x):
    """Spec with any NaN/inf replaced by null: the browser's JSON parser
    rejects NaN, which would break the whole chart."""
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def _vega(chart):
    st.vega_lite_chart(_finite(chart.to_dict()), theme=None, width="stretch")


def _lab(t):
    st.markdown(f"<p class='fbi-label'>{t}</p>", unsafe_allow_html=True)


def _note(t):
    st.markdown(f"<p class='fbi-note'>{t}</p>", unsafe_allow_html=True)


def _headline(t):
    st.markdown(f"<p class='fbi-headline'>{t}</p>", unsafe_allow_html=True)


def _section():
    st.markdown("<div class='fbi-section'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# page
# ---------------------------------------------------------------------

def render():
    st.markdown(FBI_CSS + CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='fbi-eyebrow'>Efficient Frontier</div>"
        "<div class='fbi-title'>Which mix gave the most return for the risk, and did it last?</div>"
        "<div class='fbi-sub'>Find the best risk-adjusted mix of Nifty indices over any stretch of "
        "history, slide that window through time, and see how the mix did in the years that followed.</div>",
        unsafe_allow_html=True,
    )

    universe = fm.equity_universe()
    all_names = universe["indexName"].tolist()

    with st.container(border=True):
        c1, c2 = st.columns([2.2, 3], vertical_alignment="bottom")
        with c1:
            mode = st.segmented_control("Indices", ["Nifty 500 factors", "Custom set"],
                                        default="Nifty 500 factors", key="ef_mode") or "Nifty 500 factors"
        names = [n for n in F.FACTOR_SET if n in all_names]
        if mode == "Custom set":
            with c2:
                pick = st.multiselect(
                    "Choose 2 to 10 indices", [n for n in all_names if n != F.BENCHMARK],
                    default=names,
                    format_func=fm.pretty_name, max_selections=MAX_CUSTOM, key="ef_custom",
                    placeholder="Type to add a Nifty index")
            names = list(pick)
        else:
            with c2:
                st.markdown("<p class='ef-window' style='margin-bottom:0.55rem'>Growth, Value, Quality, "
                            "Low Vol, Momentum and Equal Weight from the Nifty 500, compared with the "
                            "<b>Nifty 500</b> itself.</p>", unsafe_allow_html=True)

        d1, d2, d3 = st.columns([3.2, 1.9, 1.9], vertical_alignment="bottom")
        with d1:
            lb_key = st.segmented_control("Look-back", list(LOOKBACKS), default="5Y", key="ef_lb",
                                          help="The stretch of history the frontier is built from.") or "5Y"
        with d2:
            fw_key = st.segmented_control("Then test on the next", list(FORWARDS), default="5Y",
                                          key="ef_fw") or "5Y"
        with d3:
            cap_key = st.segmented_control("Max in one index", list(CAPS), default="No cap", key="ef_cap",
                                           help="Without a cap the best mix is often a single index. "
                                           "A cap forces it to spread out.") or "No cap"

    if len(names) < 2:
        _headline("Pick at least two indices to build a frontier.")
        return

    names_t = tuple(names)
    rets, _ = F.monthly_returns(names_t)
    if len(rets) < 24:
        _headline("These indices share less than two years of history, too little for a frontier. "
                  "Try dropping the newest one.")
        return

    fwd = FORWARDS[fw_key]
    cap = CAPS[cap_key]
    lookback = LOOKBACKS[lb_key]
    first, last = rets.index[0], rets.index[-1]

    # ---- the window --------------------------------------------------
    with st.container(border=False):
        if lookback == "custom":
            start, end = _custom_range(rets)
        elif lookback is None:
            start, end = first, last
            st.markdown(f"<p class='ef-window'>Using all the shared history: <b>{_span(first, last)}</b>.</p>",
                        unsafe_allow_html=True)
        else:
            if len(rets) < lookback * 12:
                _headline(f"These indices only share {len(rets) // 12} years of history, less than a "
                          f"{lookback}-year look-back. Pick a shorter one.")
                return
            start, end = _slider(rets, lookback)
    if start is None:
        return

    o = F.analyse_window(names_t, start, end, fwd, cap)
    fn = _weight_text_fn(names)

    _summary_headline(o, names)

    has_next = "landed" in o
    t1, t2 = st.columns([4, 1.6], vertical_alignment="bottom")
    with t1:
        _lab(f"The efficient frontier, {_span(o['start'], o['end'])}")
    with t2:
        show_next = st.toggle(f"Show the next {fwd} years", value=True, key="ef_next",
                              disabled=not has_next,
                              help="Dashed: the frontier those years actually offered. Hollow circles: "
                              "where the best mix and the Nifty 500 landed.")
    chart = fc.frontier_chart(o, names, _label, fn, show_next and has_next)
    _vega(chart)
    _note("Each faint dot is a random mix of these indices. The navy line is the frontier: no mix "
          "gives more return for its risk. Hover the line to see the mix at any point.")

    _mix_cards(o, names)

    _section()
    _next_years(o, names, fwd)

    if lookback in (None, "custom"):
        _section()
        _note("Pick a 3, 5, 7 or 10 year look-back to test every window in history the same way.")
    else:
        _section()
        _track(names_t, lookback, fwd, cap, o["end"])

    st.markdown(
        f"<p class='fbi-source'>Source: NSE Indices via FinAPI, total return in INR, month-end levels to "
        f"{last:%b %Y}. Return is the average monthly return × 12; risk is monthly volatility × √12. "
        f"Long only, fully invested. Best risk-adjusted = highest Sharpe ratio, with the Nifty 1D Rate "
        f"index as the risk-free rate ({F.RF_FALLBACK:.1f}% a year before it starts in 2011). In the "
        f"years after a window, each mix is held at fixed weights and rebalanced monthly, before costs "
        f"and taxes. Past results don't predict future ones.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# window controls
# ---------------------------------------------------------------------

def _step(delta, n):
    i = st.session_state.get("ef_win_i", n - 1) + delta
    st.session_state["ef_win_i"] = max(0, min(n - 1, i))


def _slider(rets, years):
    ends = F.window_end_options(rets, years)
    n_back = years * 12
    pos = {d: rets.index.get_loc(d) for d in ends}
    starts = {d: rets.index[pos[d] - n_back + 1] for d in ends}
    labels = [f"{starts[d]:%b %Y} – {d:%b %Y}" for d in ends]

    # keep the slider valid when the look-back or the set changes
    sig = (years, ends[0], ends[-1], len(ends))
    if st.session_state.get("ef_win_sig") != sig:
        old = st.session_state.get("ef_win_end")
        st.session_state["ef_win_i"] = (min(range(len(ends)), key=lambda i: abs((ends[i] - old).days))
                                        if old is not None else len(ends) - 1)
        st.session_state["ef_win_sig"] = sig
    st.session_state["ef_win_i"] = max(0, min(len(ends) - 1, st.session_state.get("ef_win_i", len(ends) - 1)))

    s1, s2 = st.columns([10, 1.1], vertical_alignment="bottom")
    with s1:
        i = st.select_slider(
            f"Slide the {years}-year window through history", options=list(range(len(ends))),
            format_func=lambda k: labels[k], key="ef_win_i")
    with s2:
        with st.container(key="ef_steps", horizontal=True, gap="small"):
            st.button("", icon=":material/chevron_left:", key="ef_prev", on_click=_step,
                      args=(-1, len(ends)), disabled=i == 0, help="Three months earlier")
            st.button("", icon=":material/chevron_right:", key="ef_next_btn", on_click=_step,
                      args=(1, len(ends)), disabled=i == len(ends) - 1, help="Three months later")
    st.session_state["ef_win_end"] = ends[i]
    return starts[ends[i]], ends[i]


def _custom_range(rets):
    first, last = rets.index[0], rets.index[-1]
    lo = (first - pd.offsets.MonthBegin(1)).date()
    default = (max(lo, (last - pd.DateOffset(years=5)).date()), last.date())
    picked = st.date_input("From and to", value=default, min_value=lo, max_value=last.date(),
                           key="ef_range", format="DD/MM/YYYY")
    if not isinstance(picked, (list, tuple)) or len(picked) != 2:
        _note("Pick an end date too.")
        return None, None
    a, b = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
    months = rets.index[(rets.index > a) & (rets.index <= b + pd.offsets.MonthEnd(0))]
    if len(months) < 24:
        _note("Pick at least two years so the frontier has enough months to work with.")
        return None, None
    st.markdown(f"<p class='ef-window'>Window: <b>{_span(months[0], months[-1])}</b> "
                f"({len(months) // 12} yrs {len(months) % 12} mo), whole months only.</p>",
                unsafe_allow_html=True)
    return months[0], months[-1]


# ---------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------

def _summary_headline(o, names):
    rb, vb = o["mix"]["best"]
    b = o["points"].loc[F.BENCHMARK]
    text = (f"From {_span(o['start'], o['end'])}, the best risk-adjusted mix was "
            f"{_mix_phrase(names, o['weights']['best'])}: {_pct(rb)} a year at {_pct(vb)} risk, "
            f"against the Nifty 500's {_pct(b['ret'])} at {_pct(b['risk'])}.")
    _headline(text)


def _bar(names, w):
    segs, keys = [], []
    for n, v in _weights_list(names, w):
        c = fc.WEIGHT_COLORS[names.index(n) % len(fc.WEIGHT_COLORS)]
        segs.append(f"<i style='width:{v * 100:.2f}%;background:{c}'></i>")
        keys.append(f"<span><i style='background:{c}'></i>{_label(n)}<b>{v * 100:.0f}%</b></span>")
    return f"<div class='ef-bar'>{''.join(segs)}</div><div class='ef-w'>{''.join(keys)}</div>"


def _mix_cards(o, names):
    cards = []
    for k in ("best", "low"):
        r, v = o["mix"][k]
        cards.append(
            f"<div class='ef-card' style='--c:{fc.MIX_COLORS[k]}'><h4>{fc.MIX_NAMES[k]}</h4>"
            f"<div class='ef-nums'><div><b>{_pct(r)}</b><small>Return a year</small></div>"
            f"<div><b>{_pct(v)}</b><small>Risk</small></div>"
            f"<div><b>{o['sharpe_in'][k]:.2f}</b><small>Sharpe</small></div></div>"
            f"{_bar(names, o['weights'][k])}</div>")
    b = o["points"].loc[F.BENCHMARK]
    cards.append(
        f"<div class='ef-card' style='--c:{fc.GREY}'><h4>Nifty 500</h4>"
        f"<div class='ef-nums'><div><b>{_pct(b['ret'])}</b><small>Return a year</small></div>"
        f"<div><b>{_pct(b['risk'])}</b><small>Risk</small></div>"
        f"<div><b>{o['sharpe_in']['bench']:.2f}</b><small>Sharpe</small></div></div>"
        f"<div class='ef-w' style='margin-top:4px'>The market to beat. Risk-free rate over this window: "
        f"{_pct(o['rf'])} a year.</div></div>")
    st.markdown(f"<div class='ef-mixes'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _next_years(o, names, fwd):
    if "fwd" not in o:
        _headline(f"Did it work over the next {fwd} years? "
                  f"<span class='ef-verdict wait'>Not known yet</span>")
        if o["fwd_months"]:
            _note(f"Only {o['fwd_months']} months of data come after this window. Slide it earlier "
                  f"to see how a mix chosen then held up.")
        else:
            _note("Nothing in the data comes after this window yet. Slide it earlier to see how a "
                  "mix chosen then held up.")
        return

    f = o["fwd"]
    best, bench = f["best"], f["bench"]
    partial = not o["fwd_full"]
    span = _span(o["fwd_start"], o["fwd_end"])
    beat_ret = best["cagr"] > bench["cagr"]
    beat_sh = best["sharpe"] > bench["sharpe"]
    if beat_ret and beat_sh:
        verdict, cls = "Yes", "yes"
    elif beat_ret or beat_sh:
        verdict, cls = "Partly", "wait"
    else:
        verdict, cls = "No", "no"
    if partial:
        verdict += ", so far"
    when = "so far" if partial else f"over the next {fwd} years"
    _headline(f"Did it work {when}? <span class='ef-verdict {cls}'>{verdict}</span>")
    gap = best["cagr"] - bench["cagr"]
    txt = (f"Held from {span}, the best mix returned <b>{_pct(best['cagr'])} a year</b> against the "
           f"Nifty 500's {_pct(bench['cagr'])}, {'ahead' if gap >= 0 else 'behind'} by "
           f"{abs(gap):.1f} points. ")
    exp = o["mix"]["best"][0]
    txt += (f"The window had promised about {_pct(exp)}; "
            + ("it delivered more." if best["avg"] >= exp else "it delivered less, as the best mix usually does once the "
               "period that made it look best is over."))
    _note(txt)

    rows = []
    for k in ("best", "low", "equal", "bench"):
        r = f[k]
        was = o["mix"][k] if k != "bench" else (o["points"].loc[F.BENCHMARK, "ret"], o["points"].loc[F.BENCHMARK, "risk"])
        sh_was = o["sharpe_in"][k]
        rows.append(
            f"<tr><td><i class='dot' style='background:{fc.MIX_COLORS[k]}'></i>{fc.MIX_NAMES[k]}</td>"
            f"<td><b>{_pct(r['cagr'])}</b></td>"
            f"<td>{_pct(r['vol'])}<span class='was'>was {_pct(was[1])}</span></td>"
            f"<td>{r['sharpe']:.2f}<span class='was'>was {sh_was:.2f}</span></td>"
            f"<td>{_pct(r['worst'], 0)}</td>"
            f"<td class='muted'>₹{r['growth'].iloc[-1]:.2f}L</td></tr>")
    st.markdown(
        "<table class='ef-table'><thead><tr><th>Next " + (f"{o['fwd_months']} months" if partial else f"{fwd} years")
        + "</th><th>Return a year</th><th>Risk</th><th>Sharpe</th><th>Worst fall</th><th>₹1L became</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>", unsafe_allow_html=True)
    _note("The equal mix holds every index in the set equally, the simplest alternative to optimising.")

    _lab(f"₹1 lakh invested at the start of {o['fwd_start']:%b %Y}")
    g = {k: f[k]["growth"] for k in ("best", "low", "equal", "bench")}
    _vega(fc.growth_chart(g, ["best", "low", "equal", "bench"]))


def _track(names_t, lookback, fwd, cap, selected_end):
    with st.spinner("Testing every window…"):
        w, t = F.track_record(names_t, lookback, fwd, cap)
    _headline(f"Every {lookback}-year window, tested on the {fwd} years after it.")
    if t.empty:
        _note(f"There isn't yet {lookback + fwd} years of shared history to test even one window.")
    else:
        n = len(t)
        beat = int((t["best"] > t["bench"]).sum())
        beat_sh = int((t["best_sharpe"] > t["bench_sharpe"]).sum())
        beat_eq = int((t["best"] > t["equal"]).sum())
        eq_beat = int((t["equal"] > t["bench"]).sum())
        stats = [
            (f"{beat} of {n}", "windows where the best mix beat the Nifty 500 on return"),
            (f"{beat_sh} of {n}", "beat it on risk-adjusted return (Sharpe)"),
            (f"{beat_eq} of {n}", "beat a plain equal mix of the same indices"),
            (f"{(t['best'] - t['bench']).median():+.1f} pts", "median lead over the Nifty 500, a year"),
        ]
        st.markdown("<div class='ef-stat'>" + "".join(f"<div><b>{a}</b><small>{b}</small></div>" for a, b in stats)
                    + "</div>", unsafe_allow_html=True)
        _lab(f"Best mix minus Nifty 500, return a year over the next {fwd} years, by window end")
        _vega(fc.track_chart(t, selected_end))
        _note(f"Windows ending {t.index[0]:%b %Y} to {t.index[-1]:%b %Y}, every three months. Neighbouring "
              f"windows share most of their months, so they are not {n} independent tests. "
              f"For comparison, the equal mix beat the Nifty 500 in {eq_beat} of {n}.")

    if not w.empty:
        _section()
        _headline("How the best mix has shifted.")
        _lab(f"Weights of the best risk-adjusted mix in each {lookback}-year window")
        _vega(fc.weights_chart(w, _label, selected_end))
        _note("The dashed line marks the window chosen above. Big jumps mean the 'best' mix depended "
              "heavily on which years you happened to look at.")
