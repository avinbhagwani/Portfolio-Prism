"""
Calculation helpers for factor regressions: significance labelling and
aligning fund returns with factor data. significance_stars/text and
classify_significance are pure (safe to unit test or reuse from the
Factor Indexes tool). prepare_regression_data surfaces st.error messages
for missing data, same as the original app, since that's user-facing
validation rather than pure calculation.
"""

import pandas as pd
import statsmodels.api as sm
import streamlit as st

from core.config import get_model_config
from core.data import load_factor_data


def newey_west_lags(n_obs):
    """
    Newey-West (1994) rule-of-thumb lag length: floor(4 * (T/100)^(2/9)).
    Gives 2 lags for a 12-month window, 3 for 36 months, 4 for 120.
    """
    return max(1, int(4 * (n_obs / 100) ** (2 / 9)))


def fit_factor_model(y, X):
    """
    OLS with Newey-West (HAC) standard errors.

    Coefficients are identical to plain OLS; only the standard errors,
    t-stats and p-values change. Monthly fund returns are typically
    autocorrelated and heteroskedastic, which makes plain OLS standard
    errors too small and the significance stars too generous. HAC
    errors are the standard choice for factor regressions.
    """
    return sm.OLS(y, X).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": newey_west_lags(len(y))}
    )


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
    """
    Prepare aligned monthly fund returns and factor returns.

    Equity models regress excess fund returns on equity factors.
    Fixed income models regress fund total returns on TERM_IN and CREDIT_IN.
    """
    config = get_model_config(model_key)
    factors = load_factor_data(model_key)

    if factors.empty:
        return None

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

    # EQUITY: convert fund and market returns into excess returns
    if config["asset_class"] == "Equity":
        if "RF" not in df.columns:
            st.error("Risk-free rate (RF) missing from equity factor data.")
            return None

        if "MKT" not in df.columns:
            st.error("Market return (MKT) missing from equity factor data.")
            return None

        df["Excess_Fund_Return"] = (
            df["Fund_Return"] - df["RF"]
        )

        df["MKT_RF"] = (
            df["MKT"] - df["RF"]
        )

    # FIXED INCOME: TERM_IN and CREDIT_IN are already return proxies
    else:
        df["Excess_Fund_Return"] = df["Fund_Return"]

    factor_columns = config["factors"]

    missing = [
        x for x in factor_columns
        if x not in df.columns
    ]

    if missing:
        st.error(f"Missing factors: {missing}")
        st.write("Available columns:", list(df.columns))
        return None

    return df.dropna().sort_index()
