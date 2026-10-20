"""
PRISM entry point: page config, the top navigation bar and the shared
footer. Every tool's UI lives in views/.

To add a new tool:
  1. Build it in views/<name>.py with a render() function.
  2. Add an st.Page entry to PAGES below.
"""

import streamlit as st

from views import factor_analysis, factor_indexes, drawdown_analysis, coming_soon

st.set_page_config(
    page_title="PRISM",
    page_icon="static/prism-icon.svg",
    layout="wide",
)

st.logo("static/prism-logo.svg", size="large", icon_image="static/prism-logo.svg")

st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
        max-width: 1180px; padding-top: 3.2rem; padding-bottom: 3rem;
    }
    [data-testid="stHeader"] {border-bottom: 1px solid #ECEFF2;}
    .prism-footer {color:#8A939E; font-size:0.82rem; margin-top:3rem;
        padding-top:1.2rem; border-top:1px solid #ECEFF2;}
    .prism-footer a {color:#6B7480;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _efficient_frontier():
    coming_soon.render("Efficient Frontier")


PAGES = [
    st.Page(factor_analysis.render, title="Factor Analysis",
            url_path="factor-analysis", default=True),
    st.Page(factor_indexes.render, title="FBI Intelligence",
            url_path="fbi-intelligence"),
    st.Page(drawdown_analysis.render, title="Drawdown Analysis",
            url_path="drawdown-analysis"),
    st.Page(_efficient_frontier, title="Efficient Frontier (soon)",
            url_path="efficient-frontier"),
]

page = st.navigation(PAGES, position="top")
page.run()

st.markdown(
    "<div class='prism-footer'>Questions, bugs or ideas? "
    "<a href='https://www.linkedin.com/in/avinbhagwani69/'>Connect on LinkedIn</a> "
    "or write to avinbhagwani69@gmail.com.</div>",
    unsafe_allow_html=True,
)
