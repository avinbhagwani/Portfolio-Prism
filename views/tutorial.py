"""
Page tutorials: a short, interactive slide deck for every page.

  launcher(page)          a "1-minute tour" pill under the page title
                          (with a small gold dot until it's been opened)
  tab_link(page, chapter) "How to read this tab", opening the deck at that
                          tab's chapter
  maybe_open(page)        called once per run from app.py before the page
                          renders: applies any "try it" prefill and shows
                          the deck if one is open for this page

The deck itself runs in the browser (static/tutorial.html in st.iframe,
like the games), so moving between slides, quizzes and sliders is
instant and animated, with arrow keys and swipe. The last slide's button
clicks a hidden Streamlit button (the iframe is same-origin) to close the
deck and, on Factor Analysis, fill in the example fund.

Live examples come from core/tutorial_data.py: HDFC Flexi Cap (the fund
from the PRISM launch post on my Substack) and real Nifty index history.
Game decks explain how to play and never give away an ending.
"""

import json
import random
from pathlib import Path

import streamlit as st

from core import tutorial_charts as tc
from core import tutorial_data as td

STATIC = Path(__file__).resolve().parent.parent / "static"


# =====================================================================
# Opening and closing
# =====================================================================

def _open(page, step=0):
    """step: a slide index, or a chapter name to open at."""
    st.session_state["tut_page"] = page
    st.session_state["tut_step"] = step
    st.session_state.setdefault("tut_seen", set()).add(page)


def _close():
    st.session_state.pop("tut_page", None)
    st.session_state.pop("tut_step", None)


def launcher(page, label="1-minute tour"):
    """The tour pill under a page header."""
    new = page not in st.session_state.get("tut_seen", set())
    with st.container(key=f"tutpill_{'new_' if new else ''}{page}", width="content"):
        st.button(label, key=f"tut_launch_{page}", icon=":material/school:",
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
        st.dialog(DECKS[page]["title"], width="large", on_dismiss=_close)(_deck)(page)
    elif "tut_page" in st.session_state and st.session_state["tut_page"] != page:
        _close()                               # left the page with a deck open


# =====================================================================
# The deck
# =====================================================================

@st.cache_resource(show_spinner=False)
def _template():
    return (STATIC / "tutorial.html").read_text(encoding="utf-8")


def _slides(page):
    """Built once per session per page, so live numbers load once."""
    cache = st.session_state.setdefault("_tut_slides", {})
    if page not in cache:
        with st.spinner("Loading a live example..."):
            cache[page] = DECKS[page]["build"]()
    return cache[page]


def _deck(page):
    slides = _slides(page)
    step = st.session_state.get("tut_step", 0)
    if isinstance(step, str):                  # opened from a tab: start at its chapter
        step = next((k for k, s in enumerate(slides) if s["chapter"] == step), 0)
    deck = DECKS[page]
    data = {"page": page, "slides": slides, "start": step,
            "cta": {"label": deck.get("cta", "Done")}}
    payload = json.dumps(data, default=str).replace("</", "<\\/")
    st.iframe(_template().replace("__DATA__", payload), height="content")

    # hidden: the deck's last button clicks this one
    st.markdown("<style>.st-key-tut_hidden{display:none!important}</style>", unsafe_allow_html=True)
    with st.container(key="tut_hidden"):
        if st.button("finish", key=f"tut_go_{page}"):
            if deck.get("prefill"):
                st.session_state["tut_prefill"] = deck["prefill"]
            _close()
            st.rerun()


def slide(chapter, title, body=None, **extra):
    return {"chapter": chapter, "title": title, "body": body, **extra}


# =====================================================================
# Formatting and small visuals
# =====================================================================

def _pct(x, d=1, signed=False):
    return (f"{x:+.{d}f}%" if signed else f"{x:.{d}f}%").replace("-", "−")


def _num(x, d=2, signed=True):
    return (f"{x:+.{d}f}" if signed else f"{x:.{d}f}").replace("-", "−")


def _steps(items):
    return {"type": "steps", "items": items}


def _mock(html, cap=None):
    return {"type": "mock", "html": html, "cap": cap}


def _fld(label, value, hl=False):
    return f"<div class='fld{' hl' if hl else ''}'><small>{label}</small>{value}</div>"


def _seg(options, on, hl=False):
    return (f"<div class='seg{' hl' if hl else ''}'>"
            + "".join(f"<span class='{'on' if o == on else ''}'>{o}</span>" for o in options) + "</div>")


ICONS = {
    "fund": "<svg viewBox='0 0 24 24' fill='none' stroke='#1F4E79' stroke-width='1.8'><path d='M4 19V9M10 19V5M16 19v-7M22 19H2'/></svg>",
    "index": "<svg viewBox='0 0 24 24' fill='none' stroke='#1F4E79' stroke-width='1.8'><path d='M3 17l5-6 4 3 7-9'/><path d='M15 5h4v4'/></svg>",
    "fall": "<svg viewBox='0 0 24 24' fill='none' stroke='#B54A3C' stroke-width='1.8'><path d='M3 6c3 0 4 10 8 10s5-6 10-6'/></svg>",
    "mix": "<svg viewBox='0 0 24 24' fill='none' stroke='#1F4E79' stroke-width='1.8'><path d='M3 20c3-9 8-13 18-15'/><circle cx='8' cy='16' r='1.3' fill='#98A1AC' stroke='none'/><circle cx='12' cy='14' r='1.3' fill='#98A1AC' stroke='none'/><circle cx='14' cy='17' r='1.3' fill='#98A1AC' stroke='none'/></svg>",
}

DRAWDOWN_SVG = """
<svg viewBox='0 0 520 230' style='width:100%;display:block' font-family='Inter, sans-serif'>
  <line x1='20' y1='52' x2='505' y2='52' stroke='#C9D0D8' stroke-dasharray='4 4'/>
  <text x='22' y='44' font-size='11' fill='#98A1AC'>previous high</text>
  <path class='dr' d='M20 114 C60 94 95 54 130 52 C165 52 190 167 220 167 C250 167 270 142 300 117
           C340 82 370 57 400 52 C430 47 470 40 505 34' fill='none' stroke='#1F4E79' stroke-width='2.6'/>
  <g class='fade' style='animation-delay:.5s'>
    <circle cx='130' cy='52' r='5' fill='#1F4E79'/><text x='130' y='38' font-size='11.5' fill='#17212D' text-anchor='middle'>peak</text></g>
  <g class='fade' style='animation-delay:.9s'>
    <circle cx='220' cy='167' r='5' fill='#B54A3C'/><text x='220' y='186' font-size='11.5' fill='#B54A3C' text-anchor='middle'>trough</text>
    <line x1='220' y1='58' x2='220' y2='158' stroke='#B54A3C' stroke-width='1.3' marker-start='url(#dda)' marker-end='url(#dda)'/>
    <text x='229' y='100' font-size='11.5' fill='#B54A3C'>depth</text><text x='229' y='114' font-size='11.5' fill='#B54A3C'>of the fall</text></g>
  <g class='fade' style='animation-delay:1.3s'>
    <circle cx='400' cy='52' r='5' fill='#1F4E79'/><text x='400' y='38' font-size='11.5' fill='#17212D' text-anchor='middle'>back to the high</text>
    <path d='M130 200 v6 h90 v-6 M220 206 h180 v-6' fill='none' stroke='#98A1AC'/>
    <text x='175' y='222' font-size='11' fill='#66707C' text-anchor='middle'>time to bottom</text>
    <text x='310' y='222' font-size='11' fill='#66707C' text-anchor='middle'>time to recover</text></g>
  <defs><marker id='dda' viewBox='0 0 10 10' refX='5' refY='5' markerWidth='5' markerHeight='5'
    orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10z' fill='#B54A3C'/></marker></defs>
</svg>"""


def _frontier_svg():
    rnd = random.Random(4)
    dots = []
    for k in range(150):
        x = rnd.uniform(132, 488)
        top = 150 - 112 * (1 - ((488 - x) / 356) ** 2.2)
        y = rnd.uniform(top + 8, 184)
        dots.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='2.6' fill='#C3CAD2'/>")
    return f"""
<svg viewBox='0 0 520 220' style='width:100%;display:block' font-family='Inter, sans-serif'>
  <line x1='40' y1='190' x2='505' y2='190' stroke='#C9D0D8'/><line x1='40' y1='14' x2='40' y2='190' stroke='#C9D0D8'/>
  <text x='505' y='208' font-size='11' fill='#66707C' text-anchor='end'>risk (how bumpy) →</text>
  <text x='14' y='16' font-size='11' fill='#66707C' transform='rotate(-90 14 16)' text-anchor='end'>return →</text>
  <g class='fade'>{''.join(dots)}</g>
  <path class='dr' d='M120 150 C140 95 200 62 280 48 C340 40 410 36 480 34' fill='none' stroke='#1F4E79' stroke-width='2.6'/>
  <g class='fade' style='animation-delay:1.2s'><circle cx='121' cy='148' r='6' fill='#fff' stroke='#1F4E79' stroke-width='2'/>
    <text x='132' y='168' font-size='11.5' fill='#17212D'>lowest-risk mix</text></g>
  <g class='fade' style='animation-delay:1.5s'><path d='M262 37 l4 9 10 1 -8 6 3 10 -9 -5 -9 5 3 -10 -8 -6 10 -1z' fill='#E0B15C' stroke='#B07A2A'/>
    <text x='282' y='34' font-size='11.5' fill='#17212D'>best mix for the risk</text></g>
  <text x='405' y='26' font-size='11.5' fill='#1F4E79' class='fade' style='animation-delay:1s'>the frontier</text>
</svg>"""


def _handle_svg():
    return """
<svg viewBox='0 0 520 220' style='width:100%;display:block' font-family='Inter, sans-serif'>
  <line x1='20' y1='40' x2='505' y2='40' stroke='#C9D0D8' stroke-dasharray='4 4'/>
  <text x='22' y='32' font-size='11' fill='#98A1AC'>you invest here, at the top</text>
  <path class='dr' d='M20 40 C70 44 90 70 130 92 C170 112 190 100 220 128 C250 154 280 150 310 170 C330 182 350 176 370 168'
        fill='none' stroke='#B54A3C' stroke-width='2.6'/>
  <text x='378' y='172' font-size='22' fill='#98A1AC' class='fade' style='animation-delay:1.3s'>?</text>
  <g class='fade' style='animation-delay:1.1s'>
    <rect x='392' y='60' width='112' height='36' rx='18' fill='#B54A3C'/>
    <text x='448' y='83' font-size='13.5' font-weight='600' fill='#fff' text-anchor='middle'>Sell</text>
    <rect x='392' y='60' width='112' height='36' rx='18' fill='none' stroke='#B54A3C' stroke-width='2' opacity='.5'>
      <animate attributeName='opacity' values='.6;0;.6' dur='1.8s' repeatCount='indefinite'/></rect></g>
  <text x='448' y='118' font-size='11' fill='#66707C' text-anchor='middle' class='fade' style='animation-delay:1.1s'>always there</text>
</svg>"""


# =====================================================================
# Factor Analysis
# =====================================================================

FACTORS = [
    {"name": "Size", "pos": "small companies", "neg": "large companies"},
    {"name": "Value", "pos": "cheap (value) stocks", "neg": "expensive (growth) stocks"},
    {"name": "Profitability", "pos": "highly profitable firms", "neg": "less profitable firms"},
    {"name": "Investment", "pos": "firms that invest conservatively", "neg": "firms that expand aggressively"},
    {"name": "Momentum", "pos": "recent winners", "neg": "recent losers"},
]
WORD = {"SMB": ("toward small companies", "toward large companies"),
        "HML": ("toward value stocks", "toward growth stocks"),
        "RMW": ("toward highly profitable firms", "toward less profitable firms"),
        "CMA": ("toward firms that invest conservatively", "toward firms that expand aggressively"),
        "WML": ("toward recent winners", "away from recent winners")}


def _fallback_roll_specs(windows):
    """Rolling charts from the illustrative series, if live data failed."""
    import pandas as pd
    out = {}
    for label, series in windows.items():
        rdf = pd.DataFrame({"HML": [v for _, v, _ in series], "HML_P": [p for _, _, p in series],
                            "HML_SE": [0.08] * len(series)},
                           index=pd.to_datetime([d for d, _, _ in series]))
        spec = tc.rolling_spec(rdf, "HML", "Value")
        if spec:
            out[label] = spec
    return out


def _strength(c):
    a = abs(c)
    return "a slight" if a < 0.1 else "a clear" if a < 0.3 else "a strong"


def _factor_deck():
    ex = td.fund_example()
    name = ex["name"]
    flag = ("Live data didn't load just now, so these are illustrative numbers. "
            "Run the analysis to see the real ones." if ex["example"] else None)
    rows = {r["key"]: r for r in ex["factors"]}
    tilts = [r for r in ex["factors"] if r["key"] != "MKT_RF"]
    sig = sorted([r for r in tilts if r["p"] < 0.05], key=lambda r: -abs(r["coef"]))
    hml = rows.get("HML")

    if sig:
        read = "<br>".join(
            f"<b>{r['label']} {_num(r['coef'])}</b>: {_strength(r['coef'])} lean "
            f"{WORD[r['key']][0] if r['coef'] > 0 else WORD[r['key']][1]}." for r in sig[:3])
        read = f"<p>{read}</p><p>Everything grey is too uncertain to call.</p>"
    else:
        read = "<p>None of the style tilts is reliably different from zero over this period.</p>"

    value_ok = hml is not None and hml["lo"] > 0
    value_q = None
    if hml:
        value_q = {
            "q": f"So, is {name.replace(' Fund', '')} really a value fund?",
            "options": ["Yes: its value range stays above zero", "No: its value range crosses zero"],
            "answer": "Yes: its value range stays above zero" if value_ok else "No: its value range crosses zero",
            "why": (f"Value is {_num(hml['coef'])}, with a 95% range of {_num(hml['lo'])} to {_num(hml['hi'])}. "
                    + ("The whole range is positive, so the reputation holds up in the numbers." if value_ok else
                       "The range includes zero, so over the full period the numbers can't confirm it.")),
        }

    a, ap = ex["alpha"], ex["alpha_p"]
    alpha_body = (f"<p>Alpha is the return the factors can't explain. For {name} it's "
                  f"<b>{_pct(a, signed=True)} a year</b>.</p>"
                  + ("<p>That's statistically meaningful, which is rare.</p>" if ap < 0.05 else
                     "<p>But its range crosses zero, so it could be luck. That's normal: most funds' "
                     "alpha can't be told apart from zero.</p>"))

    roll = ex["rolling"].get("HML")
    windows = ex.get("windows", {})
    roll_slides = []
    if roll:
        ex_d, ex_v = roll["exit"] if roll["exit"] else roll["last"]
        last_d, last_v = roll["last"]
        drift = last_v - ex_v
        if roll["exit"] and abs(drift) >= 0.1:
            story = (f"<p>In the 3 years to <b>{ex_d:%b %Y}</b>, around Prashant Jain's exit, value exposure "
                     f"was <b>{_num(ex_v)}</b>. In the latest window, to {last_d:%b %Y}, it's "
                     f"<b>{_num(last_v)}</b>.</p>"
                     + ("<p>The value lean has faded under new management.</p>" if drift < 0 else
                        "<p>The value lean has grown stronger since.</p>"))
            take = ("That's <b>style drift</b>. One full-period number would have averaged it away."
                    if drift < 0 else "One full-period number hides how the style has moved.")
        else:
            vals = [v for _, v, _ in roll["series"]]
            story = (f"<p>Value exposure has moved between {_num(min(vals))} and {_num(max(vals))} across "
                     f"windows, ending at <b>{_num(last_v)}</b> in the window to {last_d:%b %Y}.</p>")
            take = "A line that stays put means a steady style. Big swings mean the manager moves around."
        specs = ex.get("roll_specs") or _fallback_roll_specs(windows or {"3Y": roll["series"]})
        three = {"3Y": specs["3Y"]} if "3Y" in specs else specs
        roll_slides = [
            slide("Over time", "One number can hide a change of style",
                  "<p>The <b>Over time</b> tab reruns the regression on every 3-year window, one ending each "
                  f"month. Here's {name.replace(' Fund', '')}'s value exposure, exactly as the tab draws it.</p>",
                  viz={"type": "vega", "specs": three, "default": "3Y",
                       "cap": "Each point is one 3-year window. The shaded band is the 95% range; navy points "
                              "are significant. Prashant Jain left in mid-2022."},
                  take="Hover the line to read any window.", flag=flag),
            slide("Over time", "Reading the line", story, take=take,
                  viz={"type": "vega", "specs": three, "default": "3Y"},
                  quiz={"q": "A value line falls from 0.45 to 0.05 while R² stays high. What happened?",
                        "options": ["The manager changed style", "Value stocks crashed", "The fund got bigger"],
                        "answer": "The manager changed style",
                        "why": "Exposure measures how the fund moves with value stocks, not how they did. "
                               "A falling line with a steady R² means the portfolio itself shifted.",
                        "wrong": {"Value stocks crashed": "A crash hurts returns, but exposure measures how "
                                  "closely the fund tracks value stocks, not how they performed.",
                                  "The fund got bigger": "Size alone doesn't erase a value lean."}}),
        ]
        if len(specs) > 1:
            roll_slides.append(slide(
                "Over time", "Pick a window that fits the question",
                "<p>Switch the window on the right. <b>1Y</b> reacts fast but jumps around. <b>5Y</b> is smooth "
                "but slow to show a change. <b>3Y</b> is the default for a reason.</p>",
                take="A tilt that stays navy across most windows is part of the fund's DNA.",
                viz={"type": "vega", "specs": specs, "default": "1Y", "suffix": " windows",
                     "notes": {"1Y": "1-year windows: quick to react, lots of noise (more grey dots).",
                               "3Y": "3-year windows: the balance PRISM uses by default.",
                               "5Y": "5-year windows: smooth, but a change shows up late."}}))

    a_m, a_se = ex["alpha"] / 12, ex.get("alpha_se", 0.1)
    terms = [("Alpha", a_m, a_se, ap)] + [(r["label"], r["coef"], r["se"], r["p"]) for r in ex["factors"]]
    table = [{"term": "Alpha (monthly %)" if lab == "Alpha" else lab, "coef": c, "se": se,
              "t": c / se if se else 0, "p": p} for lab, c, se, p in terms]
    exposure = tc.exposure_spec(terms)

    def cards(hl):
        conf = "strong evidence" if ap < 0.01 else "some evidence" if ap < 0.05 else "could be noise"
        tone = "good" if ap < 0.05 and a > 0 else "bad" if ap < 0.05 else ""
        return {"type": "cards", "hl": hl, "items": [
            {"label": "Explained by factors", "value": f"{ex['r2']:.0f}%", "sub": "R² of the regression"},
            {"label": "Alpha", "value": _pct(a, signed=True), "sub": f"A year · {conf}", "tone": tone},
            {"label": "Market beta", "value": f"{ex['beta']:.2f}",
             "sub": f"Moves about {ex['beta'] * 100:.0f}% as much as the market"},
            {"label": "Months analysed", "value": str(ex["months"]),
             "sub": f"{ex['start']:%b %Y} to {ex['end']:%b %Y}"}]}

    return [
        slide("The idea", "A fund is a recipe",
              "<p>Every month, a fund's return can be split into ingredients: the market, plus a lean toward "
              "certain kinds of stocks. Whatever's left over is <b>alpha</b>.</p>",
              viz={"type": "recipe", "hint": "Hover an ingredient to see what it is.", "chips": [
                  {"t": "Fund return", "kind": "out", "d": "What the fund returned in a month, above the risk-free rate."},
                  {"t": "Market", "kind": "lead", "d": "<b>Market:</b> how much it swings with the whole market."},
                  {"t": "Size", "d": "<b>Size:</b> small companies (+) or large ones (−)."},
                  {"t": "Value", "d": "<b>Value:</b> cheap stocks (+) or expensive, growth stocks (−)."},
                  {"t": "Profitability", "d": "<b>Profitability:</b> highly profitable firms (+) or less (−)."},
                  {"t": "Investment", "d": "<b>Investment:</b> firms that invest conservatively (+) or aggressively (−)."},
                  {"t": "Momentum", "d": "<b>Momentum:</b> recent winners (+) or recent losers (−)."},
                  {"t": "Alpha", "kind": "alpha", "d": "<b>Alpha:</b> what the recipe can't explain. Skill, or luck."}]},
              take="Each ingredient gets a number, its <b>exposure</b>. This tour reads them for a real fund."),
        slide("The idea", f"Meet the test fund: {name}",
              "<p>For years it was run by Prashant Jain, known as a value investor, until he left HDFC AMC in "
              "mid-2022. It's the fund from the post launching PRISM on my Substack.</p>",
              viz={"type": "tiles", "items": [
                  {"label": "Months analysed", "value": str(ex["months"]), "num": ex["months"],
                   "sub": f"{ex['start']:%b %Y} to {ex['end']:%b %Y}"},
                  {"label": "Factor model", "value": "6", "num": 6, "sub": "Fama-French 5 + Momentum"},
                  {"label": "Manager change", "value": "2022", "sub": "Prashant Jain leaves"}]},
              take="The question for this tour: do the numbers back up the value reputation?", flag=flag),
        slide("Exposures", "Step 1: how much do the factors explain?",
              f"<p>Start with the <b>Explained by factors</b> card (R²). For {name}, the factors explain "
              f"<b>{ex['r2']:.0f}%</b> of its monthly ups and downs.</p>",
              viz=cards(0),
              take="Above about 80%, trust the rest of the page. Below about 60%, something else is driving "
                   "the fund, so read the tilts with care.", flag=flag),
        slide("Exposures", "Step 2: market beta",
              f"<p>Beta is how hard the fund swings with the market. {name}'s is "
              f"<b>{_num(ex['beta'], signed=False)}</b>. Most equity funds sit between 0.8 and 1.1.</p>"
              "<p>Drag the sliders to feel what it means.</p>",
              viz={"type": "beta", "beta": ex["beta"], "start": round(ex["beta"], 2),
                   "fund": name.replace(" Fund", "")},
              quiz={"q": "Beta 1.2, market falls 10%. Roughly how much does the fund fall?",
                    "options": ["8%", "10%", "12%"], "answer": "12%",
                    "why": "1.2 × 10% = 12%. A beta above 1 amplifies the market both ways.",
                    "wrong": {"8%": "That would be a beta of 0.8.", "10%": "That would be a beta of exactly 1."}},
              flag=flag),
        slide("Exposures", "Step 3: read a tilt, sign first, then size",
              "<p>A <b>positive</b> exposure leans toward the first group; a <b>negative</b> one leans the "
              "other way. The size says how strongly.</p>"
              "<p>So <b>Momentum +0.8</b> means the fund strongly chases recent winners. Try other factors "
              "and values.</p>",
              viz={"type": "tilt", "factors": FACTORS, "start": {"factor": "Momentum", "value": 0.8}},
              take="Under 0.1 is slight. 0.1 to 0.3 is a clear tilt. Above 0.3 is strong."),
        slide("Exposures", "Quick check",
              "<p>A large-cap fund and a small-cap fund will sit on opposite sides of the Size factor.</p>",
              quizSide=True,
              quiz={"q": "A fund shows Size −0.35. What does it mostly hold?",
                    "options": ["Small companies", "Large companies", "A mix, with no lean"],
                    "answer": "Large companies",
                    "why": "Negative size points away from small companies: a strong lean to large ones.",
                    "wrong": {"Small companies": "That would be a positive Size number.",
                              "A mix, with no lean": "At −0.35 the lean is strong. Check the sign."}}),
        slide("Exposures", "Step 4: is it real, or noise?",
              "<p>Every exposure is an estimate, so each bar gets a <b>95% range</b>. If the range crosses "
              "zero, the tilt could be nothing at all, and the bar turns grey.</p>",
              viz={"type": "vega", "spec": tc.exposure_spec([("Momentum", 0.8, 0.56, 0.15),
                                                             ("Value", 0.25, 0.066, 0.0002)], 260),
                   "cap": "An example in the Exposures chart's style: grey bars could be noise; the whisker "
                          "is the 95% range."},
              quiz={"q": "Momentum is +0.8 with a range of −0.3 to +1.9. What can you say?",
                    "options": ["Strong momentum fund", "Can't tell: it could be zero"],
                    "answer": "Can't tell: it could be zero",
                    "why": "A big number with a range that crosses zero isn't evidence. The smaller Value tilt, "
                           "with a tight range, is the real signal."}),
        slide("Exposures", f"Now the real thing: {name.replace(' Fund', '')}'s tilts", read,
              viz={"type": "vega", "spec": exposure,
                   "cap": "The Exposures chart for this fund. Hover a bar for its range."},
              quiz=value_q, flag=flag),
        slide("Exposures", "Step 5: alpha, what's left over", alpha_body,
              viz=cards(1),
              take="A big alpha with weak evidence means nothing yet. A small alpha with strong evidence is "
                   "worth noticing.", flag=flag),
        *roll_slides,
        slide("Details", "The raw numbers, if you want them",
              "<p>The <b>Details</b> tab has the growth of ₹1 lakh, the full regression and the monthly data "
              "behind it.</p><p>Standard errors are Newey-West, which allows for monthly returns that aren't "
              "fully independent of each other.</p>",
              viz={"type": "regtable", "rows": table,
                   "note": f"R² {ex['r2'] / 100:.3f}, {ex['months']} months, Newey-West standard errors."},
              flag=flag),
        slide("Your turn", "Analyse any fund in five steps",
              "<p>That's the whole method. It works the same for one fund or, in <b>Portfolio</b> mode, "
              "your whole mix.</p>",
              viz=_steps(["<b>R²</b>: do the factors explain most of it?",
                          "<b>Beta</b>: how hard does it swing with the market?",
                          "<b>Tilts</b>: sign for direction, size for strength.",
                          "<b>Confidence</b>: ignore grey bars and ranges crossing zero.",
                          "<b>Over time and alpha</b>: is the style steady, and is anything left over real?"])),
    ]


# =====================================================================
# FBI Intelligence
# =====================================================================

def _fbi_deck():
    ex = td.fbi_example()
    q = tc.quilt_png()
    ch = tc.fbi_specs()
    s = [slide("Overview", "Indices with a rule",
               "<p>Factor indices pick stocks by a rule. <b>Nifty200 Momentum 30</b> holds the 30 Nifty 200 "
               "stocks with the strongest recent price trends.</p><p>Four controls at the top drive every "
               "tab on this page.</p>",
               viz=_mock("<div class='row'>" + _fld("Index", "Nifty200 Momentum 30", True)
                         + _fld("Compare with", "Nifty500 Value 50") + "</div><div class='row'>"
                         + _fld("Benchmark", "Nifty 500") + _seg(["1Y", "3Y", "5Y", "10Y", "Max"], "5Y") + "</div>",
                         "Pick an index, an optional second one to compare, the benchmark, and the period."))]
    if ex:
        yrs = (ex["end"] - ex["start"]).days / 365.25
        grow = {k: (1 + ex["cagr"][k] / 100) ** yrs for k in ("a", "b")}
        s.append(slide("Overview", "Start with the headline",
                       f"<p>Every tab opens with a sentence worked out from the data. Since {ex['start']:%b %Y}, "
                       f"{ex['a']} returned <b>{_pct(ex['cagr']['a'])} a year</b> against "
                       f"{_pct(ex['cagr']['b'])} for the {ex['b']}.</p>",
                       viz={"type": "vega", "spec": ch.get("growth"),
                            "cap": f"Growth of ₹1 lakh. ₹1 lakh became about ₹{grow['a']:.0f} lakh against "
                                   f"₹{grow['b']:.0f} lakh. Hover for any date."},
                       take="The cards add volatility and the worst fall. Return is only half the story."))
        h = ex["hit3"]
        s.append(slide("Returns", "Returns depend on when you start",
                       "<p>One return figure depends on its start date. <b>Rolling returns</b> test every "
                       f"3-year stretch instead. {ex['a']} won <b>{h['pct']:.0f}%</b> of {h['n']} of them, by a "
                       f"median of {h['median']:.1f} points a year.</p>",
                       viz={"type": "vega", "spec": ch.get("rolling"),
                            "cap": "Rolling 3-year return, annualised: one point per 3-year stretch."},
                       quiz={"q": "Which tells you more about consistency?",
                             "options": ["Return since launch", "Share of rolling periods won"],
                             "answer": "Share of rolling periods won",
                             "why": "A single start-to-end return can be flattered by a lucky start or end date."},
                       take="Below the rolling chart, the calendar-year bars show the bad years at a glance."))
        wa, wb = ex["worst"]["a"], ex["worst"]["b"]

        def rec(w):
            return f"back by {w['recovery']:%b %Y}" if w["recovery"] is not None else "not recovered yet"
        s.append(slide("Risk", "What did the return cost?",
                       f"<p>{ex['a']}'s worst fall was <b>{_pct(wa['depth'])}</b>, from {wa['peak']:%b %Y}. The "
                       f"{ex['b']} fell {_pct(wb['depth'])}. The higher return didn't come free.</p>",
                       viz={"type": "vega", "spec": ch.get("drawdown"),
                            "cap": f"Fall from previous high. {ex['a']}: {rec(wa)}. {ex['b']}: {rec(wb)}."},
                       take="The Risk tab shows every fall from a previous high, and how long each took to recover."))
        s.append(slide("Risk", "Upside and downside capture",
                       f"<p>In months the {ex['b']} rose, {ex['a']} took <b>{ex['up']:.0f}%</b> of its gains. In "
                       f"months it fell, it took <b>{ex['down']:.0f}%</b> of the losses.</p>",
                       viz={"type": "vega", "spec": ch.get("capture"),
                            "cap": "Upper left is the good corner: more of the gains, less of the losses."},
                       quiz={"q": "Fund A: 90% up, 70% down. Fund B: 110% up, 120% down. Which protects you "
                                  "better in falls?",
                             "options": ["Fund A", "Fund B"], "answer": "Fund A",
                             "why": "Fund A takes only 70% of the market's falls. Fund B falls harder than the market."}))
        hits = ex.get("hits", {})
        if hits:
            s.append(slide("Hit ratio", "Does the rule beat where it came from?",
                           "<p>Every strategy index has a parent: Momentum 30 comes from the Nifty 200. The "
                           f"<b>Hit ratio</b> tab shows how often each beat its parent. {ex['a']} won "
                           + ", ".join(f"<b>{v:.0f}%</b> of {y}-year periods" for y, v in sorted(hits.items()))
                           + ".</p>",
                           viz={"type": "vega", "spec": ch.get("hit_gap"),
                                "cap": "What you see when you click the 3-year number: navy bars beat the parent, "
                                       "rust lagged."},
                           take="If a factor premium is real, the hit ratio usually rises as the window gets longer."))
    if q:
        s.append(slide("Market map", "Leadership rotates",
                       "<p><b>Year by year</b> is the quilt: each column is a year, ranked best to worst. "
                       "This is the page's own quilt for the Nifty 500 factors.</p>",
                       viz={"type": "img", "src": q, "alt": "Factor quilt"},
                       quiz={"q": "Does one factor top the ranking every year?",
                             "options": ["Yes, the best one does", "No, leadership rotates"],
                             "answer": "No, leadership rotates",
                             "why": "Follow any one colour across the years. That rotation is the case for holding "
                                    "more than one factor."},
                       take="The <b>Risk and return</b> view plots every index in a category: right is bumpier, up is better."))
    s.append(slide("Your turn", "Judge any index in six steps",
                   "<p>Run through these for any index before you buy a fund that tracks it.</p>",
                   viz=_steps(["<b>Return</b> against the benchmark", "<b>Consistency</b>: share of rolling periods won",
                               "<b>Pain</b>: worst fall and recovery time", "<b>Capture</b>: how much of the ups and downs",
                               "<b>Hit ratio</b>: does it beat its own parent?", "<b>Market map</b>: where it sits among peers"])))
    return s


# =====================================================================
# Drawdown, Frontier, games, home, writing
# =====================================================================

def _drawdown_deck():
    ex = td.drawdown_example()
    s = [
        slide("The idea", "What's a drawdown?",
              "<p>A drawdown is the fall from a previous high. It lasts until the investment closes back "
              "above that high.</p><p>Three things matter: how <b>deep</b>, how long to the bottom, and how "
              "long the way back takes.</p>",
              viz={"type": "svg", "svg": DRAWDOWN_SVG}),
        slide("The idea", "Falls and recoveries aren't symmetric",
              "<p>Guess first, then check it on the next slide.</p>", quizSide=True,
              quiz={"q": "An investment falls 50%. What gain gets it back to where it was?",
                    "options": ["+50%", "+75%", "+100%"], "answer": "+100%",
                    "why": "₹100 falls to ₹50. Getting back to ₹100 means doubling: +100%."}),
        slide("The idea", "Try it yourself",
              "<p>Drag the slider. The deeper the fall, the faster the climb back grows.</p>",
              viz={"type": "fallcalc", "start": 50},
              take="This is why avoiding the worst falls matters as much as catching the best rallies."),
    ]
    if ex:
        sc, nf = ex["NIFTY SMALLCAP 250"], ex["NIFTY 50"]

        def sub(w):
            if w["recovery"] is None:
                return "not recovered yet"
            return f"{(w['recovery'] - w['peak']).days / 365.25:.1f} years to recover"
        s.append(slide("The idea", "A real one: 2008",
                       f"<p>The <b>{sc['name']}</b> fell {_pct(sc['depth'])} from {sc['peak']:%b %Y}. The "
                       f"{nf['name']} fell {_pct(nf['depth'])}. Smaller companies brought a deeper, longer fall.</p>",
                       viz={"type": "vega", "spec": tc.drawdown_spec(),
                            "cap": f"Fall from previous high, as the page draws it. {sc['name']}: {sub(sc)}. "
                                   f"{nf['name']}: {sub(nf)}."}))
    s += [
        slide("Reading the page", "Pick, compare, read",
              "<p>Add up to ten indices or mutual funds. <b>Period</b> sets how far back to look. <b>Start "
              "dates</b> compares everything over the same years, or each from its own start.</p>"
              "<p>On the chart, the line sits at <b>0%</b> at every new high. The table lists the worst falls.</p>",
              viz=_mock("<div class='row'>" + _seg(["Index", "Mutual fund"], "Index")
                        + _fld("Add", "Nifty Midcap 150") + "</div><div class='row'>"
                        + "<span class='pill'>Nifty 50 ×</span><span class='pill'>Nifty Smallcap 250 ×</span></div>"
                        + "<div class='row'>" + _seg(["1Y", "3Y", "5Y", "10Y", "Max"], "Max", True)
                        + _seg(["Same for all", "Each from its own start"], "Same for all", True) + "</div>",
                        "The two highlighted controls change what's compared, so check them first."),
              take="Width matters as much as depth: a long, shallow dip tests patience more than a sharp one."),
        slide("Your turn", "Before you invest, ask",
              "<p>Run these four questions on anything you're about to buy.</p>",
              viz=_steps(["How <b>deep</b> was the worst fall?", "How long did it take to <b>recover</b>?",
                          "Is it in a fall <b>right now</b>?", "Could you have <b>sat through it</b> without selling?"]),
              take="For the last question, play <b>Can You Handle It?</b>"),
    ]
    return s


def _frontier_deck():
    ex = td.frontier_example()
    ch = tc.frontier_specs()
    s = [
        slide("The idea", "Every dot is a mix",
              "<p>Mix a few indices in different weights, and each mix has a risk and a return.</p><p>The "
              "<b>frontier</b> is the top edge: the most return any mix got for each level of risk. The "
              "starred mixes are the best for the risk (highest Sharpe ratio) and the lowest-risk one.</p>",
              viz=({"type": "vega", "spec": ch["frontier"],
                    "cap": f"The page's default view: the six Nifty 500 factor indices, {ch['span']}. "
                           "Hover the line to see the mix at any point."}
                   if ch.get("frontier") else {"type": "svg", "svg": _frontier_svg()})),
        slide("Reading the page", "The controls",
              "<p><b>Look-back</b> is the history the frontier is built from. <b>Then test on the next</b> "
              "checks the mix on the years after. The caps stop it putting everything in one index.</p>",
              viz=_mock("<div class='row'>" + _seg(["Nifty 500 factors", "Custom set"], "Nifty 500 factors") + "</div>"
                        + "<div class='row'>" + _seg(["3Y", "5Y", "10Y", "All"], "5Y", True)
                        + _seg(["1Y", "3Y", "5Y"], "5Y", True) + "</div><div class='row'>"
                        + _seg(["No cap", "50%", "40%", "30%"], "No cap") + _seg(["None", "5%", "10%"], "None")
                        + "</div><div class='row'><span class='pill'>‹</span><span style='color:#66707C'>"
                        "slide the window through time</span><span class='pill'>›</span></div>",
                        "Highlighted: the look-back and the test period."),
              take="Without a cap, the best mix is often just one index."),
    ]
    if ex:
        b = ex["beat_equal"]
        bucket = "About 25%" if b < 37.5 else "About 50%" if b < 70 else "About 90%"
        s.append(slide("Did it last?", "The catch: hindsight",
                       "<p>A frontier is drawn with perfect hindsight. Did the best past mix keep working? We "
                       f"ran {ex['n']} five-year windows of the Nifty 500 factor indices, each tested on the next "
                       "five years.</p>", quizSide=True,
                       quiz={"q": "How often did the 'best' past mix beat a simple equal mix of the same indices?",
                             "options": ["About 25%", "About 50%", "About 90%"], "answer": bucket,
                             "why": f"<b>{b:.0f}%</b> of the time: close to a coin flip."}))
        s.append(slide("Did it last?", "What actually worked",
                       "<p>The optimised mix beat the Nifty 500 almost every time. But it barely beat simply "
                       "holding the same indices equally.</p>",
                       viz=({"type": "vega", "spec": ch["track"],
                             "cap": f"The page's track record: the best mix minus the Nifty 500, a year, over the "
                                    f"next 5 years. It beat the Nifty 500 in {ex['beat_bench']:.0f}% of windows "
                                    f"but the equal mix in only {b:.0f}%."}
                            if ch.get("track") else
                            {"type": "tiles", "items": [
                                {"label": "Best past mix beat the Nifty 500", "value": f"{ex['beat_bench']:.0f}%",
                                 "num": ex["beat_bench"], "post": "%", "sub": "over the next 5 years"},
                                {"label": "Best past mix beat the equal mix", "value": f"{b:.0f}%", "num": b,
                                 "post": "%", "sub": "over the next 5 years"}]}),
                       take="The edge came from holding the factors at all, not from the optimised weights."))
    s.append(slide("Your turn", "Use it as a lens, not a recipe",
                   "<p>Slide the window and watch the weights jump. That instability is the lesson.</p>",
                   viz=_steps(["Slide the look-back window through time", "Watch which indices keep showing up",
                               "Compare the best mix with the equal mix", "Only then trust any weights"])))
    return s


def _try_to_time_deck():
    cards = "".join(
        f"<div class='fld' style='flex:1 1 30%'><small>{n}</small>Last year · 3Y · 5Y · Risk</div>"
        for n in ["Momentum", "Value", "Quality", "Low Volatility", "Growth"])
    return [
        slide("How to play", "Back one index a year",
              "<p>Five Nifty 500 factor indices race through each calendar year. Before each year, pick the "
              "one you think will win, using only what was known at the end of the year before.</p>",
              viz=_mock(f"<div class='row'>{cards}</div>", "Each card shows returns, risk and the worst fall so far.")),
        slide("How to play", "How you score",
              "<p>Points for picking well, plus a bonus for back-to-back winners. ₹1 lakh moves into your "
              "pick each year.</p>",
              viz={"type": "tiles", "items": [{"label": "Year's winner", "value": "100", "num": 100, "sub": "points"},
                                              {"label": "Second", "value": "50", "num": 50, "sub": "points"},
                                              {"label": "Third", "value": "20", "num": 20, "sub": "points"}]}),
        slide("How to play", "Beat the mystery rival",
              "<p>A rival plays alongside you. You'll find out who it was at the end.</p>",
              viz={"type": "tiles", "items": [{"label": "Your rival", "value": "?", "sub": "revealed at the end"}]}),
    ]


def _handle_it_deck():
    return [
        slide("How to play", "Invest at the top",
              "<p>Choose a Nifty index or any mutual fund. The game finds a real high point in its history "
              "and invests you there. Then time moves forward, month by month.</p>",
              viz={"type": "svg", "svg": _handle_svg()}),
        slide("How to play", "The Sell button is always there",
              "<p>Press it and your money is locked in. The game carries on to show you what happened next.</p>",
              viz={"type": "tiles", "items": [
                  {"label": "If you hold on", "value": "Stay", "sub": "you ride whatever comes next"},
                  {"label": "If you press Sell", "value": "Sell", "sub": "the fall becomes permanent"}],
                   "cap": "You only find out which was right after you choose."},
              take="Knowing an index fell in the past is easy. Staying in while it falls is the hard part."),
    ]


def _home_deck():
    return [
        slide("Start here", "What PRISM does",
              "<p>PRISM looks through Indian funds, indices and portfolios to show what really drives them. "
              "Each tool answers one question.</p>",
              viz={"type": "tools", "items": [
                  {"name": "Factor Analysis", "q": "What drives this fund?", "icon": ICONS["fund"]},
                  {"name": "FBI Intelligence", "q": "How has this index behaved?", "icon": ICONS["index"]},
                  {"name": "Drawdown Analysis", "q": "How bad did it get?", "icon": ICONS["fall"]},
                  {"name": "Efficient Frontier", "q": "Which mix was best, and did it last?", "icon": ICONS["mix"]}]}),
        slide("Start here", "Every page has a tour",
              "<p>Look for the <b>1-minute tour</b> under each page title, and <b>How to read this tab</b> "
              "inside the tabs. The games teach the same ideas by playing.</p>",
              viz=_mock("<div class='row'><span class='fld hl' style='flex:none'>🎓 1-minute tour</span></div>"
                        "<div class='row'><span class='fld' style='flex:none'>ⓘ How to read this tab</span></div>",
                        "Use ← → to move through any tour."),
              take="New to factors? Start with <b>Factor Analysis</b>."),
    ]


def _writing_deck():
    return [
        slide("Writing", "Articles from my Substack",
              "<p>Essays on factor investing and markets: the thinking behind PRISM's tools. Open any article "
              "to read it here, or on my Substack.</p>"),
        slide("Writing", "Read, then try it",
              "<p>Most articles use a tool on this site. Read the idea, then open the tool and test it on a "
              "fund or index you care about.</p>",
              take="Subscribe on my Substack to get new pieces by email."),
    ]


# page -> deck: dialog title, slide builder, last-button label, optional prefill
DECKS = {
    "home": {"title": "Welcome to PRISM", "build": _home_deck, "cta": "Start exploring"},
    "factor-analysis": {"title": "How to read a fund", "build": _factor_deck,
                        "cta": "Analyse HDFC Flexi Cap",
                        "prefill": {"fa_mode": "One fund", "fa_q": "hdfc flexi cap"}},
    "fbi-intelligence": {"title": "How to read an index", "build": _fbi_deck, "cta": "Explore indices"},
    "drawdown-analysis": {"title": "How to read a fall", "build": _drawdown_deck, "cta": "Compare falls"},
    "efficient-frontier": {"title": "How to read the frontier", "build": _frontier_deck, "cta": "Build a frontier"},
    "try-to-time": {"title": "Try to Time", "build": _try_to_time_deck, "cta": "Let's play"},
    "can-you-handle-it": {"title": "Can You Handle It?", "build": _handle_it_deck, "cta": "Let's play"},
    "writing": {"title": "Writing", "build": _writing_deck, "cta": "Start reading"},
}
