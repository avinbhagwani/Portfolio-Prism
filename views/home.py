"""
Home: what PRISM is, in as few words as possible.

  Hero      "Every return has a spectrum." beside a small space scene: a
            glass crystal among stars; a star you steer with the cursor
            sends starlight into it, which leaves as nebula in PRISM's
            colours. Drag the crystal to spin it; hold to charge the light
            and release for a supernova; nearby stars form constellations
            and stardust orbits the cursor. Drifts by itself when idle.
  Numbers   a strip of live facts from the data
  Lenses    one card per tool, each showing its own animation
  Soon      what's coming (retirement planning, portfolio attribution)
  Writing   the latest Substack article

The interactive prism is static/home-prism.html in an st.iframe,
the one place JavaScript is allowed. Navigation stays in native
st.page_link so moving to a tool keeps the session.
"""

import base64
from pathlib import Path

import streamlit as st

from core import substack as sb
from core.config import MODEL_CONFIG
from core.fbi_metrics import as_of_date, equity_universe
from core.index_data import load_index_history

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = {}  # set by app.py

LENSES = [
    ("factor-analysis", "Factor Analysis", "anim-factor-analysis.svg",
     "Split any Indian mutual fund into the factors behind its returns."),
    ("fbi-intelligence", "FBI Intelligence", "anim-fbi-intelligence.svg",
     "Compare Nifty factor indices on return, risk and consistency."),
    ("drawdown-analysis", "Drawdown Analysis", "anim-drawdown-analysis.svg",
     "How far an index fell, and how long it took to recover."),
    ("efficient-frontier", "Efficient Frontier", "anim-efficient-frontier.svg",
     "The best mix of indices for the risk, and whether it lasted."),
]

SOON = [
    ("Retirement planning", "Will the money last? Plan income for every stage."),
    ("Portfolio attribution", "Which decisions added return, and which cost it."),
]

CSS = """
<style>
.ph-eyebrow {display:none;}
.ph-by {font-size:0.88rem; color:#8A939E; margin:0 0 0.9rem 0;}
.ph-by b {color:#5B6572; font-weight:500;}
.ph-title {font-size:3.1rem; font-weight:700; color:#1B2533; line-height:1.06;
  letter-spacing:-0.028em; margin:0 0 1rem 0;}
.ph-title span {background: linear-gradient(90deg, #1F4E79, #2F8F9D 30%, #C08A2E 55%, #5E9A62 75%, #8E5B9F);
  -webkit-background-clip: text; background-clip: text; color: transparent;}
.ph-sub {font-size:1.12rem; color:#5B6572; line-height:1.55; max-width:30rem; margin:0 0 1.6rem 0;}
.st-key-ph_ctas a {border-radius:999px !important; padding:0.55rem 1.2rem !important;
  font-weight:500; transition:background 0.15s ease, border-color 0.15s ease;}
.st-key-ph_ctas a p {font-size:0.95rem !important; font-weight:500 !important;}
.st-key-ph_cta_primary a {background:#1F4E79 !important; border:1px solid #1F4E79 !important;}
.st-key-ph_cta_primary a p, .st-key-ph_cta_primary a span {color:#FFFFFF !important;}
.st-key-ph_cta_primary a:hover {background:#173E61 !important;}
.st-key-ph_cta_secondary a {background:#FFFFFF !important; border:1px solid #D5DCE3 !important;}
.st-key-ph_cta_secondary a p, .st-key-ph_cta_secondary a span {color:#1F4E79 !important;}
.st-key-ph_cta_secondary a:hover {background:#F4F7FA !important; border-color:#B9C4CF !important;}
.ph-stats {display:flex; gap:2.4rem; flex-wrap:wrap; margin:1.6rem 0 0.4rem 0;
  padding:1rem 0; border-top:1px solid #ECEFF2; border-bottom:1px solid #ECEFF2;}
.ph-stat b {display:block; font-size:1.6rem; font-weight:700; color:#1B2533;
  letter-spacing:-0.02em; font-variant-numeric:tabular-nums;}
.ph-stat small {font-size:0.82rem; color:#8A939E;}
.ph-section {font-size:1.15rem; letter-spacing:-0.01em; color:#17212D;
  font-weight:600; margin:2.8rem 0 0.9rem 0;}
.ph-card-art {background:#FFFFFF; border-radius:10px; padding:6px 0; margin-bottom:0.6rem;}
.ph-card-art img {display:block; width:100%; height:auto;}
.ph-card-title {font-size:1.08rem; font-weight:600; color:#1B2533; margin:0.1rem 0 0.25rem 0;}
.ph-card-sub {font-size:0.9rem; color:#6B7480; line-height:1.45; min-height:2.6rem;}
.ph-soon-row {display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px;}
.ph-soon {border:1px dashed #D5DCE3; border-radius:12px; padding:16px 18px; background:#FBFCFD;}
.ph-soon-pill {display:inline-block; font-size:0.68rem; font-weight:600; letter-spacing:0.08em;
  text-transform:uppercase; color:#9A6B1E; background:#FBF3E4; padding:2px 8px; border-radius:999px;}
.ph-soon-title {font-size:1rem; font-weight:600; color:#4A5562; margin:0.5rem 0 0.2rem 0;}
.ph-soon-sub {font-size:0.88rem; color:#8A939E; line-height:1.45;}
.ph-play-title {font-size:1.25rem; font-weight:600; color:#1B2533; margin:0.1rem 0 0.2rem 0;}
.ph-play-sub {font-size:0.95rem; color:#6B7480; line-height:1.5; min-height:4.5em;}
.ph-play-bars {display:flex; flex-direction:column; gap:5px; padding:4px 0;}
.ph-play-bars i {display:block; height:12px; border-radius:4px;}
.ph-latest-meta {font-size:0.78rem; color:#9A6B1E; font-weight:600; letter-spacing:0.05em;
  text-transform:uppercase;}
.ph-latest-title {font-size:1.2rem; font-weight:600; color:#1B2533; margin:0.15rem 0 0.2rem 0;}
.ph-latest-sub {font-size:0.92rem; color:#6B7480;}
</style>
"""


def _svg_img(name):
    data = base64.b64encode((STATIC / name).read_bytes()).decode()
    return f"<img src='data:image/svg+xml;base64,{data}' alt=''>"


@st.cache_data(show_spinner=False)
def _stats():
    history = load_index_history()
    first_year = history.index.min().year
    years = as_of_date().year - first_year
    return len(equity_universe()), years, len(MODEL_CONFIG)


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    left, right = st.columns([1, 1.15], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='ph-eyebrow'>PRISM</div>"
            "<div class='ph-by'>by <b>Avin Bhagwani</b></div>"
            "<div class='ph-title'>Every return has a <span>spectrum</span>.</div>"
            "<div class='ph-sub'>PRISM looks through Indian funds, indices and "
            "portfolios to show what really drives them.</div>",
            unsafe_allow_html=True,
        )
        with st.container(key="ph_ctas", horizontal=True, gap="small"):
            if "factor-analysis" in PAGES:
                with st.container(key="ph_cta_primary", width="content"):
                    st.page_link(PAGES["factor-analysis"], label="Analyse a fund",
                                 icon=":material/arrow_forward:", icon_position="right")
            if "fbi-intelligence" in PAGES:
                with st.container(key="ph_cta_secondary", width="content"):
                    st.page_link(PAGES["fbi-intelligence"], label="Explore indices",
                                 icon=":material/query_stats:")
    with right:
        st.iframe((STATIC / "home-prism.html").read_text(encoding="utf-8"), height=400)

    n_idx, years, n_models = _stats()
    st.markdown(
        "<div class='ph-stats'>"
        f"<div class='ph-stat'><b>{n_idx}</b><small>Nifty equity indices</small></div>"
        f"<div class='ph-stat'><b>{years} years</b><small>of index history</small></div>"
        f"<div class='ph-stat'><b>{n_models}</b><small>factor models</small></div>"
        "<div class='ph-stat'><b>Free</b><small>to use</small></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='ph-section'>Tools</div>", unsafe_allow_html=True)
    cols = st.columns(len(LENSES), gap="medium")
    for col, (path, title, art, blurb) in zip(cols, LENSES):
        with col, st.container(key=f"card_lens_{path}"):
            st.markdown(
                f"<div class='ph-card-art'>{_svg_img(art)}</div>"
                f"<div class='ph-card-title'>{title}</div>"
                f"<div class='ph-card-sub'>{blurb}</div>",
                unsafe_allow_html=True,
            )
            if path in PAGES:
                st.page_link(PAGES[path], label=f"Open {title}",
                             icon=":material/arrow_forward:")

    _play()
    _on_the_way()
    _latest_article()


GAMES = [
    ("try-to-time", "Think you can time the factors?",
     "Back next year's winning index, every year from 2008, using only what was "
     "known at the time. Then see how you did against holding all five.",
     "Play Try to Time", "bars"),
    ("can-you-handle-it", "Can you handle it?",
     "Invest at the top, right before a crash, and live through it month by month. "
     "The Sell button is always there.",
     "Play Can You Handle It?", "fall"),
]


def _play():
    games = [g for g in GAMES if g[0] in PAGES]
    if not games:
        return
    st.markdown("<div class='ph-section'>Games</div>", unsafe_allow_html=True)
    cols = st.columns(len(games), gap="medium")
    for col, (path, title, blurb, cta, art) in zip(cols, games):
        with col, st.container(key=f"card_play_{path}"):
            if art == "bars":
                pic = "".join(f"<i style='background:{c};width:{w}%'></i>" for c, w in
                              [("#C08A2E", 92), ("#2F6FB0", 74), ("#8E5B9F", 66),
                               ("#5E9A62", 48), ("#2F8F9D", 37)])
                pic = f"<div class='ph-play-bars'>{pic}</div>"
            else:
                pic = ("<svg viewBox='0 0 300 76' width='100%' height='76' preserveAspectRatio='none'>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 L215,14 L0,14Z' "
                       "fill='#F0525F' opacity='0.16'/>"
                       "<line x1='0' x2='300' y1='14' y2='14' stroke='#CBD3DC' stroke-dasharray='4 4'/>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 S270,4 300,2' "
                       "fill='none' stroke='#1F4E79' stroke-width='2.5'/></svg>")
            st.markdown(
                f"<div class='ph-card-art' style='padding:10px 12px;height:100px;display:flex;"
                f"flex-direction:column;justify-content:center'>{pic}</div>"
                f"<div class='ph-latest-meta'>Game</div>"
                f"<div class='ph-play-title'>{title}</div>"
                f"<div class='ph-play-sub'>{blurb}</div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES[path], label=cta, icon=":material/arrow_forward:")


def _on_the_way():
    st.markdown("<div class='ph-section'>On the way</div>", unsafe_allow_html=True)
    cards = "".join(
        f"<div class='ph-soon'><span class='ph-soon-pill'>Soon</span>"
        f"<div class='ph-soon-title'>{t}</div><div class='ph-soon-sub'>{d}</div></div>"
        for t, d in SOON
    )
    st.markdown(f"<div class='ph-soon-row'>{cards}</div>", unsafe_allow_html=True)


def _latest_article():
    posts, _ = sb.load_posts()
    if not posts or "writing" not in PAGES:
        return
    p = posts[0]
    st.markdown("<div class='ph-section'>From my Substack</div>", unsafe_allow_html=True)
    with st.container(key="card_latest"):
        a, b = st.columns([1, 2.4], gap="medium", vertical_alignment="center")
        with a:
            if p.cover:
                st.image(p.cover, width="stretch")
        with b:
            date = f"{p.date:%d %b %Y}" if p.date else ""
            st.markdown(
                f"<div class='ph-latest-meta'>Latest · {date}</div>"
                f"<div class='ph-latest-title'>{p.title}</div>"
                f"<div class='ph-latest-sub'>{p.subtitle}</div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES["writing"], label="Read the article",
                         icon=":material/arrow_forward:",
                         query_params={"post": p.slug})
