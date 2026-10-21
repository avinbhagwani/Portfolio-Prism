"""
Drawdown Analysis — same category/index picker as FBI Intelligence, but
focused on peak-to-trough drawdowns: current drawdown, max drawdown, and
the worst historical drawdown episodes (with recovery status) per index.
"""

import matplotlib.pyplot as plt
import streamlit as st

from core.index_data import get_index_levels
from core.index_analytics import (
    drawdown_series,
    drawdown_summary,
    find_drawdown_episodes,
)
from charts.index_chart import make_drawdown_chart
from charts.render import show_chart
from views._shared import select_indices

DEFAULT_INDICES = ["NIFTY 50", "NIFTY MIDCAP 100"]


def render():
    st.title("📉 Drawdown Analysis")
    st.caption(
        "Peak-to-trough drawdowns for Nifty indices — how deep, how "
        "long, and whether they've recovered."
    )

    st.divider()

    selected = select_indices(
        key_prefix="drawdown",
        max_indices=2,
        default_indices=DEFAULT_INDICES
    )

    if not selected:
        st.info("Select at least one index to see drawdowns.")
        return

    levels = get_index_levels(selected)

    if levels.empty:
        st.warning("No price history available for the selected index(es).")
        return

    legend_line = "  ".join(
        f"🟦 {name}" if i == 0 else f"🟧 {name}"
        for i, name in enumerate(selected)
    )
    st.markdown(legend_line)

    # =========================================================
    # DRAWDOWN CHART
    # =========================================================

    dd = drawdown_series(levels)

    if dd.empty:
        st.warning("Not enough history to compute drawdowns.")
        return

    show_chart(make_drawdown_chart, dd)

    # =========================================================
    # SUMMARY
    # =========================================================

    st.subheader("Summary")

    summary = drawdown_summary(levels)

    st.dataframe(
        summary.style.format({
            "Max Drawdown (%)": "{:.2f}",
            "Current Drawdown (%)": "{:.2f}",
            "Max Drawdown Date": lambda d: d.strftime("%d %b %Y"),
        }),
        width="stretch"
    )

    # =========================================================
    # WORST DRAWDOWN EPISODES
    # =========================================================

    st.subheader("Worst Drawdown Episodes")

    for name in selected:
        st.markdown(f"**{name}**")

        episodes = find_drawdown_episodes(levels, name, top_n=5)

        if not episodes:
            st.caption("No drawdowns found in the available history.")
            continue

        rows = []
        for ep in episodes:
            rows.append({
                "Peak Date": ep["peak_date"].strftime("%d %b %Y"),
                "Trough Date": ep["trough_date"].strftime("%d %b %Y"),
                "Depth (%)": round(ep["depth_pct"], 2),
                "Recovery Date": (
                    ep["recovery_date"].strftime("%d %b %Y")
                    if ep["recovery_date"] is not None
                    else "Not yet recovered"
                ),
            })

        st.dataframe(rows, width="stretch", hide_index=True)
