"""
The original PRISM tool: individual fund or portfolio factor analysis,
with rolling regression. This is the existing app.py UI moved into a
single render function so app.py can route to it. Logic is unchanged —
only the imports and the wrapping function are new.
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from core.config import MODEL_CONFIG, ROLLING_TAB_WINDOWS, get_model_config
from core.data import (
    search_funds,
    fetch_fund_history,
    month_end_dates,
    get_common_month_end_dates,
    get_monthly_returns,
)
from core.analysis import run_factor_analysis, run_rolling_regression
from charts.theme import apply_chart_theme
from charts.render import show_figure


def render():
    st.title("📊 Factor Analysis")
    st.caption(
        "Decompose Indian mutual fund returns into systematic equity or "
        "fixed-income factor exposures."
    )

    analysis_type = st.radio(
        "Analysis Type",
        ["Individual Fund", "Portfolio of Funds"],
        horizontal=True
    )

    st.divider()

    # =========================================================
    # COMMON ANALYSIS SETTINGS
    # =========================================================

    # All models are available in one dropdown, including Fixed Income.
    # This keeps the original PRISM user experience unchanged.
    model_names = list(MODEL_CONFIG.keys())

    model_name = st.selectbox(
        "Factor Model",
        model_names,
        index=model_names.index(
            "Fama-French 5 Factor Model + Momentum"
        )
    )

    model_key = MODEL_CONFIG[model_name]["key"]

    if MODEL_CONFIG[model_name]["asset_class"] == "Fixed Income":
        st.info(
            "**Fixed Income Model:** Fund returns are decomposed into "
            "**Term risk** (interest-rate / duration exposure) and "
            "**Credit risk** (AAA corporate spread exposure)."
        )

    rolling_tab_options = list(ROLLING_TAB_WINDOWS.keys())
    default_rolling_index = rolling_tab_options.index("3 Year Rolling")

    # =========================================================
    # INDIVIDUAL FUND
    # =========================================================

    if analysis_type == "Individual Fund":

        st.subheader("Fund Selection")

        search_term = st.text_input(
            "Search Fund",
            placeholder="Type at least 3 letters of a fund name..."
        )

        matches = search_funds(search_term)

        if search_term and len(search_term) >= 3:

            if not matches:
                st.warning("No funds found.")

            else:

                options = {
                    f"{x['name']} (Code: {x['code']})": x["code"]
                    for x in matches
                }

                selected_label = st.selectbox(
                    "Select Fund",
                    list(options.keys())
                )

                selected_code = options[selected_label]

                fund_df = fetch_fund_history(selected_code)

                available_dates = month_end_dates(fund_df)

                if available_dates:

                    d1, d2 = st.columns(2)

                    with d1:
                        start_date = st.selectbox(
                            "Start Date",
                            available_dates,
                            format_func=lambda x: x.strftime("%b %Y"),
                            index=0
                        )

                    with d2:
                        end_date = st.selectbox(
                            "End Date",
                            available_dates,
                            format_func=lambda x: x.strftime("%b %Y"),
                            index=len(available_dates) - 1
                        )

                    if start_date >= end_date:

                        st.error(
                            "Start Date must be before End Date."
                        )

                    else:

                        if "individual_analysis_run" not in st.session_state:
                            st.session_state.individual_analysis_run = False

                        run_button = st.button(
                            "Run Analysis",
                            type="primary",
                            key="individual_run_btn"
                        )

                        if run_button:
                            st.session_state.individual_analysis_run = True

                        # Tab selection sits below fund selection
                        if st.session_state.individual_analysis_run:

                            filtered = fund_df[
                                (fund_df["date"] >= start_date) &
                                (fund_df["date"] <= end_date)
                            ]

                            st.subheader("NAV Performance")

                            fig, ax = plt.subplots(figsize=(12, 4))

                            ax.plot(
                                filtered["date"],
                                filtered["nav"],
                                linewidth=2
                            )

                            ax.set_xlabel("Date")
                            ax.set_ylabel("NAV")
                            ax.set_title(
                                "NAV Performance",
                                fontsize=17,
                                fontweight="bold"
                            )
                            ax.grid(
                                axis="y",
                                linestyle=":",
                                alpha=0.4
                            )

                            apply_chart_theme(fig, ax)

                            fig.autofmt_xdate()
                            fig.tight_layout()

                            show_figure(fig)
                            plt.close(fig)

                            monthly_returns = get_monthly_returns(
                                selected_code,
                                start_date,
                                end_date
                            )

                            tab1, tab2 = st.tabs(
                                ["Factor Analysis", "Rolling Regression"]
                            )

                            with tab1:
                                result = run_factor_analysis(
                                    monthly_returns,
                                    model_key,
                                    "Individual Fund"
                                )

                            with tab2:
                                if result:
                                    rolling_choice = st.selectbox(
                                        "Rolling Window",
                                        rolling_tab_options,
                                        index=default_rolling_index,
                                        key="individual_rolling_window"
                                    )

                                    rolling_months = ROLLING_TAB_WINDOWS[
                                        rolling_choice
                                    ]

                                    run_rolling_regression(
                                        result["regression_df"],
                                        get_model_config(model_key)["factors"],
                                        rolling_months,
                                        "Individual Fund"
                                    )
                                else:
                                    st.info(
                                        "No factor analysis results available "
                                        "to build a rolling regression."
                                    )

                else:
                    st.warning("No month-end NAV dates available.")

    # =========================================================
    # PORTFOLIO
    # =========================================================

    else:

        st.subheader("Portfolio Construction")

        st.info(
            "Select up to 10 funds. Portfolio weights must total exactly 100%. "
            "The portfolio regression is run on the calculated portfolio return series."
        )

        selected_portfolio = []

        for i in range(10):

            st.markdown(f"**Fund {i + 1}**")

            c1, c2, c3 = st.columns([2, 5, 1])

            with c1:

                search = st.text_input(
                    f"Search {i + 1}",
                    key=f"search_{i}",
                    placeholder="Search fund..."
                )

            matches = search_funds(search)

            with c2:

                if matches:

                    options = {
                        f"{x['name']} (Code: {x['code']})": x["code"]
                        for x in matches
                    }

                    labels = ["No fund"] + list(options.keys())

                    selected_label = st.selectbox(
                        f"Select Fund {i + 1}",
                        labels,
                        key=f"fund_{i}"
                    )

                    code = (
                        None
                        if selected_label == "No fund"
                        else options[selected_label]
                    )

                else:

                    code = None

            with c3:

                weight = st.number_input(
                    "Weight %",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.5,
                    key=f"weight_{i}"
                )

            if code and weight > 0:

                selected_portfolio.append(
                    {
                        "code": code,
                        "weight": weight,
                        "name": selected_label
                    }
                )

        total_weight = sum(
            x["weight"]
            for x in selected_portfolio
        )

        if abs(total_weight - 100) < 0.001:

            st.success(
                f"Total Portfolio Weight: {total_weight:.1f}% ✓"
            )

        else:

            st.error(
                f"Total Portfolio Weight: {total_weight:.1f}% "
                f"— must equal 100%"
            )

        # -----------------------------------------------------
        # COMMON DATES
        # -----------------------------------------------------

        codes = [
            x["code"]
            for x in selected_portfolio
        ]

        if codes:

            common_dates = get_common_month_end_dates(codes)

            if common_dates:

                st.write(
                    f"**Common history:** "
                    f"{common_dates[0].strftime('%b %Y')} "
                    f"to "
                    f"{common_dates[-1].strftime('%b %Y')}"
                )

                d1, d2 = st.columns(2)

                with d1:

                    start_date = st.selectbox(
                        "Start Date",
                        common_dates,
                        format_func=lambda x: x.strftime("%b %Y"),
                        index=0,
                        key="portfolio_start"
                    )

                with d2:

                    end_date = st.selectbox(
                        "End Date",
                        common_dates,
                        format_func=lambda x: x.strftime("%b %Y"),
                        index=len(common_dates) - 1,
                        key="portfolio_end"
                    )

                if "portfolio_analysis_run" not in st.session_state:
                    st.session_state.portfolio_analysis_run = False

                run_portfolio_button = st.button(
                    "Run Portfolio Analysis",
                    type="primary",
                    key="portfolio_run_btn"
                )

                if run_portfolio_button:

                    if abs(total_weight - 100) > 0.001:
                        st.error(
                            "Portfolio weights must total exactly 100%."
                        )
                    elif start_date >= end_date:
                        st.error(
                            "Start Date must be before End Date."
                        )
                    else:
                        st.session_state.portfolio_analysis_run = True

                # Tab selection sits below fund selection
                if st.session_state.portfolio_analysis_run:

                    returns_list = []
                    missing_fund = False

                    for item in selected_portfolio:

                        returns = get_monthly_returns(
                            item["code"],
                            start_date,
                            end_date
                        )

                        if returns.empty:
                            st.error(
                                f"No return data available for "
                                f"{item['name']}."
                            )
                            missing_fund = True
                            break

                        returns_list.append(
                            returns.rename(
                                item["code"]
                            )
                        )

                    if not missing_fund:

                        returns_df = pd.concat(
                            returns_list,
                            axis=1
                        ).dropna()

                        if returns_df.empty:

                            st.error(
                                "No common monthly return observations "
                                "are available."
                            )

                        else:

                            # -----------------------------------------
                            # CALCULATE PORTFOLIO RETURNS
                            # -----------------------------------------

                            weights = {
                                x["code"]: x["weight"] / 100
                                for x in selected_portfolio
                            }

                            portfolio_returns = pd.Series(
                                0.0,
                                index=returns_df.index
                            )

                            for code, weight in weights.items():

                                portfolio_returns += (
                                    returns_df[code]
                                    * weight
                                )

                            portfolio_returns.name = (
                                "Portfolio Return"
                            )

                            # -----------------------------------------
                            # PORTFOLIO SUMMARY
                            # -----------------------------------------

                            st.subheader("Portfolio")

                            portfolio_table = pd.DataFrame([
                                {
                                    "Fund": x["name"],
                                    "Weight": x["weight"]
                                }
                                for x in selected_portfolio
                            ])

                            st.dataframe(
                                portfolio_table.style.format({
                                    "Weight": "{:.1f}%"
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                            # -----------------------------------------
                            # CUMULATIVE RETURN
                            # -----------------------------------------

                            cumulative = (
                                (1 + portfolio_returns / 100)
                                .cumprod()
                                - 1
                            ) * 100

                            fig, ax = plt.subplots(figsize=(12, 5))

                            ax.plot(
                                cumulative.index,
                                cumulative.values,
                                linewidth=2
                            )

                            ax.axhline(
                                0,
                                color="#888888",
                                linestyle="--",
                                linewidth=1
                            )

                            ax.set_title(
                                "Portfolio Cumulative Return",
                                fontsize=18,
                                fontweight="bold"
                            )

                            ax.set_xlabel("Date")
                            ax.set_ylabel("Cumulative Return (%)")

                            ax.grid(
                                axis="y",
                                linestyle=":",
                                alpha=0.4
                            )

                            apply_chart_theme(fig, ax)

                            fig.autofmt_xdate()
                            fig.tight_layout()

                            show_figure(fig)
                            plt.close(fig)

                            # -----------------------------------------
                            # MONTHLY RETURNS
                            # -----------------------------------------

                            with st.expander(
                                "View Portfolio Monthly Returns"
                            ):

                                st.dataframe(
                                    portfolio_returns.to_frame(
                                        "Portfolio Return (%)"
                                    ).round(4),
                                    use_container_width=True
                                )

                            # -----------------------------------------
                            # FACTOR ANALYSIS / ROLLING REGRESSION TABS
                            # -----------------------------------------

                            tab1, tab2 = st.tabs(
                                ["Factor Analysis", "Rolling Regression"]
                            )

                            with tab1:
                                result = run_factor_analysis(
                                    portfolio_returns,
                                    model_key,
                                    "Portfolio"
                                )

                            with tab2:
                                if result:
                                    rolling_choice = st.selectbox(
                                        "Rolling Window",
                                        rolling_tab_options,
                                        index=default_rolling_index,
                                        key="portfolio_rolling_window"
                                    )

                                    rolling_months = ROLLING_TAB_WINDOWS[
                                        rolling_choice
                                    ]

                                    run_rolling_regression(
                                        result["regression_df"],
                                        get_model_config(model_key)["factors"],
                                        rolling_months,
                                        "Portfolio"
                                    )
                                else:
                                    st.info(
                                        "No factor analysis results available "
                                        "to build a rolling regression."
                                    )

            else:

                st.warning(
                    "The selected funds do not have a common "
                    "month-end history."
                )

        else:

            st.caption(
                "Select at least one fund to see the common history."
            )
