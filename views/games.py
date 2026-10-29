"""
Games: short, playable lessons about investing.

Try to Time
    Five Nifty 500 factor indices race through each calendar year. Before
    each year the player sees only what was knowable at the previous
    year-end (last year, 3 and 5 years: returns, risk, worst falls, how
    often each has won) and backs one index. Points and a streak are tracked
    live. The opponent is a mystery rival, Momentum or Value drawn at random
    each game and held without switching; it stays hidden until the end
    screen, which compares the picks with the rival, the equal mix, simple
    rules (chase last year's winner, back the 3-year leader), the market,
    perfect hindsight and 10,000 random players. Every game opens with the
    instructions, then the goal.

The game is static/try-to-time.html in an st.iframe (the only
place JavaScript runs), so every animation happens in the browser with
no reruns. Data comes from core.time_game as one JSON payload.
"""

from pathlib import Path

import streamlit as st

from core.time_game import game_payload
from views import tutorial

STATIC = Path(__file__).resolve().parent.parent / "static"


@st.cache_resource(show_spinner=False)
def _template():
    return (STATIC / "try-to-time.html").read_text(encoding="utf-8")


def render_try_to_time():
    tutorial.launcher("try-to-time", "How to play")
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
            "- **Your money.** ₹1 lakh moves into your pick each year.\n"
            "- **The goal.** Beat your *mystery rival*: either Momentum or "
            "Value, drawn at random each game, bought at the start and never "
            "switched. Its identity and value stay hidden until the end.\n"
            "- **Source.** NSE Indices via FinAPI. Past returns don't predict "
            "future ones, which is rather the point."
        )


# =====================================================================
# CAN YOU HANDLE IT?
# =====================================================================

HANDLE_CSS = """
<style>
.hi-step {font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:#8A939E;
  font-weight:600; margin:0 0 0.2rem 0;}
</style>
"""


@st.cache_resource(show_spinner=False)
def _handle_template():
    return (STATIC / "handle-it.html").read_text(encoding="utf-8")


def render_handle_it():
    from core import fbi_metrics as fm
    from core.data import search_funds
    from core.handle_game import PRESETS, payload

    st.markdown(HANDLE_CSS, unsafe_allow_html=True)
    tutorial.launcher("can-you-handle-it", "How to play")
    universe = fm.equity_universe()
    names = universe["indexName"].tolist()
    ordered = [p for p in PRESETS if p in names] + [n for n in names if n not in PRESETS]

    with st.container(border=True):
        st.markdown("<div class='hi-step'>What do you want to invest in?</div>",
                    unsafe_allow_html=True)
        kind_col, pick_col = st.columns([1.1, 4], gap="medium", vertical_alignment="bottom")
        with kind_col:
            kind = st.segmented_control("Type", ["Index", "Mutual fund"], default="Index",
                                        key="hi_kind", label_visibility="collapsed") or "Index"
        key = label = None
        with pick_col:
            if kind == "Index":
                choice = st.selectbox("Index", ordered,
                                      index=ordered.index("NIFTY SMALLCAP 250")
                                      if "NIFTY SMALLCAP 250" in ordered else 0,
                                      format_func=fm.pretty_name, key="hi_index",
                                      label_visibility="collapsed")
                key, label = choice, fm.pretty_name(choice)
            else:
                term = st.text_input("Fund", placeholder="Type at least 3 letters of a fund name",
                                     key="hi_fund_q", label_visibility="collapsed")
                matches = search_funds(term) if term else []
                if matches:
                    opts = {m["name"]: m["code"] for m in matches[:60]}
                    name = st.selectbox("Fund", list(opts), key="hi_fund",
                                        label_visibility="collapsed")
                    key, label = opts[name], name
                elif term and len(term.strip()) >= 3:
                    st.caption("No funds found. Try another name.")

    if not key:
        st.info("Search for a fund above to start.")
        return
    with st.spinner("Loading history..."):
        try:
            data = payload("index" if kind == "Index" else "fund", key, label)
        except LookupError:
            st.warning("Couldn't download this fund's NAV history just now. Please try again in a minute.")
            return
    if data is None:
        st.warning("Couldn't load enough history for this one. Pick something with at least a few years of data, or try again in a minute.")
        return
    st.iframe(_handle_template().replace("__DATA__", data), height="content")
