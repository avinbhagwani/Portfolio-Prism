"""
FBI Intelligence — Factor-Based Index Intelligence.

Layout: the three tabs are the first thing on the page. The Index 1 /
Index 2 picker lives at the top of the Returns tab rather than above
the tabs — but since Streamlit renders every tab's body on each run
(only the inactive ones are visually hidden), that selection is
computed before the Risk tab's code runs and is simply reused there,
so switching to Risk directly still shows results for whatever's
selected in Returns without asking twice.

Tabs:
  Returns                 — calendar-year returns, rolling returns,
                             head-to-head outperformance
  Risk                    — drawdown, rolling volatility, and upside/
                             downside capture vs a selectable benchmark
                             (defaults to NIFTY 500)
  Risk-Return Scatterplot — pick a category, see every index in it
                             plotted by risk vs return against NIFTY 500
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from core.index_data import get_index_levels, list_categories, list_indices
from core.index_analytics import (
    annual_returns,
    build_quilt,
    rolling_returns,
    rolling_outperformance,
    rolling_std,
    drawdown_series,
    drawdown_summary,
    find_drawdown_episodes,
    capture_ratios,
    risk_return_points,
)
from charts.index_chart import (
    make_annual_returns_chart,
    make_rolling_returns_chart,
    make_rolling_std_chart,
    make_drawdown_chart,
    make_capture_ratio_chart,
    make_risk_return_scatter,
)
from charts.quilt_chart import make_quilt_chart, build_quilt_color_map
from charts.theme import INDEX_COLORS
from charts.render import show_figure
from views._shared import select_indices, select_single_index

ROLLING_WINDOW_OPTIONS = {
    "1 Year": 1,
    "3 Year": 3,
    "5 Year": 5,
    "7 Year": 7,
    "10 Year": 10,
}

LOOKBACK_OPTIONS = {
    "1 Year": 1,
    "3 Year": 3,
    "5 Year": 5,
    "10 Year": 10,
    "Full History": None,
}

ALL_CATEGORIES_OPTION = "All Categories"

DEFAULT_BENCHMARK = "NIFTY 500"
DEFAULT_INDICES = ["NIFTY200 MOMENTUM 30", "NIFTY500 VALUE 50"]
DEFAULT_QUILT_INDICES = [
    "NIFTY 50",
    "NIFTY MIDCAP 100",
    "NIFTY SMALLCAP 100",
    "NIFTY BANK",
    "NIFTY200 MOMENTUM 30",
]

# One-click quilt presets — clicking a button loads the category filter
# to "All Categories" and the index multiselect to this exact list.
QUILT_PRESETS = [
    {
        "label": "Factor Quilt - 500",
        "indices": [
            "NIFTY500 VALUE 50",
            "NIFTY500 LOW VOLATILITY 50",
            "NIFTY 500",
            "NIFTY500 EQUAL WEIGHT",
            "NIFTY500 MOMENTUM 50",
            "NIFTY500 QUALITY 50",
        ],
    },
    {
        "label": "Factor Quilt - 200",
        "indices": [
            "NIFTY 200",
            "NIFTY200 MOMENTUM 30",
            "NIFTY200 VALUE 30",
            "NIFTY100 LOW VOLATILITY 30",
            "NIFTY200 QUALITY 30",
        ],
    },
]


def render():
    st.title("🕵️ FBI Intelligence")
    st.caption(
        "Factor-Based Index Intelligence — returns, risk, and "
        "risk-return positioning across Nifty factor and strategy indices."
    )

    tab_returns, tab_risk, tab_scatter, tab_quilt = st.tabs(
        ["Returns", "Risk", "Risk-Return Scatterplot", "Quilt"]
    )

    with tab_returns:
        st.caption(
            "Choose up to two indices — this selection is shared with "
            "the Risk tab."
        )

        selected = select_indices(
            key_prefix="fbi",
            max_indices=2,
            default_indices=DEFAULT_INDICES
        )

        levels = get_index_levels(selected) if selected else None

        if not selected or levels is None or levels.empty:
            st.info("Select at least one index above to see returns.")
        else:
            _show_legend(selected)
            st.divider()
            _render_returns_tab(levels, selected)

    with tab_risk:
        if not selected or levels is None or levels.empty:
            st.info(
                "Select at least one index in the Returns tab to see "
                "risk metrics."
            )
        else:
            _show_legend(selected)
            st.divider()
            _render_risk_tab(levels, selected)

    with tab_scatter:
        _render_scatter_tab()

    with tab_quilt:
        _render_quilt_tab()


def _show_legend(selected):
    legend_line = "  ".join(
        f"🟦 {name}" if i == 0 else f"🟧 {name}"
        for i, name in enumerate(selected)
    )
    st.markdown(legend_line)


# =========================================================
# RETURNS TAB
# =========================================================

def _render_returns_tab(levels, selected):
    st.subheader("Annual Returns")

    annual_df = annual_returns(levels)

    if annual_df.empty:
        st.warning("Not enough history to compute calendar-year returns.")
    else:
        fig = make_annual_returns_chart(annual_df)
        show_figure(fig)
        plt.close(fig)

        with st.expander("View annual returns table"):
            st.dataframe(
                annual_df.style.format("{:.2f}"),
                use_container_width=True
            )

    st.subheader("Rolling Returns")

    window_label = st.selectbox(
        "Rolling Window",
        list(ROLLING_WINDOW_OPTIONS.keys()),
        index=list(ROLLING_WINDOW_OPTIONS.keys()).index("3 Year"),
        key="fbi_returns_window"
    )
    window_years = ROLLING_WINDOW_OPTIONS[window_label]

    rolling_df = rolling_returns(levels, window_years)

    if rolling_df.empty:
        st.warning(
            f"Not enough history for a {window_label.lower()} rolling "
            f"return on the selected index(es)."
        )
        return

    fig = make_rolling_returns_chart(rolling_df, window_years)
    show_figure(fig)
    plt.close(fig)

    with st.expander("View rolling returns table"):
        st.dataframe(rolling_df.round(2), use_container_width=True)

    if len(selected) == 2:
        index_a, index_b = selected

        st.subheader("Head-to-Head")

        result = rolling_outperformance(rolling_df, index_a, index_b)

        if result is None or result["total_periods"] == 0:
            st.info(
                "No overlapping rolling-return periods between these "
                "two indices yet."
            )
        else:
            c1, c2, c3 = st.columns(3)

            c1.metric(
                f"🟦 {index_a} led",
                f"{result['wins_a']} periods",
                f"{result['pct_a']:.1f}%"
            )
            c2.metric(
                f"🟧 {index_b} led",
                f"{result['wins_b']} periods",
                f"{result['pct_b']:.1f}%"
            )
            c3.metric("Total periods compared", result["total_periods"])

            st.caption(
                f"When {index_a} led, it did so by "
                f"{result['avg_margin_when_a_leads']:.2f} pts on average. "
                f"When {index_b} led, it did so by "
                f"{result['avg_margin_when_b_leads']:.2f} pts on average."
            )

            diff = result["diff_series"]

            fig, ax = plt.subplots(figsize=(12, 3.5))
            colors = [
                INDEX_COLORS[0] if v >= 0 else INDEX_COLORS[1]
                for v in diff.values
            ]
            ax.bar(diff.index, diff.values, color=colors, width=20)
            ax.axhline(0, color="#888888", linestyle="--", linewidth=1)
            ax.set_title(
                f"{index_a} minus {index_b} — Rolling Return Gap (pts)",
                fontsize=13,
                fontweight="bold"
            )
            ax.grid(axis="y", linestyle=":", alpha=0.4)
            fig.autofmt_xdate()
            fig.tight_layout()

            show_figure(fig)
            plt.close(fig)
    else:
        st.caption(
            "Select a second index above to see a head-to-head "
            "outperformance comparison."
        )


# =========================================================
# RISK TAB
# =========================================================

def _render_risk_tab(levels, selected):
    st.subheader("Drawdown")

    dd = drawdown_series(levels)

    if dd.empty:
        st.warning("Not enough history to compute drawdowns.")
    else:
        fig = make_drawdown_chart(dd)
        show_figure(fig)
        plt.close(fig)

        summary = drawdown_summary(levels)
        st.dataframe(
            summary.style.format({
                "Max Drawdown (%)": "{:.2f}",
                "Current Drawdown (%)": "{:.2f}",
                "Max Drawdown Date": lambda d: d.strftime("%d %b %Y"),
            }),
            use_container_width=True
        )

        with st.expander("Worst drawdown episodes"):
            for name in selected:
                st.markdown(f"**{name}**")

                episodes = find_drawdown_episodes(levels, name, top_n=5)

                if not episodes:
                    st.caption("No drawdowns found in the available history.")
                    continue

                rows = [
                    {
                        "Peak Date": ep["peak_date"].strftime("%d %b %Y"),
                        "Trough Date": ep["trough_date"].strftime("%d %b %Y"),
                        "Depth (%)": round(ep["depth_pct"], 2),
                        "Recovery Date": (
                            ep["recovery_date"].strftime("%d %b %Y")
                            if ep["recovery_date"] is not None
                            else "Not yet recovered"
                        ),
                    }
                    for ep in episodes
                ]

                st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Rolling Volatility")

    vol_window_label = st.selectbox(
        "Rolling Window",
        list(ROLLING_WINDOW_OPTIONS.keys()),
        index=list(ROLLING_WINDOW_OPTIONS.keys()).index("3 Year"),
        key="fbi_risk_window"
    )
    vol_window_years = ROLLING_WINDOW_OPTIONS[vol_window_label]

    vol_df = rolling_std(levels, vol_window_years)

    if vol_df.empty:
        st.warning(
            f"Not enough history for a {vol_window_label.lower()} rolling "
            f"volatility on the selected index(es)."
        )
    else:
        fig = make_rolling_std_chart(vol_df, vol_window_years)
        show_figure(fig)
        plt.close(fig)

        with st.expander("View rolling volatility table"):
            st.dataframe(vol_df.round(2), use_container_width=True)

    st.subheader("Upside / Downside Capture")
    st.caption(
        "How much of the benchmark's gains and losses each index "
        "captured, month by month. Above 100% upside is good; below "
        "100% downside is good."
    )

    b1, b2 = st.columns(2)

    with b1:
        benchmark = select_single_index(
            "Benchmark",
            key_prefix="fbi_capture_benchmark",
            default_index=DEFAULT_BENCHMARK,
            allow_none=False
        )

    with b2:
        capture_lookback_label = st.selectbox(
            "Lookback Period",
            list(LOOKBACK_OPTIONS.keys()),
            index=list(LOOKBACK_OPTIONS.keys()).index("5 Year"),
            key="fbi_capture_lookback"
        )

    capture_lookback_years = LOOKBACK_OPTIONS[capture_lookback_label]

    if benchmark in selected and len(selected) == 1:
        st.info(
            f"The only selected index is the benchmark itself "
            f"({benchmark}) — pick a different benchmark, or add a "
            f"second index above, to see capture ratios."
        )
        return

    capture_levels = get_index_levels(list(set(selected) | {benchmark}))

    if capture_levels.empty or benchmark not in capture_levels.columns:
        st.warning("No overlapping history with the selected benchmark.")
        return

    capture_df = capture_ratios(
        capture_levels,
        selected,
        benchmark,
        lookback_years=capture_lookback_years
    )

    if capture_df.empty:
        st.warning(
            f"Not enough overlapping monthly data against {benchmark} "
            f"over the {capture_lookback_label.lower()} lookback."
        )
        return

    fig = make_capture_ratio_chart(capture_df)
    show_figure(fig)
    plt.close(fig)

    st.dataframe(
        capture_df.style.format({
            "Upside Capture (%)": "{:.1f}",
            "Downside Capture (%)": "{:.1f}",
            "Up Months": "{:.0f}",
            "Down Months": "{:.0f}",
        }),
        use_container_width=True
    )


# =========================================================
# RISK-RETURN SCATTERPLOT TAB
# =========================================================

def _render_scatter_tab():
    st.caption(
        f"Pick a category to plot every index in it by risk vs return, "
        f"benchmarked against {DEFAULT_BENCHMARK}. The dashed lines cross "
        f"at {DEFAULT_BENCHMARK}'s own risk/return, splitting the chart "
        f"into four quadrants relative to it."
    )

    c1, c2 = st.columns(2)

    with c1:
        category = st.selectbox(
            "Category",
            list_categories(),
            key="fbi_scatter_category"
        )

    with c2:
        lookback_label = st.selectbox(
            "Lookback Period",
            list(LOOKBACK_OPTIONS.keys()),
            index=list(LOOKBACK_OPTIONS.keys()).index("5 Year"),
            key="fbi_scatter_lookback"
        )

    lookback_years = LOOKBACK_OPTIONS[lookback_label]

    index_names = list_indices(category=category)

    if not index_names:
        st.warning("No indices found in this category.")
        return

    # Always pull the benchmark too, even if its own category isn't selected
    names_to_load = list(index_names)
    if DEFAULT_BENCHMARK not in names_to_load:
        names_to_load.append(DEFAULT_BENCHMARK)

    levels = get_index_levels(names_to_load)

    if levels.empty:
        st.warning("No price history available for this category.")
        return

    points = risk_return_points(levels, lookback_years=lookback_years)

    if points.empty or DEFAULT_BENCHMARK not in points.index:
        st.warning(
            f"Not enough overlapping history to plot this category "
            f"against {DEFAULT_BENCHMARK} over the {lookback_label.lower()} "
            f"lookback. Try a shorter lookback."
        )
        return

    fig = make_risk_return_scatter(points, DEFAULT_BENCHMARK)
    show_figure(fig)
    plt.close(fig)

    with st.expander("View underlying risk/return data"):
        st.dataframe(
            points.sort_values("Return", ascending=False).style.format({
                "Return": "{:.2f}",
                "Volatility": "{:.2f}",
                "Observations": "{:.0f}",
            }),
            use_container_width=True
        )


# =========================================================
# QUILT TAB
# =========================================================

def _render_quilt_tab():
    st.caption(
        "The classic asset-allocation quilt: pick up to 7 indices and a "
        "year range, and see how their calendar-year rankings shuffle "
        "from year to year. Each index keeps the same colour in every "
        "column."
    )

    st.write("**Quick presets**")
    preset_cols = st.columns(len(QUILT_PRESETS))

    for col, preset in zip(preset_cols, QUILT_PRESETS):
        with col:
            if st.button(
                preset["label"],
                key=f"fbi_quilt_preset_{preset['label']}",
                width="stretch"
            ):
                st.session_state["fbi_quilt_category"] = ALL_CATEGORIES_OPTION
                st.session_state["fbi_quilt_indices"] = preset["indices"]
                st.rerun()

    c1, c2 = st.columns([1, 2])

    with c1:
        category = st.selectbox(
            "Category",
            [ALL_CATEGORIES_OPTION] + list_categories(),
            key="fbi_quilt_category"
        )

    category_filter = None if category == ALL_CATEGORIES_OPTION else category
    available = list_indices(category=category_filter)

    if not available:
        st.warning("No indices found in this category.")
        return

    default_selection = [
        name for name in DEFAULT_QUILT_INDICES if name in available
    ] or available[:5]

    # Initialize session_state directly rather than via the widget's
    # default= param — the preset buttons above also write this key
    # directly, and mixing default= with direct session_state writes
    # on the same key triggers a Streamlit warning even though it
    # still behaves correctly. This sidesteps it entirely.
    if "fbi_quilt_indices" not in st.session_state:
        st.session_state["fbi_quilt_indices"] = default_selection

    with c2:
        selected = st.multiselect(
            "Indices (up to 7)",
            available,
            key="fbi_quilt_indices"
        )

    if len(selected) > 7:
        st.warning(
            "Only the first 7 selections are used for the quilt — "
            "remove one to add a different index."
        )
        selected = selected[:7]

    if not selected:
        st.info("Select at least two indices to build a quilt.")
        return

    if len(selected) == 1:
        st.info("Select at least one more index to build a quilt.")
        return

    levels = get_index_levels(selected)

    if levels.empty:
        st.warning("No price history available for the selected indices.")
        return

    annual_df = annual_returns(levels)

    if annual_df.empty:
        st.warning("Not enough history to compute calendar-year returns.")
        return

    years = sorted(annual_df.index.tolist())

    d1, d2 = st.columns(2)

    with d1:
        start_year = st.selectbox(
            "Start Year",
            years,
            index=max(0, len(years) - 10),
            key="fbi_quilt_start_year"
        )

    with d2:
        end_year = st.selectbox(
            "End Year",
            years,
            index=len(years) - 1,
            key="fbi_quilt_end_year"
        )

    if start_year > end_year:
        st.error("Start Year must be before or equal to End Year.")
        return

    quilt_df = build_quilt(annual_df, start_year=start_year, end_year=end_year)

    if quilt_df.empty:
        st.warning("Not enough data in this year range to build a quilt.")
        return

    if end_year == years[-1] and pd.Timestamp.today().month != 12:
        st.caption(
            f"{end_year} is a partial year — return shown is year-to-date "
            f"as of the latest available data."
        )

    color_map = build_quilt_color_map(selected)

    matched_preset = next(
        (p for p in QUILT_PRESETS if set(p["indices"]) == set(selected)),
        None
    )
    title_prefix = matched_preset["label"] if matched_preset else "Asset Allocation Quilt"

    fig = make_quilt_chart(
        quilt_df,
        color_map,
        title=f"{title_prefix} ({start_year}\u2013{end_year})"
    )
    show_figure(fig)
    plt.close(fig)

    with st.expander("View underlying annual returns table"):
        st.dataframe(
            annual_df.loc[start_year:end_year].style.format("{:.2f}"),
            use_container_width=True
        )
