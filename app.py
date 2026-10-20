"""
PRISM entry point. Owns page config and the sidebar navigation only —
every tool's actual UI lives in views/, imported and dispatched here.

To add a new tool:
  1. Build it in views/<name>.py with a render() function.
  2. Add an entry to NAV_ITEMS below.
  3. Add a branch in the routing block at the bottom.
"""

import streamlit as st

from views import factor_analysis, factor_indexes, drawdown_analysis, coming_soon

st.set_page_config(
    page_title="Factor Analysis",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# PRISM NAVIGATION
# =========================================================

st.sidebar.title("PRISM")
st.sidebar.markdown("---")

NAV_ITEMS = [
    {"key": "factor", "label": "Factor Analysis"},
    {"key": "fbi", "label": "FBI Intelligence"},
    {"key": "drawdown", "label": "Drawdown Analysis"},
    {
        "key": "efficient_frontier",
        "label": "Efficient Frontier",
        "badge": "Under Development"
    },
]

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "factor"

st.markdown(
    """
    <style>
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]
        div.stButton > button {
        width: 100%;
        justify-content: flex-start;
        text-align: left;
        border-radius: 10px;
        padding: 0.55rem 0.9rem;
        margin-bottom: 0.3rem;
        font-weight: 500;
        font-size: 0.92rem;
        border: 1px solid transparent;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    div[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: transparent;
        color: inherit;
        opacity: 0.85;
    }
    div[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: rgba(128, 128, 128, 0.15);
        border-color: rgba(128, 128, 128, 0.25);
        opacity: 1;
    }
    div[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #2563eb;
        border-color: #2563eb;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.35);
    }
    </style>
    """,
    unsafe_allow_html=True
)

for item in NAV_ITEMS:
    is_active = st.session_state.nav_page == item["key"]

    label = item["label"]
    if item.get("badge"):
        label += f"   ·  {item['badge']}"

    if st.sidebar.button(
        label,
        key=f"nav_btn_{item['key']}",
        type="primary" if is_active else "secondary",
        use_container_width=True
    ):
        st.session_state.nav_page = item["key"]
        st.rerun()

nav_page = st.session_state.nav_page

st.sidebar.markdown("---")
st.sidebar.caption(
    "Have a question, found a bug, or want to suggest a feature? "
    "Reach out anytime — "
    "[connect on LinkedIn](https://www.linkedin.com/in/avinbhagwani69/) "
    "or drop me a line at avinbhagwani69@gmail.com."
)

# =========================================================
# ROUTING
# =========================================================

if nav_page == "fbi":
    factor_indexes.render()

elif nav_page == "drawdown":
    drawdown_analysis.render()

elif nav_page == "efficient_frontier":
    coming_soon.render("Efficient Frontier")

else:
    factor_analysis.render()
