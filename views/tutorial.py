"""
Page tutorials: a short slide deck for every page, opened from a
"Take the tour" button under each page title, and from a small
"How to read this tab" link inside each tab (which opens the deck at
that tab's chapter).

  launcher(page)          the tour button, placed under a page header
  tab_link(page, chapter) the in-tab link
  maybe_open(page)        called once per run from app.py, before the
                          page renders: applies any "try it" prefill and
                          shows the deck if one is open for this page

Decks are built from live data where it helps (core/tutorial_data.py):
the Factor Analysis deck walks through HDFC Flexi Cap, the fund from the
PRISM launch post on my Substack. Quizzes give instant feedback. Game
decks explain how to play and never give away an ending.

Design: light and minimal, navy for right/better, rust for wrong/losses.
"""

import altair as alt
import pandas as pd
import streamlit as st

from core import tutorial_data as td

NAVY, RUST, INK, MUTED, FAINT, LINE, MIST = (
    "#1F4E79", "#B54A3C", "#17212D", "#66707C", "#98A1AC", "#E6EAEF", "#F4F6F9")

CSS = """
<style>
.tut-eyebrow {font-size:0.76rem; font-weight:600; color:#B07A2A; letter-spacing:0.02em; margin:0 0 0.3rem 0;}
.tut-title {font-size:1.45rem; font-weight:600; color:#17212D; line-height:1.22; letter-spacing:-0.015em;
  margin:0 0 0.7rem 0;}
.tut-body {font-size:0.98rem; line-height:1.6; color:#3A4552; margin:0 0 0.9rem 0;}
.tut-body b {color:#17212D; font-weight:600;}
.tut-flag {font-size:0.8rem; color:#B54A3C; margin:0 0 0.6rem 0;}
.tut-tiles {display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:0.4rem 0 1rem 0;}
.tut-tile {background:#F4F6F9; border-radius:12px; padding:12px 14px;}
.tut-tile small {display:block; font-size:0.75rem; color:#66707C; margin-bottom:4px;}
.tut-tile b {font-size:1.55rem; font-weight:600; color:#17212D; letter-spacing:-0.02em; font-variant-numeric:tabular-nums;}
.tut-tile span {display:block; font-size:0.78rem; color:#66707C; margin-top:3px;}
.tut-eq {display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:0.4rem 0 1rem 0;}
.tut-eq i {font-style:normal; color:#98A1AC; font-weight:600;}
.tut-chip {background:#F4F6F9; border-radius:999px; padding:5px 12px; font-size:0.86rem; color:#17212D;}
.tut-chip.lead {background:#1F4E79; color:#fff;} .tut-chip.alpha {background:#F3E6CF; color:#6B4A12;}
.tut-list {margin:0 0 1rem 0; padding:0; list-style:none;}
.tut-list li {display:grid; grid-template-columns:118px 1fr 1fr; gap:10px; padding:8px 0;
  border-bottom:1px solid #EEF1F4; font-size:0.9rem; color:#3A4552;}
.tut-list li b {color:#17212D; font-weight:600;}
.tut-list li.head {font-size:0.76rem; color:#98A1AC; padding-top:0;}
.tut-steps {counter-reset:s; margin:0.2rem 0 1rem 0; padding:0; list-style:none;}
.tut-steps li {counter-increment:s; position:relative; padding:8px 0 8px 38px; font-size:0.95rem;
  color:#3A4552; border-bottom:1px solid #EEF1F4; line-height:1.45;}
.tut-steps li::before {content:counter(s); position:absolute; left:0; top:7px; width:26px; height:26px;
  border-radius:50%; background:#1F4E79; color:#fff; font-size:0.8rem; font-weight:600;
  display:flex; align-items:center; justify-content:center;}
.tut-steps li b {color:#17212D;}
.tut-bars {margin:0.3rem 0 0.6rem 0;}
.tut-bar {display:grid; grid-template-columns:96px 1fr 64px; align-items:center; gap:10px; height:30px;}
.tut-bar .lab {font-size:0.86rem; color:#17212D;}
.tut-bar .val {font-size:0.86rem; color:#17212D; text-align:right; font-variant-numeric:tabular-nums;}
.tut-track {position:relative; height:100%;}
.tut-track .zero {position:absolute; left:50%; top:3px; bottom:3px; width:1px; background:#C9D0D8;}
.tut-track .fill {position:absolute; top:9px; height:12px; border-radius:3px;}
.tut-track .rng {position:absolute; top:14px; height:2px; background:#17212D; opacity:0.45;}
.tut-legend {font-size:0.78rem; color:#98A1AC; margin:0 0 1rem 0;}
.tut-ok {color:#1F4E79; font-size:0.94rem; line-height:1.5; margin:0.2rem 0 0.8rem 0;}
.tut-no {color:#B54A3C; font-size:0.94rem; line-height:1.5; margin:0.2rem 0 0.8rem 0;}
.tut-ok b, .tut-no b {font-weight:600;}
.tut-dots {display:flex; gap:5px; justify-content:center; align-items:center; height:100%; flex-wrap:wrap;}
.tut-dots span {width:7px; height:7px; border-radius:50%; background:#DDE2E8;}
.tut-dots span.on {background:#1F4E79; width:18px; border-radius:4px;}
.tut-dots span.done {background:#9FB7CF;}
.tut-hit {display:grid; grid-template-columns:repeat(20, 1fr); gap:3px; margin:0.3rem 0 0.4rem 0; max-width:420px;}
.tut-hit span {aspect-ratio:1; border-radius:2px; background:#E6EAEF;}
.tut-hit span.on {background:#1F4E79;}
.tut-svg {width:100%; max-width:520px; display:block; margin:0.2rem 0 0.9rem 0;}
[class*="st-key-tutnav"] button p {font-size:0.85rem;}
</style>
"""


# =====================================================================
# Opening and closing
# =====================================================================

def _open(page, step=0):
    """step: a slide index, or a chapter name to open at."""
    st.session_state["tut_page"] = page
    st.session_state["tut_step"] = step


def _close():
    st.session_state.pop("tut_page", None)
    st.session_state.pop("tut_step", None)


def launcher(page, label="Take the 1-minute tour"):
    """The tour button under a page header."""
    st.button(label, key=f"tut_launch_{page}", type="tertiary", icon=":material/school:",
              on_click=_open, args=(page, 0))


def tab_link(page, chapter):
    """A small link at the top of a tab that opens the deck at its chapter."""
    if page not in DECKS:
        return
    st.button("How to read this tab", key=f"tut_tab_{page}_{chapter}", type="tertiary",
              icon=":material/help:", on_click=_open, args=(page, chapter))


def maybe_open(page):
    """Call once per run, before the page renders."""
    for key, value in st.session_state.pop("tut_prefill", {}).items():
        st.session_state[key] = value
    if st.session_state.get("tut_page") == page and page in DECKS:
        title = DECKS[page]["title"]
        st.dialog(title, width="large", on_dismiss=_close)(_deck)(page)
    elif "tut_page" in st.session_state and st.session_state["tut_page"] != page:
        _close()                               # left the page with a deck open


# =====================================================================
# The deck
# =====================================================================

def _slides(page):
    """Slides are built lazily and cached per session, so live numbers
    load once, when the deck first opens."""
    cache = st.session_state.setdefault("_tut_slides", {})
    if page not in cache:
        with st.spinner("Loading a live example..."):
            cache[page] = DECKS[page]["build"]()
    return cache[page]


def _go(delta, n):
    st.session_state["tut_step"] = max(0, min(n - 1, st.session_state.get("tut_step", 0) + delta))


def _jump(i):
    st.session_state["tut_step"] = i


def _deck(page):
    st.markdown(CSS, unsafe_allow_html=True)
    slides = _slides(page)
    n = len(slides)
    step = st.session_state.get("tut_step", 0)
    if isinstance(step, str):                  # opened from a tab: jump to its chapter
        step = next((k for k, x in enumerate(slides) if x["chapter"] == step), 0)
        st.session_state["tut_step"] = step
    i = min(step, n - 1)
    s = slides[i]

    chapters = list(dict.fromkeys(x["chapter"] for x in slides))
    if len(chapters) > 1:
        with st.container(key=f"tutnav_{page}", horizontal=True, gap="small"):
            for ch in chapters:
                first = next(k for k, x in enumerate(slides) if x["chapter"] == ch)
                st.button(ch, key=f"tut_ch_{page}_{ch}", on_click=_jump, args=(first,),
                          type="primary" if ch == s["chapter"] else "secondary")

    in_ch = [k for k, x in enumerate(slides) if x["chapter"] == s["chapter"]]
    st.markdown(f"<div class='tut-eyebrow'>{s['chapter']} · {in_ch.index(i) + 1} of {len(in_ch)}</div>"
                f"<div class='tut-title'>{s['title']}</div>", unsafe_allow_html=True)
    if s.get("flag"):
        st.markdown(f"<div class='tut-flag'>{s['flag']}</div>", unsafe_allow_html=True)
    if s.get("body"):
        st.markdown(f"<div class='tut-body'>{s['body']}</div>", unsafe_allow_html=True)
    if s.get("html"):
        st.markdown(s["html"], unsafe_allow_html=True)
    if s.get("chart") is not None:
        st.altair_chart(s["chart"], theme=None, width="stretch")
    if s.get("after"):
        st.markdown(f"<div class='tut-body'>{s['after']}</div>", unsafe_allow_html=True)
    if s.get("quiz"):
        _quiz(page, i, s["quiz"])

    st.write("")
    b, mid, nx = st.columns([1, 2.4, 1], vertical_alignment="center")
    with b:
        st.button("Back", key=f"tut_back_{page}", icon=":material/arrow_back:", disabled=i == 0,
                  on_click=_go, args=(-1, n), width="stretch")
    with mid:
        dots = "".join(f"<span class='{'on' if k == i else 'done' if k < i else ''}'></span>"
                       for k in range(n))
        st.markdown(f"<div class='tut-dots'>{dots}</div>", unsafe_allow_html=True)
    with nx:
        if i < n - 1:
            st.button("Next", key=f"tut_next_{page}", type="primary", icon=":material/arrow_forward:",
                      icon_position="right", on_click=_go, args=(1, n), width="stretch")
        elif st.button(s.get("cta", "Got it"), key=f"tut_done_{page}", type="primary", width="stretch"):
            if s.get("prefill"):
                st.session_state["tut_prefill"] = s["prefill"]
            _close()
            st.rerun()


def _quiz(page, i, q):
    pick = st.pills(q["q"], q["options"], key=f"tut_q_{page}_{i}")
    if pick is None:
        st.markdown("<div class='tut-legend'>Pick an answer.</div>", unsafe_allow_html=True)
    elif pick == q["answer"]:
        st.markdown(f"<div class='tut-ok'><b>Right.</b> {q['why']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='tut-no'><b>Not quite.</b> {q.get('wrong', {}).get(pick, q['why'])}</div>",
                    unsafe_allow_html=True)


def slide(chapter, title, body=None, **extra):
    return {"chapter": chapter, "title": title, "body": body, **extra}


# =====================================================================
# Small visuals
# =====================================================================

def _pct(x, d=1, signed=False):
    s = f"{x:+.{d}f}%" if signed else f"{x:.{d}f}%"
    return s.replace("-", "−")


def _num(x, d=2, signed=True):
    return (f"{x:+.{d}f}" if signed else f"{x:.{d}f}").replace("-", "−")


def _tiles(items):
    return "<div class='tut-tiles'>" + "".join(
        f"<div class='tut-tile'><small>{a}</small><b>{b}</b><span>{c}</span></div>" for a, b, c in items
    ) + "</div>"


def _bars(rows, show_range=True):
    """Diverging bars around zero; navy if significant, grey if it could be noise."""
    span = max([0.6] + [max(abs(r["lo"]), abs(r["hi"])) for r in rows]) * 1.08

    def x(v):
        return 50 + 50 * max(-1, min(1, v / span))

    out = []
    for r in rows:
        c = r["coef"]
        left, right = sorted([x(0), x(c)])
        colour = NAVY if r["p"] < 0.05 else "#C3CAD2"
        rng = (f"<div class='rng' style='left:{x(r['lo']):.1f}%; width:{x(r['hi']) - x(r['lo']):.1f}%'></div>"
               if show_range else "")
        out.append(f"<div class='tut-bar'><div class='lab'>{r['label']}</div><div class='tut-track'>"
                   f"<div class='zero'></div><div class='fill' style='left:{left:.1f}%; "
                   f"width:{max(right - left, 0.6):.1f}%; background:{colour}'></div>{rng}</div>"
                   f"<div class='val'>{_num(c)}</div></div>")
    legend = ("Navy: statistically significant. Grey: could be noise. The thin line is the 95% range."
              if show_range else "Navy: statistically significant. Grey: could be noise.")
    return f"<div class='tut-bars'>{''.join(out)}</div><div class='tut-legend'>{legend}</div>"


def _hit_strip(pct):
    on = round(pct / 5)
    return "<div class='tut-hit'>" + "".join(
        f"<span class='{'on' if k < on else ''}'></span>" for k in range(20)) + "</div>"


def _rolling_chart(series, marker=None, label="Value exposure"):
    df = pd.DataFrame(series, columns=["Date", "v", "p"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["Evidence"] = df["p"].map(lambda p: "Significant" if p < 0.05 else "Could be noise")
    base = alt.Chart(df).encode(x=alt.X("Date:T", title=None, axis=alt.Axis(format="%Y", grid=False,
                                                                           tickCount="year", labelOverlap=True,
                                                                           labelColor=MUTED, domainColor=LINE,
                                                                           tickColor=LINE)))
    line = base.mark_line(color=NAVY, strokeWidth=1.6, opacity=0.5).encode(
        y=alt.Y("v:Q", title=label, axis=alt.Axis(gridColor="#F0F2F5", labelColor=MUTED, titleColor=MUTED,
                                                  domain=False, tickCount=5, titleFontWeight="normal")))
    pts = base.mark_circle(size=22).encode(
        y="v:Q",
        color=alt.Color("Evidence:N", scale=alt.Scale(domain=["Significant", "Could be noise"],
                                                      range=[NAVY, "#C3CAD2"]),
                        legend=alt.Legend(orient="top", title=None, labelColor=MUTED)),
        tooltip=[alt.Tooltip("Date:T", format="%b %Y", title="Window ending"),
                 alt.Tooltip("v:Q", format=".2f", title=label)])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#C9D0D8").encode(y="y:Q")
    layers = [zero, line, pts]
    if marker is not None:
        m = pd.DataFrame({"Date": [marker[0]], "t": [marker[1]]})
        layers += [alt.Chart(m).mark_rule(color=RUST, strokeDash=[4, 3]).encode(x="Date:T"),
                   alt.Chart(m).mark_text(color=RUST, align="left", dx=5, dy=-70, fontSize=11)
                   .encode(x="Date:T", text="t:N")]
    return alt.layer(*layers).properties(height=210).configure_view(stroke=None).configure(
        font="Inter, sans-serif")


DRAWDOWN_SVG = """
<svg class='tut-svg' viewBox='0 0 520 224' xmlns='http://www.w3.org/2000/svg' font-family='Inter, sans-serif'>
  <line x1='20' y1='50' x2='505' y2='50' stroke='#C9D0D8' stroke-dasharray='4 4'/>
  <text x='22' y='42' font-size='11' fill='#98A1AC'>previous high</text>
  <path d='M20 112 C60 92 95 52 130 50 C165 50 190 165 220 165 C250 165 270 140 300 115
           C340 80 370 55 400 50 C430 45 470 38 505 32' fill='none' stroke='#1F4E79' stroke-width='2.4'/>
  <circle cx='130' cy='50' r='4.5' fill='#1F4E79'/>
  <text x='130' y='37' font-size='11' fill='#17212D' text-anchor='middle'>peak</text>
  <circle cx='400' cy='50' r='4.5' fill='#1F4E79'/>
  <text x='400' y='37' font-size='11' fill='#17212D' text-anchor='middle'>back to the high</text>
  <circle cx='220' cy='165' r='4.5' fill='#B54A3C'/>
  <text x='220' y='183' font-size='11' fill='#B54A3C' text-anchor='middle'>trough</text>
  <line x1='220' y1='56' x2='220' y2='156' stroke='#B54A3C' stroke-width='1.2'
        marker-start='url(#dda)' marker-end='url(#dda)'/>
  <text x='228' y='98' font-size='11' fill='#B54A3C'>depth</text>
  <text x='228' y='111' font-size='11' fill='#B54A3C'>of the fall</text>
  <path d='M130 196 v6 h90 v-6 M220 202 h180 v-6' fill='none' stroke='#98A1AC'/>
  <text x='175' y='217' font-size='10.5' fill='#66707C' text-anchor='middle'>time to bottom</text>
  <text x='310' y='217' font-size='10.5' fill='#66707C' text-anchor='middle'>time to recover</text>
  <defs><marker id='dda' viewBox='0 0 10 10' refX='5' refY='5' markerWidth='5' markerHeight='5'
    orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10z' fill='#B54A3C'/></marker></defs>
</svg>"""

FRONTIER_SVG = """
<svg class='tut-svg' viewBox='0 0 520 220' xmlns='http://www.w3.org/2000/svg' font-family='Inter, sans-serif'>
  <line x1='40' y1='190' x2='505' y2='190' stroke='#C9D0D8'/><line x1='40' y1='15' x2='40' y2='190' stroke='#C9D0D8'/>
  <text x='505' y='208' font-size='11' fill='#66707C' text-anchor='end'>risk (volatility) →</text>
  <text x='14' y='20' font-size='11' fill='#66707C' transform='rotate(-90 14 20)' text-anchor='end'>return →</text>
  __DOTS__
  <path d='M120 150 C140 95 200 62 280 48 C340 40 410 36 480 34' fill='none' stroke='#1F4E79' stroke-width='2.4'/>
  <circle cx='121' cy='148' r='6' fill='#fff' stroke='#1F4E79' stroke-width='2'/>
  <text x='132' y='166' font-size='11' fill='#17212D'>lowest-risk mix</text>
  <path d='M262 38 l4 9 10 1 -8 6 3 10 -9 -5 -9 5 3 -10 -8 -6 10 -1z' fill='#E0B15C' stroke='#B07A2A'/>
  <text x='282' y='34' font-size='11' fill='#17212D'>best mix for the risk</text>
  <text x='392' y='26' font-size='11' fill='#1F4E79'>the frontier</text>
</svg>"""


def _frontier_svg():
    import random
    rnd = random.Random(4)
    dots = []
    for _ in range(170):
        x = rnd.uniform(130, 490)
        top = 150 - 116 * (1 - ((490 - x) / 360) ** 2.2) if x > 120 else 150
        y = rnd.uniform(top + 6, 185)
        dots.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='2.6' fill='#C3CAD2' opacity='0.8'/>")
    return FRONTIER_SVG.replace("__DOTS__", "".join(dots))


# =====================================================================
# Decks
# =====================================================================

MEANINGS = [
    ("Size", "small companies", "large companies"),
    ("Value", "cheap (value) stocks", "expensive (growth) stocks"),
    ("Profitability", "highly profitable firms", "less profitable firms"),
    ("Investment", "firms that invest conservatively", "firms that expand aggressively"),
    ("Momentum", "recent winners", "recent losers"),
]
# how a reliable tilt reads in a sentence: "a clear lean <phrase>"
WORD = {"SMB": ("toward small companies", "toward large companies"),
        "HML": ("toward value stocks", "toward growth stocks"),
        "RMW": ("toward highly profitable firms", "toward less profitable firms"),
        "CMA": ("toward firms that invest conservatively", "toward firms that expand aggressively"),
        "WML": ("toward recent winners", "away from recent winners")}


def _strength(c):
    a = abs(c)
    return "a slight" if a < 0.1 else "a clear" if a < 0.3 else "a strong"


def _factor_deck():
    ex = td.fund_example()
    flag = ("Live data didn't load just now, so these are illustrative numbers. "
            "Run the analysis to see the real ones." if ex["example"] else None)
    rows = {r["key"]: r for r in ex["factors"]}
    tilts = [r for r in ex["factors"] if r["key"] != "MKT_RF"]
    sig = sorted([r for r in tilts if r["p"] < 0.05], key=lambda r: -abs(r["coef"]))
    hml = rows.get("HML")

    if sig:
        read = "; ".join(
            f"<b>{r['label']} {_num(r['coef'])}</b>, {_strength(r['coef'])} lean "
            f"{WORD[r['key']][0] if r['coef'] > 0 else WORD[r['key']][1]}" for r in sig[:3])
        read = f"The reliable tilts: {read}. Everything grey is too uncertain to call."
    else:
        read = "None of the style tilts is reliably different from zero over this period."

    value_ok = hml is not None and hml["lo"] > 0
    value_q = {
        "q": "Is HDFC Flexi Cap's value tilt reliable?",
        "options": ["Yes, its range stays above zero", "No, its range crosses zero"],
        "answer": "Yes, its range stays above zero" if value_ok else "No, its range crosses zero",
        "why": (f"Value is {_num(hml['coef'])} with a 95% range of {_num(hml['lo'])} to {_num(hml['hi'])}. "
                + ("The whole range is positive, so the value lean is real, which fits the fund's "
                   "reputation under Prashant Jain." if value_ok else
                   "The range includes zero, so over this full period we can't say it leans to value."))
        if hml else "",
    }

    a, ap = ex["alpha"], ex["alpha_p"]
    alpha_read = (f"<b>{_pct(a, signed=True)} a year</b>, and statistically meaningful." if ap < 0.05 else
                  f"<b>{_pct(a, signed=True)} a year</b>, but well within the range of luck "
                  f"(p = {ap:.2f}). That's normal: most funds' alpha can't be told apart from zero.")

    roll = ex["rolling"].get("HML")
    roll_slides = []
    if roll:
        ex_d, ex_v = roll["exit"] if roll["exit"] else roll["last"]
        last_d, last_v = roll["last"]
        drift = last_v - ex_v
        if roll["exit"] and abs(drift) >= 0.1:
            story = (f"In the 3 years to <b>{ex_d:%b %Y}</b>, around Prashant Jain's exit, value exposure was "
                     f"<b>{_num(ex_v)}</b>. In the latest window, to {last_d:%b %Y}, it's <b>{_num(last_v)}</b>. "
                     + ("The value lean has faded under new management. That's style drift, and a "
                        "single full-period regression would have averaged it away." if drift < 0 else
                        "The value lean has grown stronger since."))
        else:
            story = (f"Value exposure has moved between {_num(min(v for _, v, _ in roll['series']))} and "
                     f"{_num(max(v for _, v, _ in roll['series']))} across windows, ending at "
                     f"<b>{_num(last_v)}</b> in the window to {last_d:%b %Y}.")
        roll_slides = [
            slide("Over time", "One number can hide a change of style",
                  "The full-period regression gives one average. <b>Over time</b> reruns it on every "
                  "3-year window, one window ending each month. Each dot below is one window for "
                  "HDFC Flexi Cap's value exposure. The dashed line marks mid-2022.",
                  chart=_rolling_chart(roll["series"], (td.JAIN_EXIT, "Jain exits")), flag=flag),
            slide("Over time", "Reading the line", story,
                  quiz={"q": "A fund's value line falls from 0.45 to 0.05 over three years, while R² stays high. "
                             "What most likely happened?",
                        "options": ["The manager changed style", "Value stocks crashed", "The fund got bigger"],
                        "answer": "The manager changed style",
                        "why": "Exposure measures how the fund moves with value stocks, not how value stocks did. "
                               "A falling line with a steady R² means the portfolio itself shifted.",
                        "wrong": {"Value stocks crashed": "A value crash would hurt returns, but exposure "
                                  "measures how closely the fund tracks value stocks, not how they performed.",
                                  "The fund got bigger": "Size can change a fund over time, but by itself it "
                                  "doesn't erase a value lean. A steady R² with a falling value line points "
                                  "to the portfolio changing style."}}),
        ]

    return [
        slide("The idea", "A fund is a recipe",
              "Every month, a fund's return can be split into ingredients: how much it moves with the "
              "market, and how much it leans toward small or large companies, value or growth, profitable "
              "firms, cautious investors and recent winners. Whatever the recipe can't explain is "
              "<b>alpha</b>: the manager's own skill, or luck.",
              html="<div class='tut-eq'><span class='tut-chip'>Fund return</span><i>=</i>"
                   "<span class='tut-chip lead'>Market</span><i>+</i><span class='tut-chip'>Size</span><i>+</i>"
                   "<span class='tut-chip'>Value</span><i>+</i><span class='tut-chip'>Profitability</span><i>+</i>"
                   "<span class='tut-chip'>Investment</span><i>+</i><span class='tut-chip'>Momentum</span><i>+</i>"
                   "<span class='tut-chip alpha'>Alpha</span></div>",
              after="Each ingredient gets a number, its <b>exposure</b>. This tour reads them for a real fund."),
        slide("The idea", f"Meet the test fund: {ex['name']}",
              "For years it was run by Prashant Jain, known as a value investor, until he left HDFC AMC "
              "in mid-2022. Do the numbers agree with the reputation? This is the same fund from the "
              "post launching PRISM on my Substack.",
              html=_tiles([("Fund", "Flexi cap", ex["plan"].replace(ex["name"], "").strip(" -") or "Direct plan"),
                           ("Months analysed", f"{ex['months']}", f"{ex['start']:%b %Y} to {ex['end']:%b %Y}"),
                           ("Model", "6 factors", "Fama-French 5 + Momentum")]), flag=flag),
        slide("Exposures", "Step 1: how much do the factors explain?",
              f"The <b>Explained by factors</b> card shows R². For {ex['name']} it's "
              f"<b>{ex['r2']:.0f}%</b>: that share of its monthly ups and downs is explained by the factors.",
              html=_tiles([("Explained by factors", f"{ex['r2']:.0f}%", "R² of the regression")]),
              after="Rule of thumb: above about 80%, the factors tell most of the story and the rest of the "
                    "page is trustworthy. Below about 60%, something else is driving the fund, such as "
                    "sector bets, cash or foreign stocks, so read the tilts with care.", flag=flag),
        slide("Exposures", "Step 2: market beta",
              f"Beta is the market exposure. {ex['name']}'s is <b>{_num(ex['beta'], signed=False)}</b>: it "
              f"moves about <b>{ex['beta'] * 100:.0f}%</b> as much as the market. Equity funds usually "
              "sit between 0.8 and 1.1. Lower means the fund carries cash or calmer stocks.",
              quiz={"q": "A fund has a beta of 1.2. The market falls 10%. From market exposure alone, "
                         "roughly how much would you expect it to fall?",
                    "options": ["8%", "10%", "12%"], "answer": "12%",
                    "why": "1.2 × 10% = 12%. A beta above 1 amplifies the market in both directions.",
                    "wrong": {"8%": "That would be a beta of 0.8. A beta of 1.2 amplifies the market: 1.2 × 10% = 12%.",
                              "10%": "That's a beta of exactly 1. Here it's 1.2, so 1.2 × 10% = 12%."}},
              flag=flag),
        slide("Exposures", "Step 3: read each tilt, sign first",
              "A <b>positive</b> number means the fund leans toward the first group, and a <b>negative</b> "
              "number means it leans toward the opposite group.",
              html="<ul class='tut-list'><li class='head'><span>Factor</span><span>Positive (+)</span>"
                   "<span>Negative (−)</span></li>"
                   + "".join(f"<li><b>{a}</b><span>{p}</span><span>{n}</span></li>" for a, p, n in MEANINGS)
                   + "</ul>"),
        slide("Exposures", "Then read the size",
              "The size of the number tells you how strong the lean is. As a rough guide on this page: "
              "under 0.1 is slight, 0.1 to 0.3 is a clear tilt, and above 0.3 is strong. A Momentum "
              "exposure of <b>+0.8</b> would mean the fund strongly chases recent winners. A Value of "
              "<b>−0.4</b> would mean a strong lean toward expensive, growth stocks.",
              quiz={"q": "A fund shows Size −0.35. What does it hold?",
                    "options": ["Mostly small companies", "Mostly large companies", "A mix, no lean"],
                    "answer": "Mostly large companies",
                    "why": "Negative size means the opposite of small: a strong lean toward large companies, "
                           "typical of a large-cap fund.",
                    "wrong": {"Mostly small companies": "A positive size number would mean small companies. "
                              "Negative points the other way: large companies.",
                              "A mix, no lean": "At −0.35 the lean is strong, toward large companies."}}),
        slide("Exposures", "Step 4: is it real, or noise?",
              "Every exposure is an estimate, so the chart draws a <b>95% range</b> around it. If the range "
              "crosses zero, the tilt can't be told apart from no tilt at all. Those bars are grey. Navy "
              "bars are statistically significant. The <b>Confidence</b> column says the same in words: "
              "strong evidence, some evidence, or could be noise.",
              html=_bars([{"label": "Momentum", "coef": 0.8, "lo": -0.3, "hi": 1.9, "p": 0.15},
                          {"label": "Value", "coef": 0.25, "lo": 0.12, "hi": 0.38, "p": 0.001}]),
              quiz={"q": "Momentum is +0.8, but its range runs from −0.3 to +1.9. What can you conclude?",
                    "options": ["A strong momentum fund", "Can't tell, it could be zero", "It avoids momentum"],
                    "answer": "Can't tell, it could be zero",
                    "why": "A big number with a range that crosses zero is not evidence. The smaller Value "
                           "tilt above, +0.25 with a tight range, is the more reliable signal."}),
        slide("Exposures", f"{ex['name']}'s tilts", read,
              html=_bars(tilts), quiz=value_q if hml else None, flag=flag),
        slide("Exposures", "Step 5: alpha, what's left over",
              f"Alpha is the return the factors don't explain. For {ex['name']} it's {alpha_read} "
              "A large alpha with weak evidence means nothing yet. A small alpha with strong evidence "
              "is rare and worth noticing.", flag=flag),
        *roll_slides,
        slide("Over time", "Choosing the window",
              "<b>1Y</b> reacts fast but is noisy. <b>3Y</b> is a good default. <b>5Y</b> is smooth but slow "
              "to show a change. Darker points are significant, and the shaded band is the 95% range. "
              "A tilt that stays dark across most windows is part of the fund's DNA. The headline above "
              "the chart tells you which tilts were significant in most windows."),
        slide("Details", "The raw numbers, if you want them",
              "<b>Growth of ₹1 lakh</b> shows the fund's path. <b>Full regression</b> lists every "
              "coefficient with its standard error, t-stat and p-value. A t-stat beyond about ±2, or a "
              "p-value under 0.05, is what makes a bar navy. Standard errors are Newey-West, which allows "
              "for monthly returns that aren't fully independent of each other. <b>Monthly returns used</b> "
              "shows the exact data behind the fit."),
        slide("Your turn", "How to analyse any fund in five steps",
              html="<ol class='tut-steps'>"
                   "<li><b>R²</b>: do the factors explain most of it? Above about 80%, trust the rest.</li>"
                   "<li><b>Beta</b>: how hard does it swing with the market?</li>"
                   "<li><b>Tilts</b>: sign for direction, size for strength.</li>"
                   "<li><b>Confidence</b>: ignore grey bars and ranges that cross zero.</li>"
                   "<li><b>Over time and alpha</b>: has the style stayed put, and is anything left over real?</li>"
                   "</ol>",
              after="Use <b>Portfolio</b> mode to read your whole mix of funds the same way.",
              cta=f"Analyse {ex['name']}", prefill={"fa_mode": "One fund", "fa_q": "hdfc flexi cap"}),
    ]


def _fbi_deck():
    ex = td.fbi_example()
    s = [slide("Overview", "Indices with a rule",
               "Factor and strategy indices pick stocks by a rule. <b>Nifty200 Momentum 30</b>, for example, "
               "holds the 30 stocks from the Nifty 200 with the strongest recent price trends. This page shows "
               "how such indices really behaved. The four controls at the top (<b>Index</b>, <b>Compare with</b>, "
               "<b>Benchmark</b>, <b>Period</b>) drive every tab.")]
    if ex:
        yrs = (ex["end"] - ex["start"]).days / 365.25
        grow = {k: (1 + ex["cagr"][k] / 100) ** yrs for k in ("a", "b")}
        s.append(slide("Overview", "Start with the headline",
                       f"Each tab opens with a sentence computed from the data. Over the full history since "
                       f"{ex['start']:%b %Y}, {ex['a']} returned <b>{_pct(ex['cagr']['a'])} a year</b> against "
                       f"{_pct(ex['cagr']['b'])} for the {ex['b']}.",
                       html=_tiles([(ex["a"], f"₹{grow['a']:.0f} lakh", "from ₹1 lakh"),
                                    (ex["b"], f"₹{grow['b']:.0f} lakh", "from ₹1 lakh")]),
                       after="The cards then add volatility and the worst fall. Return is only half the story."))
        h = ex["hit3"]
        s.append(slide("Returns", "Returns depend on when you start",
                       "A single return figure depends on its start date. <b>Rolling returns</b> look at every "
                       "3-year stretch instead and count how often one index won. "
                       f"{ex['a']} beat the {ex['b']} in <b>{h['pct']:.0f}%</b> of {h['n']} rolling 3-year "
                       f"periods, by a median of {h['median']:.1f} percentage points a year.",
                       html=_hit_strip(h["pct"]) + "<div class='tut-legend'>Each square is 5% of the "
                       "rolling periods. Navy means it beat the benchmark.</div>",
                       quiz={"q": "Which tells you more about consistency?",
                             "options": ["Return since launch", "Share of rolling periods it won"],
                             "answer": "Share of rolling periods it won",
                             "why": "One start-to-end return can be flattered by a lucky start or end date. "
                                    "Rolling periods test every start date."}))
        s.append(slide("Returns", "Calendar years",
                       "Below the rolling chart, the year-by-year bars show the bad years at a glance. Look "
                       "for how often a winner over the full period still lost badly in a single year."))
        wa, wb = ex["worst"]["a"], ex["worst"]["b"]

        def ep(w):
            return (f"{_pct(w['depth'])} from {w['peak']:%b %Y}, back to its peak by {w['recovery']:%b %Y}"
                    if w["recovery"] is not None else f"{_pct(w['depth'])} from {w['peak']:%b %Y}, not recovered yet")
        s.append(slide("Risk", "What did the return cost?",
                       f"<b>{ex['a']}</b>'s worst fall was {ep(wa)}. The <b>{ex['b']}</b>: {ep(wb)}. The higher "
                       "return didn't come free. The Risk tab shows every fall from a previous high and the "
                       "worst episode."))
        s.append(slide("Risk", "Upside and downside capture",
                       f"In months the {ex['b']} rose, {ex['a']} captured <b>{ex['up']:.0f}%</b> of its gains. In "
                       f"months it fell, it took <b>{ex['down']:.0f}%</b> of the losses. The ideal is above "
                       "100% up and below 100% down.",
                       quiz={"q": "Fund A captures 90% up and 70% down. Fund B captures 110% up and 120% down. "
                                  "Which protects you better in falls?",
                             "options": ["Fund A", "Fund B"], "answer": "Fund A",
                             "why": "Fund A takes only 70% of the falls. Fund B falls more than the market."}))
    s += [
        slide("Hit ratio", "Does the rule beat where it came from?",
              "Every strategy index is built from a parent index: Momentum 30 from the Nifty 200, Value 50 "
              "from the Nifty 500. The <b>Hit ratio</b> tab shows the share of rolling 1, 3, 5 and 7-year "
              "periods in which each strategy beat its own parent. Click any number to see the periods "
              "behind it.",
              after="If a factor premium is real, the hit ratio usually rises as the window gets longer."),
        slide("Market map", "The whole field at once",
              "The <b>Risk and return</b> view plots every index in a category: further right is bumpier, "
              "higher up is better. <b>Year by year</b> is the quilt: each column is a year, ranked best "
              "to worst.",
              quiz={"q": "In the quilt, would you expect one factor to top the ranking every year?",
                    "options": ["Yes, the best one does", "No, leadership rotates"],
                    "answer": "No, leadership rotates",
                    "why": "Leadership rotates as cycles change. That's the case for holding more than one "
                           "factor rather than betting on last year's winner."}),
        slide("Your turn", "Judge any index in six steps",
              html="<ol class='tut-steps'><li><b>Return</b> against the benchmark.</li>"
                   "<li><b>Consistency</b>: the share of rolling periods it won.</li>"
                   "<li><b>Pain</b>: the worst fall and how long recovery took.</li>"
                   "<li><b>Capture</b>: how much of the ups and downs it took.</li>"
                   "<li><b>Hit ratio</b>: does it beat its own parent?</li>"
                   "<li><b>Market map</b>: where it sits among its peers.</li></ol>"),
    ]
    return s


def _drawdown_deck():
    ex = td.drawdown_example()
    s = [
        slide("The idea", "What's a drawdown?",
              "A drawdown is the fall from a previous high. It runs until the investment closes back above "
              "that high. Three things matter: how <b>deep</b>, how long to the bottom, and how long the way "
              "back took.", html=DRAWDOWN_SVG),
        slide("The idea", "Falls and recoveries aren't symmetric",
              quiz={"q": "An investment falls 50%. How much must it rise to get back to where it was?",
                    "options": ["50%", "75%", "100%"], "answer": "100%",
                    "why": "₹100 falls to ₹50. Getting back to ₹100 means doubling, a 100% gain. A −20% fall "
                           "needs +25%, −33% needs +50%, and −75% needs +300%."}),
    ]
    if ex:
        sc, nf = ex["NIFTY SMALLCAP 250"], ex["NIFTY 50"]

        def yrs(a, b):
            return f"{(b - a).days / 365.25:.1f} years"
        rec_sc = f"back to its peak by <b>{sc['recovery']:%b %Y}</b>, {yrs(sc['peak'], sc['recovery'])} after it started" \
            if sc["recovery"] is not None else "not back to its peak yet"
        rec_nf = f"recovered by {nf['recovery']:%b %Y}, {yrs(nf['peak'], nf['recovery'])} after its peak" \
            if nf["recovery"] is not None else "not recovered yet"
        s.append(slide("The idea", "A real one",
                       f"The <b>{sc['name']}</b> fell <b>{_pct(sc['depth'])}</b> from {sc['peak']:%b %Y} to "
                       f"{sc['trough']:%b %Y}, and got {rec_sc}. The {nf['name']} fell {_pct(nf['depth'])} and "
                       f"{rec_nf}. Smaller companies brought a deeper and longer fall.",
                       html=_tiles([(sc["name"], _pct(sc["depth"]), "worst fall"),
                                    (nf["name"], _pct(nf["depth"]), "worst fall")])))
    s += [
        slide("Reading the page", "Pick what to compare",
              "Add up to ten indices or mutual funds. <b>Period</b> sets how far back to look. With "
              "<b>Start dates</b> set to <b>Same for all</b>, everything is compared over the same years. "
              "<b>Each from its own start</b> shows each one's full history."),
        slide("Reading the page", "The chart and the table",
              "The line sits at <b>0%</b> whenever it's at a new high. The further it dips, the deeper the fall. "
              "Width matters as much as depth: a long, shallow dip can test patience more than a sharp one. "
              "The table at the bottom lists the worst falls, with dates and how long each recovery took."),
        slide("Your turn", "Before you invest, ask",
              html="<ol class='tut-steps'><li>How <b>deep</b> was the worst fall?</li>"
                   "<li>How long did it take to <b>recover</b>?</li>"
                   "<li>Is it in a fall <b>right now</b>?</li>"
                   "<li>Could you have <b>sat through it</b> without selling?</li></ol>",
              after="For the last question, try the game <b>Can You Handle It?</b>"),
    ]
    return s


def _frontier_deck():
    ex = td.frontier_example()
    s = [
        slide("The idea", "Every dot is a mix",
              "Combine a few indices in different weights and each mix has a risk (how bumpy it was) and a "
              "return. The <b>frontier</b> is the top edge: for each level of risk, the most return any mix "
              "achieved. The gold star is the best mix for the risk, the highest return above cash per unit "
              "of risk (the Sharpe ratio).", html=_frontier_svg()),
        slide("Reading the page", "The controls",
              "<b>Look-back</b> is the stretch of history the frontier is built from. <b>Then test on the "
              "next</b> is how many years afterwards to check the mix. <b>Max in one index</b> stops it from "
              "piling everything into one index, and <b>Min in each index</b> keeps every index in. Use the "
              "arrows to slide the window through time."),
    ]
    if ex:
        b = ex["beat_equal"]
        bucket = "About 25%" if b < 37.5 else "About 50%" if b < 70 else "About 90%"
        s.append(slide("Did it last?", "The catch: hindsight",
                       "A frontier is drawn with perfect hindsight. The real question is whether the best past "
                       "mix kept working. The page tests it on the years that followed. "
                       f"We ran every 5-year window from the six Nifty 500 factor indices, "
                       f"{ex['n']} of them, each tested on the next 5 years.",
                       quiz={"q": "Guess: how often did the 'best' past mix beat a simple equal-weight mix "
                                  "of the same indices over the next five years?",
                             "options": ["About 25%", "About 50%", "About 90%"], "answer": bucket,
                             "why": f"<b>{b:.0f}%</b> of the time, close to a coin flip, even though it beat the "
                                    f"Nifty 500 itself {ex['beat_bench']:.0f}% of the time. The edge came "
                                    "from holding the factors at all, not from the optimised weights."}))
    s.append(slide("Your turn", "Use it as a lens, not a recipe",
                   "Slide the window and watch the weights jump from one period to the next. That instability "
                   "is the lesson. Look for indices that keep showing up in the best mix across many windows, "
                   "and compare the result with the equal mix before trusting any weights."))
    return s


def _try_to_time_deck():
    return [
        slide("How to play", "Back one index a year",
              "Five Nifty 500 factor indices race through each calendar year: Momentum, Value, Quality, Low "
              "Volatility and Growth. Before each year you pick one, using only what was known at the end of "
              "the year before."),
        slide("How to play", "Reading the cards",
              "Each index shows its returns over the last 1, 3 and 5 years, its <b>risk</b> (how bumpy its "
              "monthly returns were) and its <b>worst fall</b>. Some cards also show how often each index has "
              "won. Use them however you like. That's the whole question."),
        slide("How to play", "Points, money and a rival",
              "You score 100 points for picking the year's winner, 50 for second and 20 for third, plus a "
              "streak bonus. ₹1 lakh moves into your pick each year. A <b>mystery rival</b> plays alongside "
              "you, and you'll find out who it was at the end.", cta="Let's play"),
    ]


def _handle_it_deck():
    return [
        slide("How to play", "Pick something to invest in",
              "Choose a Nifty index or search for any mutual fund. The game finds a real high point in its "
              "history and invests you there."),
        slide("How to play", "Live through it, month by month",
              "Time moves forward one month at a time. Watch your money, and notice how it feels. The "
              "<b>Sell</b> button is always there. Press it and your money is locked in, and the game "
              "carries on to show you what happened next."),
        slide("How to play", "What it's really testing",
              "Knowing an index fell in the past is easy. Staying invested while it's falling is the hard "
              "part. Play it a few times with different picks.", cta="Let's play"),
    ]


def _writing_deck():
    return [
        slide("Writing", "Articles from my Substack",
              "Essays on factor investing and markets: the thinking behind PRISM's tools. Open any article "
              "to read it right here, or on my Substack."),
        slide("Writing", "Read, then try it",
              "Most articles use a tool on this site. Read the idea, then open the tool and test it on a "
              "fund or index you care about. Subscribe on my Substack to get new pieces by email."),
    ]


def _home_deck():
    return [
        slide("Start here", "What PRISM does",
              "PRISM looks through Indian funds, indices and portfolios to show what really drives them. "
              "Each tool answers one question.",
              html="<ul class='tut-list'><li class='head'><span>Tool</span><span>Question</span><span>Start with</span></li>"
                   "<li><b>Factor Analysis</b><span>What drives this fund?</span><span>Any fund you own</span></li>"
                   "<li><b>FBI Intelligence</b><span>How has this index behaved?</span><span>Momentum vs Value</span></li>"
                   "<li><b>Drawdown Analysis</b><span>How bad did it get?</span><span>Smallcap vs Nifty 50</span></li>"
                   "<li><b>Efficient Frontier</b><span>Which mix was best, and did it last?</span><span>The default set</span></li>"
                   "</ul>"),
        slide("Start here", "Every page has a tour",
              "Look for <b>Take the 1-minute tour</b> under each page title, and <b>How to read this tab</b> "
              "inside the tabs. The games teach the same ideas by playing.", cta="Start exploring"),
    ]


# page -> deck: the dialog title and the function that builds its slides
DECKS = {
    "home": {"title": "Welcome to PRISM", "build": _home_deck},
    "factor-analysis": {"title": "How to read a fund", "build": _factor_deck},
    "fbi-intelligence": {"title": "How to read an index", "build": _fbi_deck},
    "drawdown-analysis": {"title": "How to read a fall", "build": _drawdown_deck},
    "efficient-frontier": {"title": "How to read the frontier", "build": _frontier_deck},
    "try-to-time": {"title": "Try to Time", "build": _try_to_time_deck},
    "can-you-handle-it": {"title": "Can You Handle It?", "build": _handle_it_deck},
    "writing": {"title": "Writing", "build": _writing_deck},
}
