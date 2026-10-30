"""
Home: a calm front door. Three things, lots of space.

  Hero    "Every return has a spectrum." beside the interactive prism
          (static/home-prism.html, the one place JavaScript is allowed)
          and two actions.
  Now     one live sentence from the data (this year's factor race),
          linking to FBI Intelligence.
  Index   every page as a quiet typographic list (Analyse, Play, Read):
          name, one line, arrow. No cards, no art.

Each row is a native st.page_link, so moving to a tool keeps the session.
Row descriptions are drawn with ::after keyed on the link's href, the
same trick the sidebar uses.
"""

from pathlib import Path

import streamlit as st

from core import fbi_metrics as fm
from core import substack as sb
from core.time_game import CONTESTANTS, MARKET

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = {}  # set by app.py

INDEX = [
    ("Analyse", [
        ("factor-analysis", "Factor Analysis", "What really drives a fund's returns"),
        ("fbi-intelligence", "FBI Intelligence", "Which factor index has held up best"),
        ("drawdown-analysis", "Drawdown Analysis", "How far it fell, how long it took to recover"),
        ("efficient-frontier", "Efficient Frontier", "The mix of indices that worked, and whether it lasted"),
    ]),
    ("Play", [
        ("try-to-time", "Try to Time", "Think you can pick next year's winning factor?"),
        ("can-you-handle-it", "Can You Handle It?", "Invest at the top and sit through the fall"),
    ]),
    ("Read", [
        ("writing", "Writing", "Long reads on my Substack"),
    ]),
]

CSS = """
<style>
/* ---------- hero ---------- */
.ph-by {font-size:0.88rem; color:#98A1AC; margin:0 0 1rem 0;}
.ph-by b {color:#66707C; font-weight:500;}
.ph-title {font-size:3.4rem; font-weight:700; color:#17212D; line-height:1.04;
  letter-spacing:-0.032em; margin:0 0 1.1rem 0;}
.ph-title span {background: linear-gradient(90deg, #1F4E79, #2F8F9D 30%, #C08A2E 55%, #5E9A62 75%, #8E5B9F);
  -webkit-background-clip: text; background-clip: text; color: transparent;}
.ph-sub {font-size:1.12rem; color:#66707C; line-height:1.55; max-width:27rem; margin:0 0 1.8rem 0;}
.st-key-ph_ctas a {border-radius:999px !important; padding:0.55rem 1.2rem !important;
  transition:background 0.15s ease, border-color 0.15s ease;}
.st-key-ph_ctas a p {font-size:0.95rem !important; font-weight:500 !important;}
.st-key-ph_cta_primary a {background:#1F4E79 !important; border:1px solid #1F4E79 !important;}
.st-key-ph_cta_primary a p, .st-key-ph_cta_primary a span {color:#FFFFFF !important;}
.st-key-ph_cta_primary a:hover {background:#173E61 !important;}
.st-key-ph_cta_secondary a {background:#FFFFFF !important; border:1px solid #D5DCE3 !important;}
.st-key-ph_cta_secondary a p, .st-key-ph_cta_secondary a span {color:#1F4E79 !important;}
.st-key-ph_cta_secondary a:hover {background:#F4F7FA !important; border-color:#B9C4CF !important;}

/* ---------- the one live line ---------- */
.ph-now {margin:4.2rem 0 0 0; padding:1.6rem 0 0 0; border-top:1px solid #E6EAEF;
  display:grid; grid-template-columns:calc((100% - 1rem) / 7.2) 1fr; gap:1rem; align-items:baseline;}
.ph-now .k {font-size:0.86rem; color:#98A1AC;}
.ph-now .s {font-size:1.35rem; line-height:1.45; color:#17212D; letter-spacing:-0.012em;
  font-weight:400; max-width:44rem;}
.ph-now .s b {font-weight:600;}
.ph-now .s i {font-style:normal; display:inline-block; width:0.6em; height:0.6em;
  border-radius:50%; margin:0 0.3em 0 0.05em; vertical-align:0.08em;}
.ph-now .s .neg {color:#B54A3C;}
.ph-now .m {display:block; font-size:0.84rem; color:#98A1AC; margin-top:0.5rem;}
.st-key-ph_now_link {margin:0.3rem 0 0 calc((100% - 1rem) / 7.2 + 1rem);}
.st-key-ph_now_link a p {font-size:0.9rem !important; color:#1F4E79 !important; font-weight:500 !important;}

/* ---------- index ---------- */
.ph-sec {font-size:0.86rem; color:#98A1AC; padding-top:1.35rem;}
[class*="st-key-ph_idx_"] {margin-top:3.2rem;}
[class*="st-key-ph_rows_"] {gap:0 !important; border-top:1px solid #E6EAEF;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a {
  display:grid; grid-template-columns:minmax(11rem, 15rem) 1fr auto; align-items:center;
  column-gap:1.5rem; padding:1.15rem 0.2rem; margin:0; border-radius:0;
  border-bottom:1px solid #E6EAEF; background:transparent; text-decoration:none;
  transition:padding 0.18s ease, background 0.18s ease;
}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a > span:first-child {grid-column:1; grid-row:1;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a > span:last-child {
  grid-column:3; grid-row:1; color:#C3CAD3 !important; transition:color 0.18s ease, transform 0.18s ease;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a::after {
  grid-column:2; grid-row:1; font-size:0.95rem; color:#66707C; line-height:1.4;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a p {
  font-size:1.12rem !important; font-weight:600 !important; color:#17212D !important;
  letter-spacing:-0.01em; margin:0;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a:hover {background:#F7F9FB; padding-left:0.7rem;}
[class*="st-key-ph_rows_"] [data-testid="stPageLink"] a:hover > span:last-child {
  color:#1F4E79 !important; transform:translateX(3px);}

.ph-foot {margin:4rem 0 0 0; font-size:0.84rem; color:#98A1AC; line-height:1.6;}
.ph-foot a {color:#66707C; text-decoration:none; border-bottom:1px solid #D5DCE3;}

@media (max-width: 640px) {
  .ph-title {font-size:2.3rem;}
  .ph-sub {font-size:1rem;}
  .ph-now {grid-template-columns:1fr; gap:0.4rem; margin-top:2.6rem;}
  .ph-now .s {font-size:1.12rem;}
  .st-key-ph_now_link {margin-left:0;}
  [class*="st-key-ph_idx_"] {margin-top:2.2rem;}
  .ph-sec {padding-top:0;}
  [class*="st-key-ph_rows_"] [data-testid="stPageLink"] a {
    grid-template-columns:1fr auto; row-gap:0.2rem; padding:0.95rem 0.1rem;}
  [class*="st-key-ph_rows_"] [data-testid="stPageLink"] a > span:last-child {grid-column:2; grid-row:1 / span 2;}
  [class*="st-key-ph_rows_"] [data-testid="stPageLink"] a::after {grid-column:1; grid-row:2; font-size:0.88rem;}
}
</style>
"""


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def _race():
    """This year's factor race: (year, partial, [(label, colour, ret)], market, as_of)."""
    names = [c[1] for c in CONTESTANTS] + [MARKET[1]]
    levels = fm.levels_to_as_of(names)
    if any(n not in levels.columns for n in names):
        return None
    cal, partial = fm.calendar_returns(levels)
    year = partial if partial in cal.index else int(cal.index[-1])
    row = cal.loc[year]
    race = sorted(((c[2], c[3], float(row[c[1]])) for c in CONTESTANTS), key=lambda r: -r[2])
    return year, year == partial, race, float(row[MARKET[1]]), fm.as_of_date()


def _hero():
    left, right = st.columns([1, 1.1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='ph-by'>by <b>Avin Bhagwani</b></div>"
            "<div class='ph-title'>Every return has a <span>spectrum</span>.</div>"
            "<div class='ph-sub'>See what really drives Indian mutual funds and "
            "Nifty indices. Free, and built on published factor research.</div>",
            unsafe_allow_html=True,
        )
        with st.container(key="ph_ctas", horizontal=True, gap="small"):
            if "factor-analysis" in PAGES:
                with st.container(key="ph_cta_primary", width="content"):
                    st.page_link(PAGES["factor-analysis"], label="Analyse a fund",
                                 icon=":material/arrow_forward:", icon_position="right")
            if "fbi-intelligence" in PAGES:
                with st.container(key="ph_cta_secondary", width="content"):
                    st.page_link(PAGES["fbi-intelligence"], label="Explore indices")
    with right:
        st.iframe((STATIC / "home-prism.html").read_text(encoding="utf-8"), height=400)


def _now():
    try:
        r = _race()
    except Exception:         # the homepage never fails on a data hiccup
        r = None
    if not r:
        return
    year, partial, race, mkt, as_of = r
    (top_l, top_c, top_v), (bot_l, bot_c, bot_v) = race[0], race[-1]
    when = f"{year} so far" if partial else str(year)
    neg = " class='neg'" if bot_v < 0 else ""
    st.markdown(
        "<div class='ph-now'><div class='k'>Right now</div><div class='s'>"
        f"<i style='background:{top_c}'></i><b>{top_l}</b> leads {when} at "
        f"{fm.fmt_pct(top_v, signed=True)}, while "
        f"<i style='background:{bot_c}'></i><b>{bot_l}</b> sits at "
        f"<span{neg}>{fm.fmt_pct(bot_v, signed=True)}</span>. "
        f"Same market, a {top_v - bot_v:.1f}-point spread."
        f"<span class='m'>Nifty 500 factor indices, total return, to {as_of:%d %b %Y}. "
        f"Nifty 500 itself: {fm.fmt_pct(mkt, signed=True)}.</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if "fbi-intelligence" in PAGES:
        with st.container(key="ph_now_link"):
            st.page_link(PAGES["fbi-intelligence"], label="See the full race",
                         icon=":material/arrow_forward:", icon_position="right")


def _latest_post():
    try:
        posts, _ = sb.load_posts()
    except Exception:
        return None
    return posts[0] if posts else None


def _index():
    css = []
    post = _latest_post() if "writing" in PAGES else None
    for section, rows in INDEX:
        rows = [r for r in rows if r[0] in PAGES]
        if not rows:
            continue
        with st.container(key=f"ph_idx_{section.lower()}"):
            a, b = st.columns([1, 6.2], gap="medium")
            with a:
                st.markdown(f"<div class='ph-sec'>{section}</div>", unsafe_allow_html=True)
            with b, st.container(key=f"ph_rows_{section.lower()}", gap=None):
                for path, label, desc in rows:
                    params = None
                    if path == "writing" and post:
                        label, desc, params = post.title, "Latest on my Substack", {"post": post.slug}
                    st.page_link(PAGES[path], label=label, query_params=params,
                                 icon=":material/arrow_forward:", icon_position="right",
                                 width="stretch")
                    safe = desc.replace('"', "\\\"")
                    css.append(f'[class*="st-key-ph_rows_"] a[href^="{path}"]::after'
                               f'{{content:"{safe}";}}')
    st.markdown("<style>" + "".join(css) + "</style>", unsafe_allow_html=True)


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    _hero()
    _now()
    _index()
    st.markdown(
        "<div class='ph-foot'>Coming next: retirement planning and portfolio attribution. "
        f"Ideas or bugs? <a href='{sb.tracked(sb.SUBSTACK_URL, 'home')}' target='_blank'>"
        "Write to me on my Substack</a>.</div>",
        unsafe_allow_html=True,
    )
