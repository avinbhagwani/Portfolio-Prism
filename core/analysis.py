"""
Factor regressions for the Factor Analysis page: one full-period fit and
rolling fits. Pure calculation (the page decides how to show it), apart
from the validation messages prepare_regression_data raises for missing
data. Standard errors are Newey-West (HAC) throughout.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import streamlit as st

from core.config import get_model_config
from core.regression_stats import fit_factor_model, newey_west_lags, prepare_regression_data


def fit(return_series, model_key):
    """Full-period regression. Returns dict(model, data, factors, lags) or None."""
    data = prepare_regression_data(return_series, model_key)
    if data is None or data.empty:
        return None
    factors = get_model_config(model_key)["factors"]
    if len(data) < len(factors) + 6:
        return None
    X = sm.add_constant(data[factors], has_constant="add")
    model = fit_factor_model(data["Excess_Fund_Return"], X)
    return {"model": model, "data": data, "factors": factors, "lags": newey_west_lags(len(data))}


@st.cache_data(max_entries=200, ttl=6 * 3600, show_spinner=False)
def rolling(data, factors, months):
    """One HAC regression per rolling window of `months`; coefficient,
    p-value and standard error for alpha and every factor."""
    factors = list(factors)
    data = data[["Excess_Fund_Return"] + factors].dropna().sort_index()
    out = []
    for i in range(months - 1, len(data)):
        w = data.iloc[i - months + 1:i + 1]
        X = sm.add_constant(w[factors], has_constant="add")
        try:
            m = fit_factor_model(w["Excess_Fund_Return"], X)
        except Exception:
            continue
        row = {"Date": data.index[i]}
        for name, key in [("Alpha", "const")] + [(f, f) for f in factors]:
            row[name] = m.params.get(key, np.nan)
            row[f"{name}_P"] = m.pvalues.get(key, np.nan)
            row[f"{name}_SE"] = m.bse.get(key, np.nan)
        out.append(row)
    return pd.DataFrame(out).set_index("Date") if out else None
