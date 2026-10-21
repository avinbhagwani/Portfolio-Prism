"""
PRISM entry point: page config, the left navigation, the first-visit
intro and the shared sidebar footer. Every tool's UI lives in views/.

To add a new tool:
  1. Build it in views/<name>.py with a render() function.
  2. Add an st.Page entry to PAGES below.
"""

from pathlib import Path

import streamlit as st

from views import factor_analysis, factor_indexes, drawdown_analysis, coming_soon, intro, sidebar

STATIC = Path(__file__).resolve().parent / "static"

st.set_page_config(
    page_title="PRISM",
    page_icon=str(STATIC / "prism-icon.svg"),
    layout="wide",
)

st.logo(str(STATIC / "prism-logo-light.svg"), size="large",
        icon_image=str(STATIC / "prism-icon-light.svg"))

st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
        max-width: 1180px; padding-top: 3rem; padding-bottom: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Always render the intro slot (empty after the first run) so every
# element below keeps the same position between reruns. If it vanished,
# Streamlit would treat the page's tabs as new and reset them to the
# first tab on the visitor's first click.
intro.show(first_visit=not st.session_state.get("intro_shown"))
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
    st.Page(_efficient_frontier, title="Efficient Frontier",
            icon=":material/scatter_plot:", url_path="efficient-frontier"),
]

page = st.navigation(PAGES, position="hidden")
sidebar.render({p.url_path or "factor-analysis": p for p in PAGES},
               page.url_path or "factor-analysis")
page.run()
