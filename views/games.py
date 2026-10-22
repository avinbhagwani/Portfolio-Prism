"""
Games: short, playable lessons about investing.

Try to Time
    Five Nifty 500 factor indices race through each calendar year. Before
    each year the player sees only what was knowable at the previous
    year-end (last year, 3 and 5 years: returns, risk, worst falls, how
    often each has won) and backs one index. Points, a streak, and their
    money against an untouched equal mix are tracked live. The end screen
    compares their picks with the equal mix, simple rules (chase last
    year's winner, back the 3-year leader), the market, perfect hindsight
    and 10,000 random players.

The game is static/try-to-time.html in an st.iframe (the only
place JavaScript runs), so every animation happens in the browser with
no reruns. Data comes from core.time_game as one JSON payload.
"""

from pathlib import Path

import streamlit as st

from core.time_game import game_payload

STATIC = Path(__file__).resolve().parent.parent / "static"


@st.cache_resource(show_spinner=False)
def _template():
    return (STATIC / "try-to-time.html").read_text(encoding="utf-8")


def render_try_to_time():
    html = _template().replace("__DATA__", game_payload())
    st.iframe(html, height="content")   # grows and shrinks with each screen
    with st.expander("How the game works"):
        st.markdown(
            "- **The field.** Nifty500 Momentum 50, Value 50, Quality 50, Low "
            "Volatility 50 and Growth 50, all total return in INR. Nifty 500 is "
            "shown for reference but can't be picked.\n"
            "- **No peeking.** Each year you see only what was known at the "
            "previous year-end. 3- and 5-year figures use month-end levels; "
            "*risk* is annualised volatility of monthly returns and *worst "
            "fall* is the largest peak-to-trough drop. Windows that reach back "
            "before April 2005 use the history available and are marked.\n"
            "- **Scoring.** 100 points for the winner, 50 for second, 20 for "
            "third. Back-to-back winners add a streak bonus of 25 per year.\n"
            "- **Your money.** ₹1 lakh moves into your pick each year. The "
            "*equal mix* puts 20% in each index at the start and never touches "
            "it.\n"
            "- **Source.** NSE Indices via FinAPI. Past returns don't predict "
            "future ones, which is rather the point."
        )
