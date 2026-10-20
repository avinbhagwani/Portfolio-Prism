"""
Orchestration layer: runs the actual OLS regressions (single-period and
rolling) and renders the results — metrics, tables, charts, interpretation
text. This is intentionally where Streamlit rendering and calculation mix,
since factor analysis in this app is "compute and immediately display" —
splitting rendering out further would add indirection without much benefit.
Pure calculation lives in core/regression_stats.py; chart drawing lives in
charts/.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import streamlit as st
import matplotlib.pyplot as plt

from core.config import FACTOR_LABELS, get_model_config
from core.regression_stats import (
    prepare_regression_data,
    significance_stars,
    significance_text,
)
from charts.factor_chart import make_factor_chart
from charts.rolling_chart import make_rolling_chart
from charts.render import show_figure


def run_factor_analysis(return_series, model_key, analysis_name):
    regression_df = prepare_regression_data(
        return_series,
        model_key
    )

    if regression_df is None or regression_df.empty:
        st.warning("No overlapping return/factor observations.")
        return None

    factor_columns = get_model_config(model_key)["factors"]

    X = sm.add_constant(
        regression_df[factor_columns],
        has_constant="add"
    )
    y = regression_df["Excess_Fund_Return"]

    model = sm.OLS(y, X).fit()

    st.subheader(f"{analysis_name} — Factor Analysis")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Observations", len(regression_df))
    c2.metric("R-squared", f"{model.rsquared:.2%}")
    c3.metric("Adjusted R²", f"{model.rsquared_adj:.2%}")

    alpha = model.params["const"]
    alpha_p = model.pvalues["const"]

    c4.metric(
        "Monthly Alpha",
        f"{alpha:.3f}% {significance_stars(alpha_p)}"
    )

    st.caption(
        f"Alpha significance: {significance_text(alpha_p)} "
        f"(p = {alpha_p:.4f})"
    )

    # Include Alpha (the regression constant) alongside the factors so it
    # shows up in the exposure table and chart, not just the metric card.
    display_columns = ["const"] + factor_columns

    rows = []

    for factor in display_columns:
        p = model.pvalues[factor]

        rows.append({
            "Factor": FACTOR_LABELS.get(factor, factor),
            "Coefficient": model.params[factor],
            "t-stat": model.tvalues[factor],
            "P-value": p,
            "Significance": significance_stars(p),
            "Significance Level": significance_text(p)
        })

    exposure_df = pd.DataFrame(rows)

    st.dataframe(
        exposure_df.style.format({
            "Coefficient": "{:.4f}",
            "t-stat": "{:.4f}",
            "P-value": "{:.4f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    fig = make_factor_chart(
        model,
        display_columns,
        f"{analysis_name} — Factor Exposures"
    )

    show_figure(fig)
    plt.close(fig)

    st.markdown("#### Interpretation")

    config = get_model_config(model_key)

    if config["asset_class"] == "Equity":
        st.markdown(
            """
Think of PRISM as a lens that separates a fund's return into its
underlying building blocks. Each coefficient shows how strongly the
fund is tilted toward a particular investment style or characteristic.

- **Alpha:** The return unexplained after accounting for known factors.
- **Market:** Sensitivity to overall equity market movements.
- **Size:** Tilt toward small-cap versus large-cap stocks.
- **Value:** Tilt toward value versus growth stocks.
- **Profitability:** Exposure to more versus less profitable companies.
- **Investment:** Exposure to conservative versus aggressive investment firms.
- **Momentum:** Exposure to recent winners versus recent losers.
            """
        )
    else:
        st.markdown(
            """
Think of the Fixed Income model as separating a debt fund's return into
its two major systematic risk drivers:

- **Alpha:** The portion of return not explained by systematic Term and
  Credit exposures.

- **Term:** Sensitivity to interest-rate movements and duration risk.
  A higher positive loading generally indicates stronger exposure to
  longer-duration government-bond movements.

- **Credit:** Sensitivity to movements in AAA corporate credit spreads.
  A higher positive loading indicates greater exposure to corporate
  spread risk.
            """
        )

    st.caption(
        "This tool uses Indian equity factors and fixed-income factor proxies "
        "developed for the Indian market. Equity factor data is sourced through "
        "the IndiaFactorLibrary; the Fixed Income model uses TERM_IN and CREDIT_IN "
        "benchmark-exposure proxies. "
        "This dataset can be freely accessed at "
        "[invespar.com/research](https://invespar.com/research). "
        "The construction methodology behind the Invespar Indian Factor "
        "Library has been described below: Raju, Rajan, Four and "
        "Five-Factor Models in the Indian Equities Market (March 10, 2022). "
        "Available at SSRN: https://ssrn.com/abstract=4054146"
    )

    return {
        "model": model,
        "regression_df": regression_df
    }


def run_rolling_regression(
    regression_df,
    factor_columns,
    rolling_months,
    analysis_name
):
    required = ["Excess_Fund_Return"] + factor_columns

    data = (
        regression_df[required]
        .dropna()
        .sort_index()
    )

    if len(data) < rolling_months:
        st.warning(
            f"Not enough observations for {rolling_months}-month "
            f"rolling regression. Available: {len(data)}."
        )
        return None

    results = []

    for i in range(rolling_months - 1, len(data)):
        window = data.iloc[
            i - rolling_months + 1:i + 1
        ]

        X = sm.add_constant(
            window[factor_columns],
            has_constant="add"
        )
        y = window["Excess_Fund_Return"]

        try:
            model = sm.OLS(y, X).fit()
        except Exception:
            continue

        row = {
            "Date": data.index[i],
            "Alpha": model.params.get("const", np.nan),
            "Alpha_P": model.pvalues.get("const", np.nan)
        }

        for factor in factor_columns:
            row[factor] = model.params.get(factor, np.nan)
            row[f"{factor}_P"] = model.pvalues.get(
                factor,
                np.nan
            )

        results.append(row)

    rolling_df = pd.DataFrame(results)

    if rolling_df.empty:
        return None

    rolling_df = rolling_df.set_index("Date")

    st.subheader(
        f"{analysis_name} — Rolling Regression"
    )

    # Two charts per row to save space
    plot_items = ["Alpha"] + factor_columns

    for i in range(0, len(plot_items), 2):
        pair = plot_items[i:i + 2]
        cols = st.columns(2)

        for col, factor in zip(cols, pair):
            p_column = (
                "Alpha_P"
                if factor == "Alpha"
                else f"{factor}_P"
            )

            title = (
                "Alpha"
                if factor == "Alpha"
                else FACTOR_LABELS.get(factor, factor)
            )

            fig = make_rolling_chart(
                rolling_df,
                factor,
                p_column,
                title,
                rolling_months
            )

            with col:
                show_figure(fig)

            plt.close(fig)

    st.write("Rolling Regression Results")
    st.dataframe(
        rolling_df.round(4),
        use_container_width=True
    )

    return rolling_df
