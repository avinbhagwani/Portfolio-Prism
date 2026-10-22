"""
Home: what PRISM is, in as few words as possible.

  Hero      "Every return has a spectrum." over an interactive prism: the
            beam follows the cursor; drag the prism to turn it; hold to
            charge the light, release for a pulse; hover a ray to light it.
            Drifts by itself on touch screens or when idle.
  Numbers   a strip of live facts from the data
  Lenses    one card per tool, each showing its own animation
  Soon      what's coming (retirement planning, portfolio attribution,
            efficient frontier)
  Writing   the latest Substack article

The interactive prism is static/home-prism.html in a component iframe,
the one place JavaScript is allowed. Navigation stays in native
st.page_link so moving to a tool keeps the session.
"""

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
]

SOON = [
    ("Retirement planning", "Will the money last? Plan income for every stage."),
    ("Portfolio attribution", "Which decisions added return, and which cost it."),
    ("Efficient frontier", "The best mix for the risk you can take."),
]

CSS = """
<style>
.ph-eyebrow {font-size:0.8rem; letter-spacing:0.18em; text-transform:uppercase;
  color:#1F4E79; font-weight:600; margin:0 0 0.5rem 0;}
.ph-title {font-size:3rem; font-weight:700; color:#1B2533; line-height:1.05;
  letter-spacing:-0.025em; margin:0 0 0.7rem 0;}
.ph-title span {background: linear-gradient(90deg, #1F4E79, #2F8F9D 30%, #C08A2E 55%, #5E9A62 75%, #8E5B9F);
  -webkit-background-clip: text; background-clip: text; color: transparent;}
.ph-sub {font-size:1.15rem; color:#5B6572; line-height:1.5; max-width:38rem; margin:0;}
.ph-stats {display:flex; gap:2.4rem; flex-wrap:wrap; margin:0.6rem 0 0.4rem 0;
  padding:1rem 0; border-top:1px solid #ECEFF2; border-bottom:1px solid #ECEFF2;}
.ph-stat b {display:block; font-size:1.6rem; font-weight:700; color:#1B2533;
  letter-spacing:-0.02em; font-variant-numeric:tabular-nums;}
.ph-stat small {font-size:0.82rem; color:#8A939E;}
.ph-section {font-size:0.78rem; letter-spacing:0.14em; text-transform:uppercase;
  color:#8A939E; font-weight:600; margin:2.2rem 0 0.8rem 0;}
.ph-card-art {background:#F7F9FB; border-radius:10px; padding:6px 0; margin-bottom:0.6rem;}
.ph-card-art img {display:block; width:100%; height:auto;}
.ph-card-title {font-size:1.08rem; font-weight:600; color:#1B2533; margin:0.1rem 0 0.25rem 0;}
.ph-card-sub {font-size:0.9rem; color:#6B7480; line-height:1.45; min-height:2.6rem;}
.ph-soon-row {display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px;}
.ph-soon {border:1px dashed #D5DCE3; border-radius:12px; padding:16px 18px; background:#FBFCFD;}
.ph-soon-pill {display:inline-block; font-size:0.68rem; font-weight:600; letter-spacing:0.08em;
  text-transform:uppercase; color:#9A6B1E; background:#FBF3E4; padding:2px 8px; border-radius:999px;}
.ph-soon-title {font-size:1rem; font-weight:600; color:#4A5562; margin:0.5rem 0 0.2rem 0;}
.ph-soon-sub {font-size:0.88rem; color:#8A939E; line-height:1.45;}
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
    st.markdown(
        "<div class='ph-eyebrow'>PRISM</div>"
        "<div class='ph-title'>Every return has a <span>spectrum</span>.</div>"
        "<div class='ph-sub'>PRISM looks through Indian funds, indices and "
        "portfolios to show what really drives them.</div>",
        unsafe_allow_html=True,
    )

    components.html((STATIC / "home-prism.html").read_text(encoding="utf-8"),
                    height=380)

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

    st.markdown("<div class='ph-section'>Pick a lens</div>", unsafe_allow_html=True)
    cols = st.columns(len(LENSES), gap="medium")
    for col, (path, title, art, blurb) in zip(cols, LENSES):
        with col, st.container(border=True):
            st.markdown(
                f"<div class='ph-card-art'>{_svg_img(art)}</div>"
                f"<div class='ph-card-title'>{title}</div>"
                f"<div class='ph-card-sub'>{blurb}</div>",
                unsafe_allow_html=True,
            )
            if path in PAGES:
                st.page_link(PAGES[path], label=f"Open {title}",
                             icon=":material/arrow_forward:")

    _on_the_way()
    _latest_article()


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
    with st.container(border=True):
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
