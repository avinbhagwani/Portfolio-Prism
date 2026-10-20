"""
Light/dark theme detection and matplotlib re-colouring, shared by every
chart in the app so none of them show up as a bright white block when
Streamlit is in dark mode.
"""

import streamlit as st

THEME_COLORS = {
    "dark": {
        "bg": "#0e1117",       # matches Streamlit's default dark background
        "text": "#e6e6e6",
        "grid": "#333333",
        "spine": "#4d4d4d",
    },
    "light": {
        "bg": "#ffffff",
        "text": "#31333f",     # matches Streamlit's default light text
        "grid": "#d6d6d6",
        "spine": "#cccccc",
    },
}

# Fixed colour assignment for up to two indices being compared, used
# consistently across annual returns, rolling returns, and drawdown
# charts so the same index is always the same colour on screen.
INDEX_COLORS = ["#2563eb", "#f97316"]  # blue, orange

# Fixed colour assignment for the Quilt tab (up to 7 indices) — flat,
# high-contrast colours with black text on every one, matching the
# classic printed "asset allocation quilt" style. Chosen to be easy to
# tell apart at a glance: warm/cool and light/dark are both varied.
QUILT_COLORS = [
    "#3FA8A4",  # teal
    "#C48CB0",  # mauve
    "#AFC6EA",  # light blue
    "#8FC67A",  # green
    "#F0AE68",  # peach/orange
    "#F5D547",  # gold
    "#8C9EB8",  # slate blue-grey (7th, for when all 7 slots are used)
]


def get_streamlit_theme_type():
    """Best-effort detection of the viewer's active light/dark theme."""
    try:
        theme_type = st.context.theme.type
        if theme_type in ("light", "dark"):
            return theme_type
    except Exception:
        pass

    try:
        base = st.get_option("theme.base")
        if base in ("light", "dark"):
            return base
    except Exception:
        pass

    return "light"


def apply_chart_theme(fig, axes):
    """
    Recolour a matplotlib figure (background, text, grid, spines, legend)
    to match Streamlit's currently active light/dark theme.
    """
    theme_type = get_streamlit_theme_type()
    c = THEME_COLORS[theme_type]

    if not isinstance(axes, (list, tuple)):
        axes = [axes]

    fig.patch.set_facecolor(c["bg"])

    for ax in axes:
        ax.set_facecolor(c["bg"])

        ax.title.set_color(c["text"])
        ax.xaxis.label.set_color(c["text"])
        ax.yaxis.label.set_color(c["text"])
        ax.tick_params(colors=c["text"], which="both")

        for spine in ax.spines.values():
            spine.set_color(c["spine"])

        for line in ax.get_xgridlines() + ax.get_ygridlines():
            line.set_color(c["grid"])

        # Recolour any free-floating text annotations (e.g. bar value labels)
        for txt in ax.texts:
            txt.set_color(c["text"])

        legend = ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(c["bg"])
            legend.get_frame().set_edgecolor(c["spine"])
            for text in legend.get_texts():
                text.set_color(c["text"])

    return c
