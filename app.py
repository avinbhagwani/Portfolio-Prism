import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import statsmodels.api as sm
import streamlit as st
from indiafactorlibrary import IndiaFactorLibrary

st.set_page_config(
    page_title="Factor Analysis",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# CONFIGURATION
# =========================================================

MODEL_CONFIG = {
    "CAPM": {
        "key": "capm",
        "factors": ["MKT_RF"]
    },
    "Fama-French 3 Factor Model": {
        "key": "ff3",
        "factors": ["MKT_RF", "SMB", "HML"]
    },
    "Fama-French 3 Factor Model + Momentum": {
        "key": "ff4",
        "factors": ["MKT_RF", "SMB", "HML", "WML"]
    },
    "Fama-French 5 Factor Model": {
        "key": "ff5",
        "factors": ["MKT_RF", "SMB", "HML", "RMW", "CMA"]
    },
    "Fama-French 5 Factor Model + Momentum": {
        "key": "ff6",
        "factors": ["MKT_RF", "SMB", "HML", "RMW", "CMA", "WML"]
    }
}

FACTOR_LABELS = {
    "const": "Alpha",
    "MKT_RF": "Market",
    "SMB": "Size",
    "HML": "Value",
    "RMW": "Profitability",
    "CMA": "Investment",
    "WML": "Momentum"
}

ROLLING_WINDOWS = {
    "No Rolling Regression": None,
    "1 Year Rolling": 12,
    "2 Year Rolling": 24,
    "3 Year Rolling": 36,
    "5 Year Rolling": 60,
    "7 Year Rolling": 84,
    "10 Year Rolling": 120
}

# Windows offered inside the Rolling Regression tab (no "No Rolling" option
# needed there since the tab's whole purpose is to show rolling regression).
ROLLING_TAB_WINDOWS = {
    k: v for k, v in ROLLING_WINDOWS.items() if v is not None
}

# Significance colour scheme used throughout rolling regression charts
SIG_COLORS = {
    "high": "#2ca02c",      # green  -> p < 0.01  (three stars)
    "moderate": "#1f77b4",  # blue   -> p < 0.05  (two stars)
    "none": "#d62728",      # red    -> not significant
}


# =========================================================
# MODEL LOOKUP HELPER
# =========================================================

def get_model_config(model_key):
    for config in MODEL_CONFIG.values():
        if config["key"] == model_key:
            return config
    raise ValueError(f"Unknown model key: {model_key}")


# =========================================================
# HELPERS
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def search_funds(term):
    if not term or len(term.strip()) < 3:
        return []

    try:
        response = requests.get(
            "https://api.mfapi.in/mf/search",
            params={"q": term.strip()},
            timeout=15
        )
        response.raise_for_status()
        matches = response.json()

        return [
            {
                "name": x["schemeName"],
                "code": str(x["schemeCode"])
            }
            for x in matches
        ]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fund_history(scheme_code):
    if not scheme_code:
        return pd.DataFrame()

    try:
        response = requests.get(
            f"https://api.mfapi.in/mf/{scheme_code}",
            timeout=30
        )
        response.raise_for_status()
        payload = response.json()

        df = pd.DataFrame(payload.get("data", []))

        if df.empty:
            return pd.DataFrame()

        df["date"] = pd.to_datetime(
            df["date"],
            format="%d-%m-%Y",
            errors="coerce"
        )
        df["nav"] = pd.to_numeric(
            df["nav"],
            errors="coerce"
        )

        df = (
            df.dropna(subset=["date", "nav"])
              .sort_values("date")
              .reset_index(drop=True)
        )

        return df

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_factor_data(model_key):
    try:
        ifl = IndiaFactorLibrary()

        if model_key in ["capm", "ff3", "ff4"]:
            data = ifl.read("ff4")
        else:
            data = ifl.read("ff6")

        factors = data[0].copy()
        factors.index = pd.to_datetime(factors.index)

        if "SMB5" in factors.columns and "SMB" not in factors.columns:
            factors.rename(columns={"SMB5": "SMB"}, inplace=True)

        return factors

    except Exception as e:
        st.error(f"Factor data error: {e}")
        return pd.DataFrame()


def month_end_dates(df):
    if df.empty:
        return []

    dates = pd.to_datetime(df["date"])
    dates = dates[dates.dt.is_month_end]

    return sorted(pd.to_datetime(dates.unique()))


def get_common_month_end_dates(codes):
    if not codes:
        return []

    common = None

    for code in codes:
        df = fetch_fund_history(code)

        if df.empty:
            return []

        dates = set(month_end_dates(df))

        if common is None:
            common = dates
        else:
            common &= dates

    if not common:
        return []

    return sorted(pd.to_datetime(list(common)))


def get_monthly_returns(code, start_date, end_date):
    df = fetch_fund_history(code)

    if df.empty:
        return pd.Series(dtype=float)

    df = df.set_index("date").sort_index()

    monthly_nav = (
        df["nav"]
        .resample("ME")
        .last()
        .dropna()
    )

    monthly_nav = monthly_nav[
        (monthly_nav.index >= pd.Timestamp(start_date)) &
        (monthly_nav.index <= pd.Timestamp(end_date))
    ]

    returns = monthly_nav.pct_change().dropna() * 100
    returns.name = code

    return returns


def significance_stars(p):
    if pd.isna(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def significance_text(p):
    if pd.isna(p):
        return "N/A"
    if p < 0.01:
        return "Significant at 1%"
    if p < 0.05:
        return "Significant at 5%"
    if p < 0.10:
        return "Significant at 10%"
    return "Not Significant"


def classify_significance(p):
    """Bucket a p-value into the rolling-regression colour scheme."""
    if pd.isna(p):
        return "none"
    if p < 0.01:
        return "high"       # three stars -> green
    if p < 0.05:
        return "moderate"   # two stars -> blue
    return "none"


def prepare_regression_data(return_series, model_key):
    factors = load_factor_data(model_key)

    if factors.empty:
        return None

    factors.index = (
        pd.to_datetime(factors.index)
        .to_period("M")
        .to_timestamp("M")
    )

    return_series = return_series.copy()
    return_series.index = (
        pd.to_datetime(return_series.index)
        .to_period("M")
        .to_timestamp("M")
    )

    df = (
        return_series
        .to_frame("Fund_Return")
        .join(factors, how="inner")
    )

    if df.empty:
        return None

    df["Excess_Fund_Return"] = df["Fund_Return"] - df["RF"]
    df["MKT_RF"] = df["MKT"] - df["RF"]

    factor_columns = get_model_config(model_key)["factors"]

    missing = [x for x in factor_columns if x not in df.columns]

    if missing:
        st.error(f"Missing factors: {missing}")
        st.write("Available columns:", list(df.columns))
        return None

    return df.dropna().sort_index()


def make_factor_chart(model, factor_columns, title):
    values = [model.params[x] for x in factor_columns]
    pvalues = [model.pvalues[x] for x in factor_columns]
    labels = [FACTOR_LABELS.get(x, x) for x in factor_columns]

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(range(len(values)), values)

    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Coefficient")
    ax.set_title(title, fontsize=18, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.4)

    max_abs = max([abs(x) for x in values] + [1])

    for bar, value, p in zip(bars, values, pvalues):
        stars = significance_stars(p)
        sig = significance_text(p)

        if value >= 0:
            number_y = value + max_abs * 0.025
            sig_y = value + max_abs * 0.085
            number_va = "bottom"
            sig_va = "bottom"
        else:
            number_y = value - max_abs * 0.025
            sig_y = value - max_abs * 0.085
            number_va = "top"
            sig_va = "top"

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            number_y,
            f"{value:.3f}",
            ha="center",
            va=number_va,
            fontsize=11,
            fontweight="bold"
        )

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            sig_y,
            f"{stars}  {sig}",
            ha="center",
            va=sig_va,
            fontsize=9
        )

    ymin, ymax = ax.get_ylim()
    padding = max_abs * 0.25
    ax.set_ylim(ymin - padding, ymax + padding)

    fig.tight_layout()
    return fig


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

    st.pyplot(fig)
    plt.close(fig)

    st.markdown("#### Interpretation")
    st.markdown(
        """
Think of PRISM as a lens that separates a fund's return into its
underlying building blocks. Each coefficient shows how strongly the
fund is tilted toward a particular investment style or characteristic.
Together, these factor exposures create a PRISM of the portfolio,
revealing what is really driving its performance beyond what may be
visible on the surface.

- **const (Alpha):** The return that remains unexplained after
  accounting for the fund's exposure to the known factors. This is
  often interpreted as the potential value added by the manager's
  investment decisions.
- **MF (Market):** Measures the fund's sensitivity to overall market
  movements — essentially, its exposure to systematic market risk.
- **SMB (Size):** Shows the fund's tilt toward small-cap versus
  large-cap stocks. A positive loading indicates greater exposure to
  smaller companies.
- **HML (Value):** Captures the fund's value versus growth tilt. A
  positive loading suggests greater exposure to value stocks —
  companies with relatively high book-to-price ratios.
- **RMW (Profitability):** Measures exposure to more profitable
  companies versus less profitable companies. A positive loading
  indicates a preference for stronger profitability.
- **CMA (Investment):** Captures the fund's tilt toward companies
  with conservative versus aggressive investment policies. A positive
  loading indicates greater exposure to firms with lower asset growth.
- **WML (Momentum):** Measures exposure to recent winners versus
  recent losers. A positive loading indicates a stronger momentum
  orientation.
        """
    )

    st.caption(
        "This tool uses monthly long-short factor returns developed by "
        "[Rajan Raju](https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=3354364). "
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


def make_rolling_chart(rolling_df, factor, p_column, title, rolling_months):
    """
    Build a single rolling-regression chart for one factor (or Alpha).

    Colour scheme:
      - red line/points   : not significant
      - blue dots + line  : significant at 5% (two stars, p < 0.05)
      - green dots + line : significant at 1% (three stars, p < 0.01)

    Consecutive points that share the same significance bucket are
    connected with a coloured line segment (not just isolated dots),
    so runs of significance read clearly on the chart.
    """
    beta = rolling_df[factor].astype(float)
    pvalues = rolling_df[p_column].astype(float)
    dates = beta.index

    buckets = [classify_significance(p) for p in pvalues]

    fig, ax = plt.subplots(figsize=(7.5, 5))

    # Base line (context / not-significant backbone)
    ax.plot(
        dates,
        beta.values,
        linewidth=1.2,
        color=SIG_COLORS["none"],
        alpha=0.6,
        zorder=1
    )

    # Coloured connecting segments between consecutive same-bucket points
    for i in range(len(dates) - 1):
        b1, b2 = buckets[i], buckets[i + 1]
        if b1 == b2 and b1 in ("high", "moderate"):
            ax.plot(
                dates[i:i + 2],
                beta.values[i:i + 2],
                linewidth=2.4,
                color=SIG_COLORS[b1],
                zorder=4
            )

    # Coloured dots on top
    for bucket in ("moderate", "high"):
        mask = pd.Series(
            [b == bucket for b in buckets],
            index=dates
        )
        if mask.any():
            ax.scatter(
                dates[mask],
                beta[mask],
                color=SIG_COLORS[bucket],
                s=22,
                zorder=5
            )

    ax.axhline(0, color="black", linestyle="--", linewidth=1)

    if rolling_months % 12 == 0:
        window_text = f"{rolling_months // 12} Year"
    else:
        window_text = f"{rolling_months} Months"

    ax.set_title(
        f"{title} — {window_text} Rolling",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Coefficient")
    ax.grid(axis="y", linestyle=":", alpha=0.35)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_elements = [
        Line2D([0], [0], color=SIG_COLORS["none"], lw=2, label="Not Significant"),
        Line2D([0], [0], color=SIG_COLORS["moderate"], lw=2, marker="o",
               label="Significant (p < 0.05)"),
        Line2D([0], [0], color=SIG_COLORS["high"], lw=2, marker="o",
               label="Significant (p < 0.01)"),
    ]
    ax.legend(handles=legend_elements, frameon=False, fontsize=8)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


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
                st.pyplot(fig)

            plt.close(fig)

    st.write("Rolling Regression Results")
    st.dataframe(
        rolling_df.round(4),
        use_container_width=True
    )

    return rolling_df


# =========================================================
# PRISM NAVIGATION
# =========================================================

st.sidebar.title("PRISM")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "Factor Analysis",
        "Drawdown Analysis (Coming Soon)",
        "Efficient Frontier (Coming Soon)"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Have a question, found a bug, or want to suggest a feature? "
    "Reach out anytime — "
    "[connect on LinkedIn](https://www.linkedin.com/in/avinbhagwani69/) "
    "or drop me a line at avinbhagwani69@gmail.com."
)


def render_coming_soon(title):
    st.title(title)
    st.divider()

    st.markdown(
        """
        <div style="text-align:center; padding-top:120px;">
            <h1 style="font-size:48px;">Coming Soon</h1>
            <p style="font-size:20px; color:#777;">
                This section is currently under development.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if page == "Drawdown Analysis (Coming Soon)":
    render_coming_soon("Drawdown Analysis")

elif page == "Efficient Frontier (Coming Soon)":
    render_coming_soon("Efficient Frontier")

else:
    # =========================================================
    # UI
    # =========================================================

    st.title("📊 Factor Analysis")
    st.caption(
        "CAPM / Fama-French factor analysis for individual funds "
        "and custom portfolios."
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

    model_name = st.selectbox(
        "Factor Model",
        list(MODEL_CONFIG.keys()),
        index=4
    )

    model_key = MODEL_CONFIG[model_name]["key"]

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

                            fig.autofmt_xdate()
                            fig.tight_layout()

                            st.pyplot(fig)
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
                                color="black",
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

                            fig.autofmt_xdate()
                            fig.tight_layout()

                            st.pyplot(fig)
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
