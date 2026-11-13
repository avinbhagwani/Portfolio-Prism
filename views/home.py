"""
Home: PRISM as a small solar system that fills the page.

  The star   PRISM itself. Clicking it opens the tour.
  Worlds     one per page, each in its own colour (the same spectral
             line it carries in the left navigation): the four tools on
             the inner orbits, the two games sharing an outer one, and
             Writing as a comet. Hover or tab to a world and time stops
             while it says what it is for; click it to go there. Drag
             the sky to spin the system.
  Far out    tools that are on the way, drawn as faint dashed bodies.

The scene is static/home-solar.html in an st.iframe, the one place
JavaScript is allowed. A click on a world clicks the matching hidden
st.page_link below, so moving to a tool keeps the session exactly as
the left navigation does. The camera flies into the world first, and
the tool page opens out of that world's colour (views/intro.py); coming
back, the system zooms out of the world that was just left.
"""

import json
from pathlib import Path

import streamlit as st

from core.config import MODEL_CONFIG
from core.fbi_metrics import as_of_date, equity_universe
from core.index_data import load_index_history
from views import tutorial
from views.style import LINES

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = {}  # set by app.py

# url_path, name, what it is for, call to action. Order = tab order.
WORLDS = [
    ("factor-analysis", "Factor Analysis", "What drives a fund's returns", "Open"),
    ("fbi-intelligence", "FBI Intelligence", "How factor indices have behaved", "Open"),
    ("drawdown-analysis", "Drawdown Analysis", "How far it fell, how long to recover", "Open"),
    ("efficient-frontier", "Efficient Frontier", "The best mix for the risk", "Open"),
    ("try-to-time", "Try to Time", "Pick next year's winning factor", "Play"),
    ("can-you-handle-it", "Can You Handle It?", "Sit through a real crash", "Play"),
    ("writing", "Writing", "Articles from my Substack", "Read"),
]

SOON = ["Retirement planning", "Portfolio attribution"]
_WORDS = {5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}

CSS = """
<style>
/* Home only: the scene fills the whole main area, edge to edge */
[data-testid="stMain"] {background:#05090F; overflow:hidden;}
[data-testid="stMainBlockContainer"] {max-width:none; padding:0; height:100vh;}
[data-testid="stHeader"] {background:transparent;}
.st-key-solar_stage {position:absolute; inset:0; z-index:1; height:100vh !important;}
.st-key-solar_stage *, .st-key-solar_stage iframe {
  height:100vh !important; width:100% !important; display:block; border:0;}
/* the page links a world clicks: present, never seen, not in the tab order */
.st-key-solar_links {position:absolute; width:1px; height:1px; overflow:hidden;
  visibility:hidden; pointer-events:none;}
/* the tour pill floats over the sky, bottom right */
[class*="st-key-tutpill_"][class*="home"] {
  position:absolute !important; right:clamp(20px, 4vw, 56px);
  bottom:calc((clamp(34px, 6vh, 56px) - 2rem) / 2);
  left:auto; margin:0 !important; z-index:3; width:auto !important;}
[class*="st-key-tutpill_"][class*="home"] button {
  background:transparent !important; border:1px solid #2C445D !important; border-radius:2px !important;}
[class*="st-key-tutpill_"][class*="home"] button:hover {border-color:#D9B36A !important;}
[class*="st-key-tutpill_"][class*="home"] button p {color:#D5DEE8 !important;}
[class*="st-key-tutpill_"][class*="home"] button [data-testid="stIconMaterial"] {color:#D9B36A !important;}
@media (max-width:640px) {
  [class*="st-key-tutpill_"][class*="home"] {right:14px; bottom:calc(clamp(34px, 6vh, 56px) + 10px);}
  [class*="st-key-tutpill_"][class*="home"] button {background:rgba(3,7,13,.8) !important;}
}
</style>
"""


@st.cache_data(show_spinner=False)
def _stats():
    history = load_index_history()
    first_year = history.index.min().year
    years = as_of_date().year - first_year
    return len(equity_universe()), years, len(MODEL_CONFIG)


@st.cache_data(show_spinner=False)
def _template():
    return (STATIC / "home-solar.html").read_text(encoding="utf-8")


def render():
    st.markdown(CSS, unsafe_allow_html=True)

    worlds = [{"path": p, "name": n, "desc": d, "cta": c, "idx": LINES[p][1]}
              for p, n, d, c in WORLDS if p in PAGES]
    n_idx, years, n_models = _stats()
    data = {
        "worlds": worlds,
        "soon": SOON,
        "lede": ("PRISM looks through Indian funds, indices and portfolios to show "
                 f"what really drives them. {_WORDS.get(len(worlds), len(worlds))} worlds, "
                 "one question each."),
        "tour": "New here? Start with the tour",
        # the page just left, so the system can zoom back out of its world
        "from": st.session_state.get("solar_from"),
        "stats": [[n_idx, "Nifty equity indices"], [years, "years of history"],
                  [n_models, "factor models"], ["Free", "to use"]],
    }
    with st.container(key="solar_stage"):
        st.iframe(_template().replace("__DATA__", json.dumps(data)), height=700)

    with st.container(key="solar_links"):
        for w in worlds:
            st.page_link(PAGES[w["path"]], label=w["name"])

    tutorial.launcher("home", "New here? Take the tour")
