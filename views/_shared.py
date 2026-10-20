"""
Shared UI component used by both FBI Intelligence and Drawdown Analysis.

Each index gets its own independent "Category → Index" dropdown pair,
side by side, so the two indices being compared don't have to come
from the same category (e.g. a Strategy index against a Sectoral one).
"""

import streamlit as st

from core.index_data import list_categories, list_indices

NONE_OPTION = "— None —"


def select_single_index(label, key_prefix, default_index=None, allow_none=False):
    """
    One "Category → Index" dropdown pair. If allow_none is True, an
    extra "— None —" choice is offered and None is returned when it's
    picked; otherwise a real index is always returned (used for things
    like a benchmark picker, where "no benchmark" isn't a valid state).
    """
    categories = list_categories()

    default_category = None
    if default_index:
        matches = [
            c for c in categories
            if default_index in list_indices(category=c)
        ]
        if matches:
            default_category = matches[0]

    category_index = (
        categories.index(default_category)
        if default_category in categories else 0
    )

    category = st.selectbox(
        f"{label} — Category",
        categories,
        index=category_index,
        key=f"{key_prefix}_category"
    )

    available = list_indices(category=category)

    if not available:
        st.warning("No indices found in this category.")
        return None

    options = ([NONE_OPTION] if allow_none else []) + available

    default_option = (
        default_index
        if default_index in available
        else available[0]
    )

    index_choice = st.selectbox(
        f"{label} — Index",
        options,
        index=options.index(default_option),
        key=f"{key_prefix}_index"
    )

    return None if index_choice == NONE_OPTION else index_choice


def select_indices(key_prefix, max_indices=2, default_indices=None):
    """
    Renders one "Category → Index" picker per slot (side by side) and
    returns the chosen index names, in order, skipping any left on
    "None". Duplicate picks (same index in both slots) are collapsed
    to a single entry. Returns an empty list if nothing is selected.
    """
    defaults = list(default_indices or [])
    cols = st.columns(max_indices)

    selected = []

    for i in range(max_indices):
        with cols[i]:
            default = defaults[i] if i < len(defaults) else None
            choice = select_single_index(
                f"Index {i + 1}",
                key_prefix=f"{key_prefix}_{i}",
                default_index=default,
                allow_none=True
            )

        if choice and choice not in selected:
            selected.append(choice)

    return selected
