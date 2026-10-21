"""
PRISM entry point: page config, the left navigation, the first-visit
intro and the shared sidebar footer. Every tool's UI lives in views/.

To add a new tool:
  1. Build it in views/<name>.py with a render() function.
  2. Add an st.Page entry to PAGES below.
"""

import streamlit as st

from views import factor_analysis, factor_indexes, drawdown_analysis, coming_soon, intro

st.set_page_config(
    page_title="PRISM",
    page_icon="static/prism-icon.svg",
    layout="wide",
)

st.logo("static/prism-logo.svg", size="large", icon_image="static/prism-icon.svg")

st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
        max-width: 1180px; padding-top: 3rem; padding-bottom: 3rem;
    }
    [data-testid="stSidebarNav"] a {border-radius: 8px; padding: 0.15rem 0.5rem;}
    [data-testid="stSidebarNav"] a span {font-size: 0.95rem;}
    [data-testid="stSidebarNav"] a[aria-current="page"] {background: #E3EAF2;}
    [data-testid="stSidebarNav"] a[aria-current="page"] span {color: #1F4E79; font-weight: 600;}
    .prism-side-foot {color:#8A939E; font-size:0.8rem; line-height:1.5;
        border-top:1px solid #E3E7EC; padding-top:0.9rem; margin-top:0.6rem;}
    .prism-side-foot a {color:#6B7480;}
    </style>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("intro_shown"):
    intro.show()
    st.session_state["intro_shown"] = True


def _efficient_frontier():
    coming_soon.render("Efficient Frontier")


PAGES = [
    st.Page(factor_analysis.render, title="Factor Analysis",
            icon=":material/insights:", url_path="factor-analysis", default=True),
    st.Page(factor_indexes.render, title="FBI Intelligence",
            icon=":material/query_stats:", url_path="fbi-intelligence"),
    st.Page(drawdown_analysis.render, title="Drawdown Analysis",
            icon=":material/trending_down:", url_path="drawdown-analysis"),
    st.Page(_efficient_frontier, title="Efficient Frontier (soon)",
            icon=":material/scatter_plot:", url_path="efficient-frontier"),
]

page = st.navigation(PAGES, position="sidebar")

st.sidebar.markdown(
    "<div class='prism-side-foot'>Questions, bugs or ideas?<br>"
    "<a href='https://www.linkedin.com/in/avinbhagwani69/'>Connect on LinkedIn</a> "
    "or write to avinbhagwani69@gmail.com.</div>",
    unsafe_allow_html=True,
)

page.run()
