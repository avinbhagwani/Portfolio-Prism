"""
Home: what PRISM is, and proof of it, in one scroll.

Borrowed from how the best research sites open (Our World in Data's
chart-plus-takeaway cards, backtesters' one-click presets, Koyfin's
coverage and credibility blocks), kept in PRISM's light navy look.

  Hero       "Every return has a spectrum." beside the interactive prism
             (static/home-prism.html, the one place JavaScript is
             allowed), the main actions, one-click example funds and a
             line of live facts.
  The data   three cards computed from the index data on every refresh:
             this year's factor race, how far each factor sits below its
             peak, and how often each beat the market over 5 years.
             Each card opens the tool that goes deeper.
  Questions  one card per tool, framed as the question it answers.
  Games      the two games (no spoilers).
  Writing    the latest Substack article and a subscribe link.
  How        data sources and method, so the numbers can be trusted.
  Soon       what's coming, as one quiet line.

Navigation stays in native st.page_link so moving to a tool keeps the
session. Charts are plain HTML bars so they stay crisp and light.
"""

import base64
from pathlib import Path

import streamlit as st

from core import fbi_metrics as fm
from core import substack as sb
from core.config import MODEL_CONFIG
from core.fbi_metrics import as_of_date, equity_universe
from core.index_data import load_index_history
from core.time_game import CONTESTANTS, MARKET

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = {}  # set by app.py

# One-click examples for Factor Analysis (seed its search box)
EXAMPLES = [
    ("Parag Parikh Flexi Cap", "parag flexi"),
    ("HDFC Flexi Cap", "hdfc flexi"),
    ("Quant Small Cap", "quant small"),
    ("Nifty 50 index fund", "nifty 50 index"),
]

TOOLS = [
    ("factor-analysis", "What really drives my fund?", "Factor Analysis",
     "anim-factor-analysis.svg",
     "Split any Indian mutual fund, or a whole portfolio, into market, size, value, "
     "quality and momentum. What's left is the manager's real skill."),
    ("fbi-intelligence", "Which factor has held up best?", "FBI Intelligence",
     "anim-fbi-intelligence.svg",
     "Compare Nifty factor indices on return, risk, consistency and how often each "
     "beat the index it's built from."),
    ("drawdown-analysis", "How bad can it get?", "Drawdown Analysis",
     "anim-drawdown-analysis.svg",
     "Every major fall in an index or fund: how deep it went and how long the "
     "climb back took."),
    ("efficient-frontier", "What mix would have worked?", "Efficient Frontier",
     "anim-efficient-frontier.svg",
     "The best blend of indices for the risk you take, and whether that blend "
     "kept working afterwards."),
]

GAMES = [
    ("try-to-time", "Think you can time the factors?",
     "Back next year's winning index, every year from 2008, using only what was "
     "known at the time. Then see how you did against holding all five.",
     "Play Try to Time", "bars"),
    ("can-you-handle-it", "Can you handle it?",
     "Invest at the top, right before a crash, and live through it month by month. "
     "The Sell button is always there.",
     "Play Can You Handle It?", "fall"),
]

SOON = ["Retirement planning", "Portfolio attribution"]

GREY = MARKET[3]

CSS = """
<style>
/* ---------- hero ---------- */
.ph-by {font-size:0.88rem; color:#8A939E; margin:0 0 0.9rem 0;}
.ph-by b {color:#5B6572; font-weight:500;}
.ph-title {font-size:3.1rem; font-weight:700; color:#1B2533; line-height:1.06;
  letter-spacing:-0.028em; margin:0 0 1rem 0;}
.ph-title span {background: linear-gradient(90deg, #1F4E79, #2F8F9D 30%, #C08A2E 55%, #5E9A62 75%, #8E5B9F);
  -webkit-background-clip: text; background-clip: text; color: transparent;}
.ph-sub {font-size:1.12rem; color:#5B6572; line-height:1.55; max-width:31rem; margin:0 0 1.5rem 0;}
.st-key-ph_ctas a {border-radius:999px !important; padding:0.55rem 1.2rem !important;
  font-weight:500; transition:background 0.15s ease, border-color 0.15s ease;}
.st-key-ph_ctas a p {font-size:0.95rem !important; font-weight:500 !important;}
.st-key-ph_cta_primary a {background:#1F4E79 !important; border:1px solid #1F4E79 !important;}
.st-key-ph_cta_primary a p, .st-key-ph_cta_primary a span {color:#FFFFFF !important;}
.st-key-ph_cta_primary a:hover {background:#173E61 !important;}
.st-key-ph_cta_secondary a {background:#FFFFFF !important; border:1px solid #D5DCE3 !important;}
.st-key-ph_cta_secondary a p, .st-key-ph_cta_secondary a span {color:#1F4E79 !important;}
.st-key-ph_cta_secondary a:hover {background:#F4F7FA !important; border-color:#B9C4CF !important;}

/* example funds: small chips under the actions */
.ph-try {font-size:0.82rem; color:#8A939E; margin:1.3rem 0 0.45rem 0;}
.st-key-ph_examples {gap:0.4rem !important; flex-wrap:wrap;}
.st-key-ph_examples a {border:1px solid #E3E7EC !important; border-radius:999px !important;
  padding:0.18rem 0.75rem !important; background:#FFFFFF; min-height:0 !important;
  transition:border-color 0.15s ease, background 0.15s ease;}
.st-key-ph_examples a:hover {border-color:#1F4E79 !important; background:#F4F7FA;}
.st-key-ph_examples a p {font-size:0.82rem !important; color:#1F4E79 !important; font-weight:500 !important;}

.ph-facts {display:flex; gap:2.2rem; flex-wrap:wrap; margin:2.2rem 0 0 0;
  padding:1rem 0 0 0; border-top:1px solid #ECEFF2;}
.ph-fact b {display:block; font-size:1.45rem; font-weight:700; color:#1B2533;
  letter-spacing:-0.02em; font-variant-numeric:tabular-nums; line-height:1.2;}
.ph-fact small {font-size:0.8rem; color:#8A939E;}

/* ---------- section heads ---------- */
.ph-head {display:flex; align-items:baseline; justify-content:space-between; gap:1rem;
  flex-wrap:wrap; margin:3.6rem 0 1rem 0;}
.ph-head .t {font-size:1.45rem; font-weight:600; color:#17212D; line-height:1.2;
  letter-spacing:-0.018em;}
.ph-head span {font-size:0.84rem; color:#98A1AC;}
.ph-lede {font-size:0.98rem; color:#66707C; margin:-0.5rem 0 1.1rem 0; max-width:40rem; line-height:1.5;}

/* ---------- live insight cards ---------- */
.ph-ins-kicker {font-size:0.8rem; font-weight:500; color:#66707C; margin:0 0 0.35rem 0;}
.ph-ins-title {font-size:1.06rem; font-weight:600; color:#17212D; line-height:1.38;
  letter-spacing:-0.008em; margin:0 0 0.95rem 0; min-height:4.2em;}
.ph-ins-title b {font-weight:600;}
.ph-bars {display:flex; flex-direction:column; gap:7px; margin:0 0 0.4rem 0;}
.ph-bar {display:grid; grid-template-columns:5.6rem 1fr 3.4rem; align-items:center; gap:8px;
  font-size:0.8rem; color:#4A5562;}
.ph-bar .lab {white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.ph-bar .lab i {display:inline-block; width:8px; height:8px; border-radius:50%;
  margin-right:6px; vertical-align:0;}
.ph-bar .trk {position:relative; height:10px; background:#FFFFFF; border-radius:3px;}
.ph-bar .fill {position:absolute; top:0; bottom:0; border-radius:3px;}
.ph-bar .mid {position:absolute; top:-3px; bottom:-3px; width:1px; background:#C9D1DA;}
.ph-bar .val {text-align:right; font-weight:600; color:#17212D; font-variant-numeric:tabular-nums;}
.ph-bar .val.neg {color:#B54A3C;}
.ph-bar.mkt .lab, .ph-bar.mkt .val {color:#8A939E; font-weight:500;}
.ph-ins-note {font-size:0.76rem; color:#98A1AC; margin:0.55rem 0 0.2rem 0;}

/* ---------- question cards (tools) ---------- */
.ph-card-art {background:#FFFFFF; border-radius:10px; padding:6px 0;}
.ph-card-art img {display:block; width:100%; height:auto;}
.ph-q {font-size:1.2rem; font-weight:600; color:#17212D; line-height:1.25;
  letter-spacing:-0.012em; margin:0.1rem 0 0.2rem 0;}
.ph-tool {font-size:0.8rem; font-weight:500; color:#9A6B1E; margin:0 0 0.45rem 0;}
.ph-card-sub {font-size:0.9rem; color:#6B7480; line-height:1.5; margin:0 0 0.2rem 0;}

/* ---------- games ---------- */
.ph-play-title {font-size:1.2rem; font-weight:600; color:#1B2533; margin:0.6rem 0 0.25rem 0;}
.ph-play-sub {font-size:0.92rem; color:#6B7480; line-height:1.5;}
.ph-play-bars {display:flex; flex-direction:column; gap:5px; padding:4px 0;}
.ph-play-bars i {display:block; height:12px; border-radius:4px;}

/* ---------- writing band ---------- */
.ph-latest-meta {font-size:0.82rem; color:#9A6B1E; font-weight:500;}
.ph-latest-title {font-size:1.3rem; font-weight:600; color:#1B2533; line-height:1.3;
  letter-spacing:-0.012em; margin:0.2rem 0 0.35rem 0;}
.ph-latest-sub {font-size:0.94rem; color:#6B7480; line-height:1.5; margin:0 0 0.3rem 0;}
.st-key-card_latest .ph-sub-link {display:inline-block; margin-top:0.2rem; font-size:0.88rem;
  color:#1F4E79; font-weight:500; text-decoration:none; border-bottom:1px solid #C9D6E3;}
.st-key-card_latest .ph-sub-link:hover {border-bottom-color:#1F4E79;}

/* ---------- how it works ---------- */
.ph-how {display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:2rem;
  border-top:1px solid #E6EAEF; padding-top:1.4rem;}
.ph-how h4 {font-size:0.98rem !important; font-weight:600 !important; color:#17212D;
  margin:0 0 0.4rem 0 !important; padding:0 !important;}
.ph-how p {font-size:0.88rem; color:#66707C; line-height:1.55; margin:0;}
.ph-how a {color:#1F4E79; text-decoration:none; border-bottom:1px solid #C9D6E3;}
.ph-soon {margin:2.4rem 0 0 0; font-size:0.88rem; color:#98A1AC;}
.ph-soon b {color:#66707C; font-weight:500;}
.ph-soon em {font-style:normal; display:inline-block; font-size:0.74rem; font-weight:600;
  color:#9A6B1E; background:#FBF3E4; padding:1px 8px; border-radius:999px; margin-right:0.5rem;}

@media (max-width: 640px) {
  .ph-title {font-size:2.2rem;}
  .ph-sub {font-size:1rem;}
  .ph-facts {gap:1.4rem;}
  .ph-head {margin-top:2.6rem;}
  .ph-ins-title {min-height:0;}
  .ph-how {grid-template-columns:1fr; gap:1.2rem;}
  [class*="st-key-card_tool_"] .ph-card-art img {max-height:96px; width:auto; margin:0 auto;}
}
</style>
"""


# =====================================================================
# Data
# =====================================================================

def _svg_img(name):
    data = base64.b64encode((STATIC / name).read_bytes()).decode()
    return f"<img src='data:image/svg+xml;base64,{data}' alt=''>"


@st.cache_data(show_spinner=False)
def _stats():
    history = load_index_history()
    first_year = history.index.min().year
    years = as_of_date().year - first_year
    return len(equity_universe()), years, len(MODEL_CONFIG)


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def _insights():
    """Live numbers for the three data cards. None if the data is missing."""
    racers = [(c[2], c[1], c[3]) for c in CONTESTANTS]
    market = (MARKET[2], MARKET[1], GREY)
    names = [n for _, n, _ in racers] + [market[1]]
    levels = fm.levels_to_as_of(names)
    if any(n not in levels.columns for n in names):
        return None
    as_of = as_of_date()

    # 1. this year so far (falls back to last full year in January)
    cal, partial = fm.calendar_returns(levels)
    year = partial if partial in cal.index else int(cal.index[-1])
    row = cal.loc[year]
    race = sorted(((lab, col, float(row[n])) for lab, n, col in racers),
                  key=lambda r: -r[2])
    race_mkt = float(row[market[1]])

    # 2. distance below each index's own peak
    below = sorted(((lab, col, float(fm.current_drawdown(levels[n].dropna())))
                    for lab, n, col in racers), key=lambda r: r[2])
    below_mkt = float(fm.current_drawdown(levels[market[1]].dropna()))

    # 3. share of rolling 5-year periods each beat the Nifty 500
    roll = fm.rolling_cagr(levels, 5)
    hits, since = [], None
    for lab, n, col in racers:
        h = fm.hit_rate(roll, n, market[1])
        if h:
            hits.append((lab, col, float(h["pct"])))
            since = h["since"]
    hits.sort(key=lambda r: -r[2])

    return dict(as_of=as_of, year=year, partial=year == partial,
                race=race, race_mkt=race_mkt, below=below, below_mkt=below_mkt,
                hits=hits, since=since)


# =====================================================================
# Small HTML charts
# =====================================================================

def _bar_row(label, colour, value, lo, hi, text, mkt=False, neg=False):
    """One horizontal bar on a lo..hi scale with a zero line."""
    span = (hi - lo) or 1
    zero = (0 - lo) / span * 100
    pos = (value - lo) / span * 100
    left, width = min(zero, pos), abs(pos - zero)
    fill = f"<span class='fill' style='left:{left:.1f}%;width:{max(width, 0.8):.1f}%;background:{colour}'></span>"
    mid = f"<span class='mid' style='left:{zero:.1f}%'></span>" if 0 < zero < 100 else ""
    return (f"<div class='ph-bar{' mkt' if mkt else ''}'>"
            f"<span class='lab'><i style='background:{colour}'></i>{label}</span>"
            f"<span class='trk'>{fill}{mid}</span>"
            f"<span class='val{' neg' if neg else ''}'>{text}</span></div>")


def _race_chart(ins):
    vals = [v for _, _, v in ins["race"]] + [ins["race_mkt"]]
    lo, hi = min(0.0, min(vals)), max(0.0, max(vals))
    pad = (hi - lo) * 0.04
    lo, hi = lo - (pad if lo < 0 else 0), hi + pad
    rows = [_bar_row(l, c, v, lo, hi, fm.fmt_pct(v, signed=True), neg=v < 0)
            for l, c, v in ins["race"]]
    m = ins["race_mkt"]
    rows.append(_bar_row("Nifty 500", GREY, m, lo, hi, fm.fmt_pct(m, signed=True), mkt=True))
    return "<div class='ph-bars'>" + "".join(rows) + "</div>"


def _below_chart(ins):
    worst = min([v for _, _, v in ins["below"]] + [ins["below_mkt"]])
    lo = min(worst * 1.04, -1.0)
    rows = []
    for l, c, v in ins["below"]:
        text = "At high" if v > -0.05 else fm.fmt_pct(v)
        rows.append(_bar_row(l, c, v, lo, 0, text, neg=v <= -0.05))
    m = ins["below_mkt"]
    rows.append(_bar_row("Nifty 500", GREY, m, lo, 0,
                         "At high" if m > -0.05 else fm.fmt_pct(m), mkt=True))
    return "<div class='ph-bars'>" + "".join(rows) + "</div>"


def _hits_chart(ins):
    rows = [_bar_row(l, c, v, 0, 100, f"{v:.0f}%") for l, c, v in ins["hits"]]
    return "<div class='ph-bars'>" + "".join(rows) + "</div>"


def _race_title(ins):
    top, bottom = ins["race"][0], ins["race"][-1]
    when = f"{ins['year']} so far" if ins["partial"] else str(ins["year"])
    spread = top[2] - bottom[2]
    return (f"<b>{top[0]}</b> leads {when} at {fm.fmt_pct(top[2], signed=True)}. "
            f"{bottom[0]} trails at {fm.fmt_pct(bottom[2], signed=True)}, a "
            f"{spread:.1f}-point spread inside one market.")


def _below_title(ins):
    at_high = [l for l, _, v in ins["below"] if v > -0.05]
    deepest = ins["below"][0]
    first = (f"<b>{at_high[0]}</b> is at a record high" if at_high
             else f"No factor is at its high")
    return (f"{first}, while <b>{deepest[0]}</b> is still "
            f"{abs(deepest[2]):.1f}% below its peak.")


def _hits_title(ins):
    best = ins["hits"][0]
    since = f"{ins['since']:%Y}" if ins["since"] is not None else "the start"
    return (f"<b>{best[0]}</b> beat the Nifty 500 in {best[2]:.0f}% of rolling "
            f"5-year periods since {since}.")


# =====================================================================
# Sections
# =====================================================================

def _head(title, note=""):
    st.markdown(f"<div class='ph-head'><div class='t'>{title}</div>"
                f"{f'<span>{note}</span>' if note else ''}</div>",
                unsafe_allow_html=True)


def _hero():
    n_idx, years, n_models = _stats()
    left, right = st.columns([1, 1.12], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='ph-by'>by <b>Avin Bhagwani</b></div>"
            "<div class='ph-title'>Every return has a <span>spectrum</span>.</div>"
            "<div class='ph-sub'>See what really drives Indian mutual funds and Nifty "
            "indices: the factors underneath, the falls they live through and the mixes "
            "that hold up. Free, and built on published factor research.</div>",
            unsafe_allow_html=True,
        )
        with st.container(key="ph_ctas", horizontal=True, gap="small"):
            if "factor-analysis" in PAGES:
                with st.container(key="ph_cta_primary", width="content"):
                    st.page_link(PAGES["factor-analysis"], label="Analyse a fund",
                                 icon=":material/arrow_forward:", icon_position="right")
            if "fbi-intelligence" in PAGES:
                with st.container(key="ph_cta_secondary", width="content"):
                    st.page_link(PAGES["fbi-intelligence"], label="Explore indices",
                                 icon=":material/query_stats:")
        if "factor-analysis" in PAGES:
            st.markdown("<div class='ph-try'>Or start with a fund</div>",
                        unsafe_allow_html=True)
            with st.container(key="ph_examples", horizontal=True, gap=None):
                for label, term in EXAMPLES:
                    st.page_link(PAGES["factor-analysis"], label=label,
                                 query_params={"fund": term}, width="content",
                                 icon=":material/search:")
    with right:
        st.iframe((STATIC / "home-prism.html").read_text(encoding="utf-8"), height=400)

    st.markdown(
        "<div class='ph-facts'>"
        f"<div class='ph-fact'><b>{n_idx}</b><small>Nifty equity indices</small></div>"
        f"<div class='ph-fact'><b>{years} years</b><small>of index history</small></div>"
        f"<div class='ph-fact'><b>{n_models}</b><small>factor models</small></div>"
        "<div class='ph-fact'><b>Every fund</b><small>in India, by name</small></div>"
        f"<div class='ph-fact'><b>{as_of_date():%b %Y}</b><small>latest month in the data</small></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _data_cards():
    try:
        ins = _insights()
    except Exception:     # the homepage must never fail on a data hiccup
        ins = None
    if not ins:
        return
    _head("What the data says right now",
          f"Five Nifty 500 factor indices, total return, to {ins['as_of']:%d %b %Y}")
    cards = [
        ("fbi-intelligence",
         f"The factor race, {ins['year']}{' so far' if ins['partial'] else ''}",
         _race_title(ins), _race_chart(ins), "Compare every index"),
        ("drawdown-analysis", "Distance from the peak",
         _below_title(ins), _below_chart(ins), "See every fall and recovery"),
        ("fbi-intelligence", "Beat the market over 5 years",
         _hits_title(ins), _hits_chart(ins), "See hit ratios for every index"),
    ]
    cols = st.columns(3, gap="medium")
    for i, (col, (path, kicker, title, chart, cta)) in enumerate(zip(cols, cards)):
        with col, st.container(key=f"card_ins_{i}"):
            note = ("Share of monthly-rolling 5-year windows with a higher return "
                    "than the Nifty 500." if i == 2 else
                    "Below the index's own all-time high, month-end." if i == 1 else
                    "Calendar-year return.")
            st.markdown(
                f"<div class='ph-ins-kicker'>{kicker}</div>"
                f"<div class='ph-ins-title'>{title}</div>{chart}"
                f"<div class='ph-ins-note'>{note}</div>",
                unsafe_allow_html=True,
            )
            if path in PAGES:
                st.page_link(PAGES[path], label=cta, icon=":material/arrow_forward:")


def _questions():
    tools = [t for t in TOOLS if t[0] in PAGES]
    if not tools:
        return
    _head("Start with a question")
    for row in range(0, len(tools), 2):
        cols = st.columns(2, gap="medium")
        for col, (path, q, name, art, blurb) in zip(cols, tools[row:row + 2]):
            with col, st.container(key=f"card_tool_{path}"):
                a, b = st.columns([1, 1.5], gap="medium", vertical_alignment="center")
                with a:
                    st.markdown(f"<div class='ph-card-art'>{_svg_img(art)}</div>",
                                unsafe_allow_html=True)
                with b:
                    st.markdown(
                        f"<div class='ph-q'>{q}</div>"
                        f"<div class='ph-tool'>{name}</div>"
                        f"<div class='ph-card-sub'>{blurb}</div>",
                        unsafe_allow_html=True,
                    )
                    st.page_link(PAGES[path], label=f"Open {name}",
                                 icon=":material/arrow_forward:")


def _games():
    games = [g for g in GAMES if g[0] in PAGES]
    if not games:
        return
    _head("Test your nerve", "Two short games, real Indian market history")
    cols = st.columns(len(games), gap="medium")
    for col, (path, title, blurb, cta, art) in zip(cols, games):
        with col, st.container(key=f"card_play_{path}"):
            if art == "bars":
                pic = "".join(f"<i style='background:{c};width:{w}%'></i>" for c, w in
                              [("#C08A2E", 92), ("#2F6FB0", 74), ("#8E5B9F", 66),
                               ("#5E9A62", 48), ("#2F8F9D", 37)])
                pic = f"<div class='ph-play-bars'>{pic}</div>"
            else:
                pic = ("<svg viewBox='0 0 300 76' width='100%' height='76' preserveAspectRatio='none'>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 L215,14 L0,14Z' "
                       "fill='#B54A3C' opacity='0.14'/>"
                       "<line x1='0' x2='300' y1='14' y2='14' stroke='#CBD3DC' stroke-dasharray='4 4'/>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 S270,4 300,2' "
                       "fill='none' stroke='#1F4E79' stroke-width='2.5'/></svg>")
            st.markdown(
                f"<div class='ph-card-art' style='padding:10px 12px;height:96px;display:flex;"
                f"flex-direction:column;justify-content:center'>{pic}</div>"
                f"<div class='ph-play-title'>{title}</div>"
                f"<div class='ph-play-sub'>{blurb}</div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES[path], label=cta, icon=":material/arrow_forward:")


def _writing():
    if "writing" not in PAGES:
        return
    try:
        posts, _ = sb.load_posts()
    except Exception:
        posts = []
    if not posts:
        return
    p = posts[0]
    _head("From my Substack", "Long reads on factors, funds and behaviour")
    with st.container(key="card_latest"):
        a, b = st.columns([1, 2.2], gap="large", vertical_alignment="center")
        with a:
            if p.cover:
                st.image(p.cover, width="stretch")
        with b:
            date = f"{p.date:%d %b %Y}" if p.date else ""
            mins = f" · {p.read_minutes} min read" if p.words else ""
            st.markdown(
                f"<div class='ph-latest-meta'>Latest · {date}{mins}</div>"
                f"<div class='ph-latest-title'>{p.title}</div>"
                f"<div class='ph-latest-sub'>{p.subtitle}</div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES["writing"], label="Read the article",
                         icon=":material/arrow_forward:",
                         query_params={"post": p.slug})
            st.markdown(
                f"<a class='ph-sub-link' href='{sb.tracked(sb.SUBSCRIBE_URL, 'home')}' "
                "target='_blank'>Get new articles by email</a>",
                unsafe_allow_html=True,
            )


def _how():
    _head("How PRISM works")
    st.markdown(
        "<div class='ph-how'>"
        "<div><h4>Index data</h4><p>Total-return history for Nifty equity indices, "
        "cut at the last complete month so every comparison uses the same window. "
        "Price-only, leveraged and inverse series are left out.</p></div>"
        "<div><h4>Factor research</h4><p>Equity factors from the IndiaFactorLibrary "
        "(Invespar), built as in Raju (2022), "
        "<a href='https://ssrn.com/abstract=4054146' target='_blank'>SSRN 4054146</a>. "
        "Regressions use monthly returns and Newey-West standard errors.</p></div>"
        "<div><h4>Fund NAVs</h4><p>Daily NAVs for every Indian mutual fund plan from "
        "mfapi.in, turned into month-end returns.</p></div>"
        "</div>"
        "<div class='ph-soon'><em>Soon</em>"
        + " &nbsp;·&nbsp; ".join(f"<b>{s}</b>" for s in SOON) +
        "</div>",
        unsafe_allow_html=True,
    )


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    _hero()
    _data_cards()
    _questions()
    _games()
    _writing()
    _how()
