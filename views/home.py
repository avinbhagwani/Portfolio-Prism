"""
Home: what PRISM is, in as few words as possible, set in a star atlas.

  Hero      "Every return has a spectrum." beside the PRISM triangle as a
            thick glass slab. It sways in front of a slowly turning star
            chart (degree scale, coordinate rings, the ecliptic, the Big
            Dipper, Cassiopeia and Orion); a sweep circles the chart and
            lights each constellation as it passes, and a ring of light
            orbits through the glass. It leans towards the cursor.
  Numbers   a strip of live facts from the data
  Tools     one card per tool
  Games     the two games
  Soon      what's coming (retirement planning, portfolio attribution)
  Writing   the latest Substack article

The page follows Streamlit's light or dark theme: light reads as a printed
star chart (navy and gold ink on off-white), dark as the night sky. Behind
everything sits a faint star field with celestial grid lines and
constellations that draw themselves in.

The prism is static/home-prism-light.html or home-prism-dark.html in an
st.iframe, the one place JavaScript is allowed. Navigation stays in native
st.page_link so moving to a tool keeps the session.
"""

import base64
import random
from pathlib import Path

import streamlit as st

from charts.theme import get_streamlit_theme_type
from core import substack as sb
from core.config import MODEL_CONFIG
from core.fbi_metrics import as_of_date, equity_universe
from core.index_data import load_index_history
from views import tutorial

STATIC = Path(__file__).resolve().parent.parent / "static"
PAGES = {}  # set by app.py

LENSES = [
    ("factor-analysis", "Factor Analysis", "bars",
     "Split any Indian mutual fund into the factors behind its returns."),
    ("fbi-intelligence", "FBI Intelligence", "lines",
     "Compare Nifty factor indices on return, risk and consistency."),
    ("drawdown-analysis", "Drawdown Analysis", "fall",
     "How far an index fell, and how long it took to recover."),
    ("efficient-frontier", "Efficient Frontier", "frontier",
     "The best mix of indices for the risk, and whether it lasted."),
]

SOON = [
    ("Retirement planning", "Will the money last? Plan income for every stage."),
    ("Portfolio attribution", "Which decisions added return, and which cost it."),
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

# ---------------------------------------------------------------------
# Two palettes: a printed star chart (light) and the night sky (dark)
# ---------------------------------------------------------------------

PALETTES = {
    "light": dict(
        bg="#F7F9FC", ink="#17212D", body="#4E5966", muted="#66707C", strong="#3B4652",
        card="#FFFFFF", card_hover="#FFFFFF", line="#E6EAEF", line_hover="#C3CDD8",
        art="#F1F4F8", dashed="#D5DCE3", pill="#EEF2F6", pill_text="#4E5966",
        link="#1F4E79", label="#8A5A16", free="#8A5A16",
        btn="#1F4E79", btn_text="#FFFFFF", btn_hover="#173E61",
        btn2_border="#D5DCE3", btn2_text="#1F4E79", btn2_hover="#EEF2F6",
        spectrum="linear-gradient(90deg, #1F4E79, #2F8F9D 30%, #C08A2E 55%, #5E9A62 75%, #8E5B9F)",
        star="#9AA6B4", star_op=0.6, gold="#B07A2A", grid="#1F4E79", grid_op=0.07,
        con_line="#1F4E79", con_star="#3E5C7C", con_op=0.32, meteor="#1F4E79",
        bar="#1F4E79", bar_quiet="#C3CBD4", line_a="#2563EB", line_b="#F97316",
        fall="#B54A3C", fall_fill="#B54A3C", fall_op=0.14, base_line="#CBD3DC",
        game_fall="#F0525F", game_fall_op=0.16, game_line="#1F4E79",
    ),
    "dark": dict(
        bg="#060D18", ink="#F3F6FA", body="#A9B8C8", muted="#8FA2B6", strong="#DCE6F0",
        card="#0B1626", card_hover="#0E1B2E", line="#1A2A3E", line_hover="#2E4560",
        art="#0F1E32", dashed="#24364D", pill="#15243A", pill_text="#C7D6E4",
        link="#9FC0DE", label="#E0B15C", free="#E0B15C",
        btn="#F3F6FA", btn_text="#0B1626", btn_hover="#DCE6F0",
        btn2_border="#2A3D55", btn2_text="#DCE6F0", btn2_hover="#0E1B2E",
        spectrum="linear-gradient(90deg, #9FC0DE, #4FB3BF 30%, #E0B15C 55%, #8FC67A 75%, #C48CB0)",
        star="#DCE6F0", star_op=0.85, gold="#E0B15C", grid="#9FC0DE", grid_op=0.08,
        con_line="#9FC0DE", con_star="#E6ECF2", con_op=0.4, meteor="#FFFFFF",
        bar="#9FC0DE", bar_quiet="#3A4D63", line_a="#60A5FA", line_b="#FB923C",
        fall="#E07A6A", fall_fill="#E07A6A", fall_op=0.18, base_line="#3A4D63",
        game_fall="#F0525F", game_fall_op=0.25, game_line="#9FC0DE",
    ),
}

# Constellations: points, the lines between them, and star sizes
DIPPER = ([(0, 0), (40, 8), (72, 22), (100, 40), (108, 74), (150, 82), (160, 46)],
          [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 3)],
          [2.4, 2, 2, 1.8, 2.2, 2.6, 2.4])
CASS = ([(0, 20), (30, 0), (55, 28), (85, 8), (110, 30)],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        [2.2, 2.6, 2.4, 2, 2.2])
ORION = ([(0, 0), (70, -6), (22, 58), (35, 62), (48, 66), (10, 120), (68, 116), (36, -26)],
         [(0, 2), (1, 4), (2, 3), (3, 4), (2, 5), (4, 6), (0, 7), (1, 7)],
         [3, 2.6, 2, 2, 2, 2.4, 3, 1.6])


def _figure(con, ox, oy, sc, p, delay):
    pts, edges, mag = con
    P = [(ox + x * sc, oy + y * sc) for x, y in pts]
    d = "".join(f"M{P[a][0]:.1f},{P[a][1]:.1f}L{P[b][0]:.1f},{P[b][1]:.1f}" for a, b in edges)
    out = (f'<path d="{d}" stroke="{p["con_line"]}" stroke-opacity="{p["con_op"]}" '
           f'stroke-width="0.8" fill="none" pathLength="1" class="cd" '
           f'style="animation-delay:{delay}s"/>')
    for i, ((x, y), m) in enumerate(zip(P, mag)):
        out += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{m * sc ** 0.5:.1f}" '
                f'fill="{p["con_star"]}" class="t{i % 3}"/>')
    return out


@st.cache_data(show_spinner=False)
def _sky(theme):
    """The page background as an SVG data URI: stars, grid, constellations."""
    p = PALETTES[theme]
    rnd = random.Random(7)
    stars = "".join(
        f'<circle cx="{rnd.uniform(0, 1000):.1f}" cy="{rnd.uniform(0, 2400):.1f}" '
        f'r="{rnd.choice([0.7, 0.8, 0.9, 1.0, 1.2, 1.4]):.1f}"'
        f'{" class=%st%d%s" % (chr(34), i % 3, chr(34)) if i % 4 == 0 else ""}/>'
        for i in range(70))
    golds = "".join(
        f'<circle cx="{x}" cy="{y}" r="1.4" class="t{i}"/>'
        for i, (x, y) in enumerate([(672, 96), (250, 1240), (930, 1760)]))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 2400" preserveAspectRatio="xMidYMin slice">
<style>
@keyframes tw{{0%,100%{{opacity:.25}}50%{{opacity:1}}}}
@keyframes cd{{0%{{stroke-dashoffset:1;opacity:0}}8%{{opacity:1}}35%{{stroke-dashoffset:0}}85%{{stroke-dashoffset:0;opacity:1}}100%{{stroke-dashoffset:0;opacity:0}}}}
@keyframes sh{{0%{{transform:translate(0,0);opacity:0}}2%{{opacity:1}}9%{{transform:translate(-420px,210px);opacity:0}}100%{{transform:translate(-420px,210px);opacity:0}}}}
.t0{{animation:tw 3.2s ease-in-out infinite}}
.t1{{animation:tw 4.6s ease-in-out infinite 1.2s}}
.t2{{animation:tw 5.8s ease-in-out infinite 2.4s}}
.cd{{stroke-dasharray:1;animation:cd 14s ease-in-out infinite}}
.sh{{opacity:0;animation:sh 11s ease-out infinite 2s}}
@media (prefers-reduced-motion: reduce){{.t0,.t1,.t2,.cd,.sh{{animation:none}}.cd{{stroke-dasharray:none}}}}
</style>
<g fill="{p['star']}" fill-opacity="{p['star_op']}">{stars}</g>
<g fill="none" stroke="{p['grid']}" stroke-opacity="{p['grid_op']}" stroke-width="0.8">
<ellipse cx="500" cy="1100" rx="1300" ry="980"/>
<ellipse cx="500" cy="1100" rx="900" ry="1150" stroke-dasharray="3 7"/>
<ellipse cx="500" cy="1100" rx="420" ry="1250" stroke-dasharray="3 7"/>
<path d="M-50,520 C250,470 750,470 1050,520" stroke-dasharray="3 7"/>
<path d="M-50,1580 C250,1640 750,1640 1050,1580" stroke-dasharray="3 7"/>
</g>
{_figure(CASS, 790, 668, 1.05, p, 0)}
{_figure(ORION, 880, 1040, 0.5, p, 4.5)}
{_figure(DIPPER, 760, 1372, 0.75, p, 9)}
<g fill="{p['gold']}">{golds}</g>
<line x1="930" y1="330" x2="990" y2="300" stroke="{p['meteor']}" stroke-width="1.3" stroke-linecap="round" class="sh"/>
</svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _css(theme):
    p = PALETTES[theme]
    return f"""
<style>
/* the sky behind the page */
[data-testid="stMain"] {{
  background-color:{p['bg']};
  background-image:url("{_sky(theme)}");
  background-size:100% auto; background-repeat:no-repeat; background-position:top center;
  background-attachment:local;
}}
[data-testid="stHeader"] {{ background:transparent; }}

.ph-by {{font-size:0.88rem; color:{p['muted']}; margin:0 0 1rem 0;}}
.ph-by b {{color:{p['strong']}; font-weight:600;}}
.ph-title {{font-size:3.6rem; font-weight:800; color:{p['ink']}; line-height:1.03;
  letter-spacing:-0.035em; margin:0 0 1.2rem 0;}}
.ph-title span {{background:{p['spectrum']};
  -webkit-background-clip:text; background-clip:text; color:transparent;}}
.ph-sub {{font-size:1.15rem; color:{p['body']}; line-height:1.55; max-width:28rem; margin:0 0 1.8rem 0;}}

.st-key-ph_ctas a {{border-radius:999px !important; padding:0.6rem 1.3rem !important;
  transition:background 0.15s ease, border-color 0.15s ease;}}
.st-key-ph_ctas a p {{font-size:0.95rem !important; font-weight:600 !important;}}
.st-key-ph_cta_primary a {{background:{p['btn']} !important; border:1px solid {p['btn']} !important;}}
.st-key-ph_cta_primary a p, .st-key-ph_cta_primary a span {{color:{p['btn_text']} !important;}}
.st-key-ph_cta_primary a:hover {{background:{p['btn_hover']} !important;}}
.st-key-ph_cta_secondary a {{background:transparent !important; border:1px solid {p['btn2_border']} !important;}}
.st-key-ph_cta_secondary a p, .st-key-ph_cta_secondary a span {{color:{p['btn2_text']} !important;}}
.st-key-ph_cta_secondary a:hover {{background:{p['btn2_hover']} !important;}}
[class*="st-key-tutpill_"] button {{background:transparent !important;}}
[class*="st-key-tutpill_"] button p {{color:{p['body']} !important;}}

.ph-stats {{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:1.6rem 0 0 0;}}
.ph-stat {{background:{p['card']}; border:1px solid {p['line']}; border-radius:16px; padding:18px 20px;}}
.ph-stat b {{display:block; font-size:1.85rem; font-weight:700; color:{p['ink']}; letter-spacing:-0.02em;}}
.ph-stat small {{font-size:0.88rem; color:{p['muted']};}}
.ph-stat.free b {{color:{p['free']};}}
.ph-section {{font-size:1.75rem; letter-spacing:-0.02em; color:{p['ink']}; font-weight:700; margin:3.6rem 0 1.1rem 0;}}

/* cards: solid surface, thin edge, a small lift on hover */
[class*="st-key-card_"] {{background:{p['card']} !important; border:1px solid {p['line']};
  border-radius:18px !important; padding:0 !important; overflow:hidden; gap:0 !important;
  transition:transform .3s cubic-bezier(.2,.8,.2,1), border-color .3s, background .3s;}}
[class*="st-key-card_"]:hover {{transform:translateY(-2px); border-color:{p['line_hover']};
  background:{p['card_hover']} !important;}}
[class*="st-key-card_"] [data-testid="stPageLink"] {{padding:12px 20px 18px 20px;}}
[class*="st-key-card_"] [data-testid="stPageLink"] a {{padding:0 !important; background:transparent !important;}}
[class*="st-key-card_"] [data-testid="stPageLink"] a > span:has([data-testid="stIconMaterial"]) {{display:none;}}
[class*="st-key-card_"] [data-testid="stPageLink"] a p,
[class*="st-key-card_"] [data-testid="stPageLink"] a span {{color:{p['link']} !important; font-weight:600 !important; font-size:0.9rem !important;
  white-space:normal !important; overflow:visible !important; text-overflow:clip !important;}}
.ph-art {{height:128px; background:{p['art']}; display:flex; align-items:center; justify-content:center;}}
.ph-card-body {{padding:18px 20px 8px 20px;}}
.ph-card-title {{font-size:1.08rem; font-weight:600; color:{p['ink']}; margin:0 0 0.4rem 0;}}
.ph-card-sub {{font-size:0.9rem; color:{p['body']}; line-height:1.5; min-height:2.8rem;}}

.st-key-card_play_try-to-time, .st-key-card_play_can-you-handle-it {{padding:0 !important;}}
.ph-game {{display:flex; flex-wrap:wrap; gap:22px; align-items:center; padding:24px 24px 6px 24px;}}
.ph-game-art {{flex:0 0 150px; height:120px; border-radius:12px; background:{p['art']}; padding:14px;
  box-sizing:border-box; display:flex; flex-direction:column; justify-content:center; gap:6px;}}
.ph-game-art i {{display:block; height:11px; border-radius:4px;}}
.ph-game-text {{flex:1 1 200px; min-width:0;}}
.ph-meta {{font-size:0.75rem; color:{p['label']}; font-weight:600; letter-spacing:0.08em; text-transform:uppercase;}}
.ph-play-title {{font-size:1.2rem; font-weight:600; color:{p['ink']}; margin:0.25rem 0 0.3rem 0;}}
.ph-play-sub {{font-size:0.9rem; color:{p['body']}; line-height:1.5;}}
.st-key-card_play_try-to-time [data-testid="stPageLink"],
.st-key-card_play_can-you-handle-it [data-testid="stPageLink"] {{padding:12px 24px 20px 196px;}}

.ph-soon-row {{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px;}}
.ph-soon {{display:flex; gap:16px; align-items:flex-start; padding:20px 22px; border-radius:16px; border:1px dashed {p['dashed']};}}
.ph-soon-pill {{flex:0 0 auto; font-size:0.68rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase;
  color:{p['pill_text']}; background:{p['pill']}; padding:4px 9px; border-radius:999px;}}
.ph-soon-title {{font-size:1rem; font-weight:600; color:{p['strong']}; margin:0 0 0.2rem 0;}}
.ph-soon-sub {{font-size:0.88rem; color:{p['muted']}; line-height:1.45;}}

.st-key-card_latest {{padding:20px !important;}}
.ph-latest-title {{font-size:1.4rem; font-weight:600; color:{p['ink']}; letter-spacing:-0.015em; margin:0.3rem 0 0.3rem 0;}}
.ph-latest-sub {{font-size:0.95rem; color:{p['body']};}}
.st-key-card_latest [data-testid="stPageLink"] {{padding:0.6rem 0 0 0;}}

@media (max-width: 640px) {{
  .ph-title {{font-size:2.6rem;}}
  .st-key-card_play_try-to-time [data-testid="stPageLink"],
  .st-key-card_play_can-you-handle-it [data-testid="stPageLink"] {{padding:0 24px 20px 24px;}}
}}
</style>
"""


def _art(kind, p):
    if kind == "bars":
        return (f'<svg width="150" height="84" viewBox="0 0 150 84" aria-hidden="true">'
                f'<line x1="0" y1="56" x2="150" y2="56" stroke="{p["base_line"]}"/>'
                f'<rect x="8" y="10" width="18" height="46" rx="3" fill="{p["bar"]}"/>'
                f'<rect x="34" y="56" width="18" height="12" rx="3" fill="{p["bar"]}"/>'
                f'<rect x="60" y="36" width="18" height="20" rx="3" fill="{p["bar"]}"/>'
                f'<rect x="86" y="50" width="18" height="6" rx="2" fill="{p["bar_quiet"]}"/>'
                f'<rect x="112" y="56" width="18" height="8" rx="2" fill="{p["bar"]}"/></svg>')
    if kind == "lines":
        return (f'<svg width="150" height="84" viewBox="0 0 150 84" aria-hidden="true">'
                f'<path d="M0,74 C30,68 46,56 70,52 S110,26 150,10" fill="none" stroke="{p["line_a"]}" stroke-width="2.6"/>'
                f'<path d="M0,74 C30,70 52,64 78,60 S120,46 150,40" fill="none" stroke="{p["line_b"]}" stroke-width="2.6"/></svg>')
    if kind == "fall":
        return (f'<svg width="150" height="84" viewBox="0 0 150 84" aria-hidden="true">'
                f'<line x1="0" y1="12" x2="150" y2="12" stroke="{p["base_line"]}" stroke-dasharray="4 4"/>'
                f'<path d="M0,12 C20,14 32,56 52,70 S80,76 96,56 S128,16 150,12 Z" fill="{p["fall_fill"]}" opacity="{p["fall_op"]}"/>'
                f'<path d="M0,12 C20,14 32,56 52,70 S80,76 96,56 S128,16 150,12" fill="none" stroke="{p["fall"]}" stroke-width="2.4"/></svg>')
    return (f'<svg width="150" height="84" viewBox="0 0 150 84" aria-hidden="true">'
            f'<path d="M12,78 C24,40 56,18 144,8" fill="none" stroke="{p["bar"]}" stroke-width="2.6"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{p["muted"]}" opacity="0.6"/>'
                      for x, y in [(46, 60), (78, 50), (100, 66), (120, 40)])
            + f'<circle cx="66" cy="26" r="4.5" fill="{p["gold"]}"/></svg>')


@st.cache_data(show_spinner=False)
def _stats():
    history = load_index_history()
    first_year = history.index.min().year
    years = as_of_date().year - first_year
    return len(equity_universe()), years, len(MODEL_CONFIG)


def render():
    theme = get_streamlit_theme_type()
    p = PALETTES[theme]
    st.markdown(_css(theme), unsafe_allow_html=True)

    left, right = st.columns([1, 1.1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='ph-by'>by <b>Avin Bhagwani</b></div>"
            "<div class='ph-title'>Every return has a <span>spectrum</span>.</div>"
            "<div class='ph-sub'>PRISM looks through Indian funds, indices and "
            "portfolios to show what really drives them.</div>",
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
        tutorial.launcher("home", "New here? Take the tour")
    with right:
        st.iframe((STATIC / f"home-prism-{theme}.html").read_text(encoding="utf-8"), height=500)

    n_idx, years, n_models = _stats()
    st.markdown(
        "<div class='ph-stats'>"
        f"<div class='ph-stat'><b>{n_idx}</b><small>Nifty equity indices</small></div>"
        f"<div class='ph-stat'><b>{years} years</b><small>of index history</small></div>"
        f"<div class='ph-stat'><b>{n_models}</b><small>factor models</small></div>"
        "<div class='ph-stat free'><b>Free</b><small>to use</small></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='ph-section'>Tools</div>", unsafe_allow_html=True)
    cols = st.columns(len(LENSES), gap="medium")
    for col, (path, title, art, blurb) in zip(cols, LENSES):
        with col, st.container(key=f"card_lens_{path}"):
            st.markdown(
                f"<div class='ph-art'>{_art(art, p)}</div>"
                f"<div class='ph-card-body'><div class='ph-card-title'>{title}</div>"
                f"<div class='ph-card-sub'>{blurb}</div></div>",
                unsafe_allow_html=True,
            )
            if path in PAGES:
                st.page_link(PAGES[path], label=f"Open {title} →")

    _play(p)
    _on_the_way()
    _latest_article()


def _play(p):
    games = [g for g in GAMES if g[0] in PAGES]
    if not games:
        return
    st.markdown("<div class='ph-section'>Games</div>", unsafe_allow_html=True)
    cols = st.columns(len(games), gap="medium")
    for col, (path, title, blurb, cta, art) in zip(cols, games):
        with col, st.container(key=f"card_play_{path}"):
            if art == "bars":
                pic = "".join(f"<i style='background:{c};width:{w}%'></i>" for c, w in
                              [("#C08A2E", 92), ("#2F6FB0", 74), ("#8E5B9F", 66),
                               ("#5E9A62", 48), ("#2F8F9D", 37)])
            else:
                pic = ("<svg viewBox='0 0 300 76' width='100%' height='76' preserveAspectRatio='none'>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 L215,14 L0,14Z' "
                       f"fill='{p['game_fall']}' opacity='{p['game_fall_op']}'/>"
                       f"<line x1='0' x2='300' y1='14' y2='14' stroke='{p['base_line']}' stroke-dasharray='4 4'/>"
                       "<path d='M0,14 C40,16 55,52 80,64 S120,72 140,58 S190,20 215,15 S270,4 300,2' "
                       f"fill='none' stroke='{p['game_line']}' stroke-width='2.5'/></svg>")
            st.markdown(
                f"<div class='ph-game'><div class='ph-game-art'>{pic}</div>"
                f"<div class='ph-game-text'><div class='ph-meta'>Game</div>"
                f"<div class='ph-play-title'>{title}</div>"
                f"<div class='ph-play-sub'>{blurb}</div></div></div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES[path], label=f"{cta} →")


def _on_the_way():
    st.markdown("<div class='ph-section'>On the way</div>", unsafe_allow_html=True)
    cards = "".join(
        f"<div class='ph-soon'><span class='ph-soon-pill'>Soon</span>"
        f"<div><div class='ph-soon-title'>{t}</div><div class='ph-soon-sub'>{d}</div></div></div>"
        for t, d in SOON
    )
    st.markdown(f"<div class='ph-soon-row'>{cards}</div>", unsafe_allow_html=True)


def _latest_article():
    posts, _ = sb.load_posts()
    if not posts or "writing" not in PAGES:
        return
    post = posts[0]
    st.markdown("<div class='ph-section'>From my Substack</div>", unsafe_allow_html=True)
    with st.container(key="card_latest"):
        a, b = st.columns([1, 1.8], gap="large", vertical_alignment="center")
        with a:
            if post.cover:
                st.image(post.cover, width="stretch")
        with b:
            date = f"{post.date:%d %b %Y}" if post.date else ""
            st.markdown(
                f"<div class='ph-meta'>Latest · {date}</div>"
                f"<div class='ph-latest-title'>{post.title}</div>"
                f"<div class='ph-latest-sub'>{post.subtitle}</div>",
                unsafe_allow_html=True,
            )
            st.page_link(PAGES["writing"], label="Read the article →",
                         query_params={"post": post.slug})
