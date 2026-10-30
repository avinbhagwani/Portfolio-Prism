"""
PRISM entry point: page config, the left navigation, the first-visit
intro and the shared sidebar footer. Every tool's UI lives in views/.

To add a new tool:
  1. Build it in views/<name>.py with a render() function.
  2. Add an st.Page entry to PAGES below.
"""

from pathlib import Path

import streamlit as st

from views import (factor_analysis, factor_indexes, drawdown_analysis, efficient_frontier,
                   games, home, intro, sidebar, style, tutorial, writing)

STATIC = Path(__file__).resolve().parent / "static"

st.set_page_config(
    page_title="PRISM",
    page_icon=str(STATIC / "prism-icon.svg"),
    layout="wide",
)

st.logo(str(STATIC / "prism-logo-light.svg"), size="large",
        icon_image=str(STATIC / "prism-icon-light.svg"))

style.inject()

PAGES = [
    st.Page(home.render, title="Home", icon=":material/home:",
            url_path="home", default=True),
    st.Page(factor_analysis.render, title="Factor Analysis",
            icon=":material/insights:", url_path="factor-analysis"),
    st.Page(factor_indexes.render, title="FBI Intelligence",
            icon=":material/query_stats:", url_path="fbi-intelligence"),
    st.Page(drawdown_analysis.render, title="Drawdown Analysis",
            icon=":material/trending_down:", url_path="drawdown-analysis"),
    st.Page(games.render_try_to_time, title="Try to Time",
            icon=":material/sports_esports:", url_path="try-to-time"),
    st.Page(games.render_handle_it, title="Can You Handle It?",
            icon=":material/monitor_heart:", url_path="can-you-handle-it"),
    st.Page(writing.render, title="Writing",
            icon=":material/edit_note:", url_path="writing"),
    st.Page(efficient_frontier.render, title="Efficient Frontier",
            icon=":material/scatter_plot:", url_path="efficient-frontier"),
]

page = st.navigation(PAGES, position="hidden")
current = page.url_path or "home"
pages_by_path = {p.url_path or "home": p for p in PAGES}
writing.PAGES = pages_by_path
home.PAGES = pages_by_path

# Overlay slot: full intro on the first visit, a short prism transition
# naming the destination when the visitor switches pages, empty
# otherwise. Always rendered so elements below keep their positions
# between reruns (otherwise tabs would reset on the next click).
first_visit = not st.session_state.get("intro_shown")
previous = st.session_state.get("last_page")
switched = previous is not None and previous != current
if switched:
    st.session_state["transition_n"] = st.session_state.get("transition_n", 0) + 1
intro.show(
    first_visit=first_visit,
    transition_to=page.title if switched else None,
    page_key=current,
    nonce=st.session_state.get("transition_n", 0),
)
st.session_state["intro_shown"] = True
st.session_state["last_page"] = current

sidebar.render(pages_by_path, current)
tutorial.maybe_open(current)
page.run()
