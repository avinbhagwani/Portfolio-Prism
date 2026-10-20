"""
Placeholder for nav items that don't have a built tool yet.
"""

import streamlit as st


def render(title):
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
