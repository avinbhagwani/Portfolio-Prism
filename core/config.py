"""
Static configuration for PRISM: factor models, labels, rolling windows,
and chart colour schemes. No Streamlit calls and no data fetching here —
just constants and a lookup helper, so other modules can import this
freely without side effects.
"""

MODEL_CONFIG = {
    # EQUITY
    "CAPM": {
        "key": "capm",
        "asset_class": "Equity",
        "dataset": "ff4",
        "factors": ["MKT_RF"]
    },
    "Fama-French 3 Factor Model": {
        "key": "ff3",
        "asset_class": "Equity",
        "dataset": "ff4",
        "factors": ["MKT_RF", "SMB", "HML"]
    },
    "Fama-French 3 Factor Model + Momentum": {
        "key": "ff4",
        "asset_class": "Equity",
        "dataset": "ff4",
        "factors": ["MKT_RF", "SMB", "HML", "WML"]
    },
    "Fama-French 5 Factor Model": {
        "key": "ff5",
        "asset_class": "Equity",
        "dataset": "ff6",
        "factors": ["MKT_RF", "SMB", "HML", "RMW", "CMA"]
    },
    "Fama-French 5 Factor Model + Momentum": {
        "key": "ff6",
        "asset_class": "Equity",
        "dataset": "ff6",
        "factors": ["MKT_RF", "SMB", "HML", "RMW", "CMA", "WML"]
    },

    # FIXED INCOME
    "Fixed Income: Term + Credit Model": {
        "key": "fi2",
        "asset_class": "Fixed Income",
        "dataset": "fi_factors",
        "factors": ["TERM_IN", "CREDIT_IN"]
    }
}

FACTOR_LABELS = {
    "const": "Alpha",
    "MKT_RF": "Market",
    "SMB": "Size",
    "HML": "Value",
    "RMW": "Profitability",
    "CMA": "Investment",
    "WML": "Momentum",
    "TERM_IN": "Term",
    "CREDIT_IN": "Credit"
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


def get_model_config(model_key):
    for config in MODEL_CONFIG.values():
        if config["key"] == model_key:
            return config
    raise ValueError(f"Unknown model key: {model_key}")
