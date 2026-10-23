"""
All external data access lives here: mfapi.in fund search/history and
IndiaFactorLibrary factor data. Successful responses are cached with
st.cache_data; failures are not, so a momentary outage clears on retry.
"""

import requests
import pandas as pd
import streamlit as st
from indiafactorlibrary import IndiaFactorLibrary

from core.config import get_model_config


# Failures are never cached: each loader below raises inside the cached
# function (st.cache_data doesn't store exceptions) and the public wrapper
# turns the error into an empty result. Before, a single failed request was
# cached as "no results" for an hour, so one blip from mfapi.in left fund
# search showing "No funds found" until the cache expired.

@st.cache_data(ttl=3600, show_spinner=False)
def _search_funds(term):
    response = requests.get(
        "https://api.mfapi.in/mf/search",
        params={"q": term},
        timeout=15
    )
    response.raise_for_status()
    return [
        {"name": x["schemeName"], "code": str(x["schemeCode"])}
        for x in response.json()
    ]


def search_funds(term):
    if not term or len(term.strip()) < 3:
        return []
    try:
        return _search_funds(term.strip())
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_fund_history(scheme_code):
    response = requests.get(
        f"https://api.mfapi.in/mf/{scheme_code}",
        timeout=30
    )
    response.raise_for_status()
    df = pd.DataFrame(response.json().get("data", []))
    if df.empty:
        raise ValueError(f"No NAV history returned for {scheme_code}")
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    # mfapi occasionally repeats a date; keep one NAV per day
    df = df[df["nav"] > 0].drop_duplicates("date", keep="last")
    return df.sort_values("date").reset_index(drop=True)


def fetch_fund_history(scheme_code):
    if not scheme_code:
        return pd.DataFrame()
    try:
        return _fetch_fund_history(scheme_code)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def _load_factor_data(model_key):
    config = get_model_config(model_key)
    data = IndiaFactorLibrary().read(config["dataset"])
    factors = data[0].copy()
    factors.index = pd.to_datetime(factors.index).to_period("M").to_timestamp("M")
    # Normalise equity naming
    if "SMB5" in factors.columns and "SMB" not in factors.columns:
        factors.rename(columns={"SMB5": "SMB"}, inplace=True)
    # Normalise fixed-income naming defensively
    factors.rename(columns={
        "TERM": "TERM_IN", "Term": "TERM_IN", "term": "TERM_IN",
        "CREDIT": "CREDIT_IN", "Credit": "CREDIT_IN", "credit": "CREDIT_IN",
    }, inplace=True)
    return factors.sort_index()


def load_factor_data(model_key):
    """
    Load factor data for either equity or fixed income models.

    Equity:
        ff4 / ff6 from IndiaFactorLibrary

    Fixed Income:
        fi_factors containing TERM_IN and CREDIT_IN.

    The fixed income factors are monthly benchmark-exposure proxies
    constructed for Indian fixed income markets.
    """
    try:
        return _load_factor_data(model_key)
    except Exception as e:
        st.error(f"Couldn't load the factor data right now ({type(e).__name__}). "
                 "Please try again in a minute.")
        if model_key == "fi2":
            st.info(
                "The Fixed Income model requires IndiaFactorLibrary data symbol "
                "'fi_factors'. Update indiafactorlibrary to the latest version "
                "if this dataset is unavailable."
            )
        return pd.DataFrame()


def month_end_dates(df):
    """
    One calendar month-end date for every month the fund has NAV data.

    NAVs are only published on business days, so the literal last day
    of the month (e.g. a Saturday or Sunday) often has no NAV. Checking
    for the exact calendar month-end used to silently drop those months
    from the date pickers. Instead, every month with at least one NAV is
    kept, labelled by its calendar month-end — which is exactly how
    get_monthly_returns() buckets returns via resample("ME").last().

    The latest month is dropped if it isn't complete yet (the last NAV
    is before that month's last business day), so a partial month is
    never offered as an end date.
    """
    if df.empty:
        return []

    dates = pd.to_datetime(df["date"]).dropna()

    if dates.empty:
        return []

    month_ends = sorted(
        pd.Timestamp(p.end_time.normalize())
        for p in dates.dt.to_period("M").unique()
    )

    last_date = dates.max().normalize()
    last_business_day = pd.offsets.BMonthEnd().rollforward(last_date)

    if last_date < last_business_day:
        month_ends = month_ends[:-1]

    return month_ends


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
