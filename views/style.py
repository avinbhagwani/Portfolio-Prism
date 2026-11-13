"""
PRISM house style, injected once per run from app.py so every page
shares one set of type, spacing and widget rules. Page modules keep
only what is specific to them.

The look is "the observatory": the left navigation is the night sky
(views/sidebar.py) and the page is the logbook an observer writes in.

Design rules:
  * Light and minimal, navy ink and rust. Ink is the action colour;
    rust is kept for losses and warnings only.
  * Two voices. Inter does the work (titles, controls, tables, every
    number, the computed finding); IBM Plex Mono labels (the small mark
    above a title, section marks, the nav).
  * Every tool owns one spectral line: a colour that marks it in the
    navigation and above its page title. See LINES below.
  * Structure through space and hairlines: control panels sit on warm
    paper, results sit on white.
"""

import streamlit as st

INK = "#14212E"
MUTED = "#5F6975"
FAINT = "#959DA8"
LINE = "#E7E3DA"
MIST = "#F6F4EF"      # warm paper
NAVY = "#1F4E79"
RUST = "#B54A3C"
BRASS = "#B08A3E"

MONO = "'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, monospace"

# url_path -> (spectral line colour, index shown in the navigation)
LINES = {
    "home": ("#E9EEF4", ""),
    "factor-analysis": ("#5B93C7", "01"),
    "fbi-intelligence": ("#35A3A8", "02"),
    "drawdown-analysis": ("#C9604F", "03"),
    "efficient-frontier": ("#6BAA6E", "04"),
    "try-to-time": ("#D2A244", "05"),
    "can-you-handle-it": ("#A274B5", "06"),
    "writing": ("#9FB2C6", "07"),
}

CSS = f"""
<style>
:root {{
  --ink:{INK}; --muted:{MUTED}; --faint:{FAINT}; --line:{LINE};
  --mist:{MIST}; --navy:{NAVY}; --rust:{RUST}; --brass:{BRASS};
  --mono:{MONO};
}}

/* ---------- page frame ---------- */
[data-testid="stMain"] {{ position:relative; }}
[data-testid="stMainBlockContainer"] {{
  max-width:1120px; padding-top:3rem; padding-bottom:4.5rem;
}}
html, body, [data-testid="stApp"] {{ font-variant-numeric:tabular-nums; }}
::selection {{ background:#F1E3C4; color:var(--ink); }}

/* ---------- page header (shared by every tool) ----------
   mark:  a short spectral line in the tool's colour, then its name
   title: the question the page answers                              */
[data-testid="stMain"] .fbi-eyebrow, [data-testid="stMain"] .pw-eyebrow,
[data-testid="stMain"] .ph-section {{
  display:flex; align-items:center; gap:0.7rem;
  font-family:var(--mono); font-size:0.72rem; font-weight:500;
  letter-spacing:0.14em; text-transform:uppercase; color:var(--muted);
  margin:0 0 1.1rem 0;
}}
[data-testid="stMain"] .fbi-eyebrow::before, [data-testid="stMain"] .pw-eyebrow::before,
[data-testid="stMain"] .ph-section::before {{
  content:""; width:28px; height:2px; border-radius:2px; background:var(--tool, var(--brass));
}}
[data-testid="stMain"] .fbi-title, [data-testid="stMain"] .pw-title {{
  font-size:2.25rem; font-weight:600; color:var(--ink); line-height:1.12;
  letter-spacing:-0.025em; margin:0 0 0.55rem 0; max-width:40rem;
}}
[data-testid="stMain"] .fbi-sub, [data-testid="stMain"] .pw-sub {{
  font-size:1.02rem; line-height:1.6; color:var(--muted);
  margin:0 0 1.8rem 0; max-width:38rem;
}}

/* findings: the computed sentence that opens each result */
[data-testid="stMain"] .fbi-headline {{
  font-size:1.42rem; line-height:1.45; font-weight:400; color:var(--ink);
  letter-spacing:-0.012em; margin:1.7rem 0 0.7rem 0; padding-left:1.1rem;
  border-left:2px solid var(--tool, var(--brass)); max-width:46rem; text-wrap:pretty;
}}
[data-testid="stMain"] .fbi-headline b {{ font-weight:600; }}
[data-testid="stMain"] .fbi-label {{
  font-family:var(--mono); font-size:0.72rem; font-weight:500; letter-spacing:0.1em;
  text-transform:uppercase; color:var(--muted); margin:2.2rem 0 0.5rem 0;
}}
[data-testid="stMain"] .fbi-note {{
  font-size:0.86rem; line-height:1.5; color:var(--faint);
  margin:0.25rem 0 0 0; max-width:44rem;
}}
[data-testid="stMain"] .fbi-section {{ height:1px; background:var(--line); margin:3rem 0 0.2rem 0; }}
[data-testid="stMain"] .fbi-source {{
  font-family:var(--mono); font-size:0.72rem; color:var(--faint); margin-top:3rem;
}}

/* ---------- control panels: warm paper with a hairline ---------- */
[class*="st-key-controls"] {{
  background:var(--mist); border:1px solid var(--line); border-radius:12px;
  padding:18px 20px 20px 20px; gap:0.9rem;
}}
[class*="st-key-controls"] [data-testid="stWidgetLabel"] p {{
  font-family:var(--mono); font-size:0.7rem; font-weight:500; letter-spacing:0.08em;
  text-transform:uppercase; color:var(--muted);
}}
[class*="st-key-controls"] .react-aria-ComboBox > div,
[class*="st-key-controls"] [data-baseweb="input"],
[class*="st-key-controls"] [data-baseweb="select"] > div {{
  background:#fff !important;
}}

/* ---------- cards (home, writing): paper surface that lifts ---------- */
[class*="st-key-card_"] {{
  background:var(--mist); border:1px solid var(--line); border-radius:14px;
  padding:14px 16px 16px 16px;
  transition:transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}}
[class*="st-key-card_"]:hover {{
  transform:translateY(-2px); border-color:#D9D3C5;
  box-shadow:0 10px 24px -14px rgba(20,33,46,.28);
}}

/* ---------- inputs ---------- */
[data-testid="stWidgetLabel"] p {{ font-weight:500; }}
.react-aria-ComboBox > div {{
  border-radius:8px !important; border:1px solid var(--line) !important;
  box-shadow:none !important;
}}
.react-aria-ComboBox > div:focus-within {{ border-color:var(--ink) !important; }}

/* segmented controls: quiet track, ink when chosen */
[data-testid="stButtonGroup"] [role="radiogroup"],
[data-testid="stButtonGroup"] > div:last-child {{ gap:0 !important; }}
button[data-variant="segmented_control"] {{
  padding:0 0.8rem !important; border-color:var(--line) !important; color:var(--muted) !important;
  font-weight:500 !important; background:#fff !important;
  min-height:2.25rem !important; transition:background 120ms, color 120ms;
}}
button[data-variant="segmented_control"]:hover {{ color:var(--ink) !important; }}
button[data-variant="segmented_control"][aria-checked="true"],
button[data-variant="segmented_control"][data-selected="true"],
button[data-variant="segmented_control"][aria-pressed="true"] {{
  background:var(--ink) !important; border-color:var(--ink) !important;
  color:#fff !important;
}}
button[data-variant="segmented_control"][aria-checked="true"] p,
button[data-variant="segmented_control"][data-selected="true"] p,
button[data-variant="segmented_control"][aria-pressed="true"] p {{ color:#fff !important; }}

/* ---------- tabs ---------- */
div[data-testid="stTabs"] [role="tablist"] {{
  gap:1.8rem; border-bottom:1px solid var(--line);
}}
div[data-testid="stTab"] {{ padding:0.7rem 0 0.75rem 0; }}
div[data-testid="stTab"] p {{
  font-size:0.98rem !important; font-weight:500 !important; color:var(--faint) !important;
  transition:color 120ms;
}}
div[data-testid="stTab"]:hover p {{ color:var(--muted) !important; }}
div[data-testid="stTab"][aria-selected="true"] p {{ color:var(--ink) !important; }}

/* ---------- expanders ---------- */
[data-testid="stExpander"] details {{
  border:none !important; border-top:1px solid var(--line) !important;
  border-radius:0 !important;
}}
[data-testid="stExpander"] summary {{ padding-left:0 !important; }}
[data-testid="stExpander"] summary p {{ font-weight:500; color:var(--muted); }}

/* ---------- tables and number tiles ---------- */
[data-testid="stDataFrame"] {{ border-radius:10px; overflow:hidden; }}
.fa-table th, .dd-table th, .ef-table th {{
  font-family:var(--mono) !important; text-transform:uppercase !important;
  letter-spacing:0.07em !important; font-size:0.68rem !important;
  font-weight:500 !important; color:var(--muted) !important;
}}

/* KPI tiles: white, a hairline frame, and the series colour as a
   spectral line across the top */
[data-testid="stMain"] .kpi, [data-testid="stMain"] .ef-card, [data-testid="stMain"] .fa-card {{
  border:1px solid var(--line) !important; background:#fff !important;
  border-radius:12px !important; position:relative; overflow:hidden;
}}
[data-testid="stMain"] .kpi::before, [data-testid="stMain"] .ef-card::before {{
  content:""; position:absolute; left:0; right:0; top:0; height:3px; background:var(--c);
}}
[data-testid="stMain"] .ef-card {{ border-top:1px solid var(--line) !important; }}
.ef-card h4 {{ color:var(--ink) !important; }}
.kpi-meta {{ border-top:1px solid var(--line) !important; }}
/* ---------- buttons ---------- */
button[kind="primary"], button[data-testid="stBaseButton-primary"],
a[data-testid="stBaseLinkButton-primary"] {{
  background:var(--ink) !important; border-color:var(--ink) !important;
  border-radius:8px !important; transition:transform 120ms ease, background 120ms ease;
}}
button[data-testid="stBaseButton-primary"]:hover,
a[data-testid="stBaseLinkButton-primary"]:hover {{ background:#22364B !important; transform:translateY(-1px); }}
button[data-testid="stBaseButton-secondary"], a[data-testid="stBaseLinkButton-secondary"] {{
  border-radius:8px !important; border-color:#D9D3C5 !important;
}}

/* ---------- tour pill and tab links (views/tutorial.py) ---------- */
[class*="st-key-tutpill_"] {{ margin:-0.9rem 0 1.5rem 0; position:relative; }}
[class*="st-key-tutpill_"][class*="home"], [class*="st-key-tutpill_"][class*="try-to-time"],
[class*="st-key-tutpill_"][class*="can-you-handle-it"] {{ margin:0.3rem 0 0.6rem 0; }}
[class*="st-key-tutpill_"] button {{
  background:#fff !important; border:1px solid var(--line) !important; border-radius:999px !important;
  min-height:2rem !important; padding:0.25rem 0.95rem 0.25rem 0.75rem !important;
  transition:border-color 150ms ease, transform 150ms ease;
}}
[class*="st-key-tutpill_"] button:hover {{ border-color:var(--brass) !important; transform:translateY(-1px); }}
[class*="st-key-tutpill_"] button p {{ font-size:0.84rem !important; font-weight:500 !important; color:var(--ink) !important; }}
[class*="st-key-tutpill_"] button [data-testid="stIconMaterial"] {{ color:var(--brass) !important; font-size:1.05rem !important; }}
[class*="st-key-tutpill_new_"] button::after {{
  content:""; width:7px; height:7px; border-radius:50%; background:#C9A25A; margin-left:7px;
  animation:tutping 1.8s ease-in-out infinite;
}}
@keyframes tutping {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(201,162,90,.55); }} 60% {{ box-shadow:0 0 0 6px rgba(201,162,90,0); }} }}
[class*="st-key-tut_tab_"] {{ margin:0.4rem 0 -0.4rem 0; }}
[class*="st-key-tut_tab_"] button p {{ font-size:0.82rem !important; color:var(--faint) !important; }}
[class*="st-key-tut_tab_"] button:hover p {{ color:var(--ink) !important; }}
[class*="st-key-tut_tab_"] button [data-testid="stIconMaterial"] {{ color:var(--faint) !important; font-size:1rem !important; }}

/* ---------- dialogs ---------- */
div[role="dialog"] {{ border-radius:16px !important; }}

@media (prefers-reduced-motion: reduce) {{
  [class*="st-key-card_"], button {{ transition:none !important; }}
  [class*="st-key-card_"]:hover {{ transform:none; }}
}}

/* ---------- phones ---------- */
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-top:1.4rem; }}
  [data-testid="stMain"] .fbi-title, [data-testid="stMain"] .pw-title {{ font-size:1.7rem; }}
  [data-testid="stMain"] .fbi-sub, [data-testid="stMain"] .pw-sub {{ font-size:0.96rem; margin-bottom:1.3rem; }}
  [data-testid="stMain"] .fbi-headline {{ font-size:1.16rem; }}
  [class*="st-key-controls"] {{ padding:14px 14px 16px 14px; border-radius:12px; }}
  /* long button rows scroll sideways instead of being cut off */
  [data-testid="stButtonGroup"] [role="radiogroup"] {{
    overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none;
  }}
  div[data-testid="stTabs"] [role="tablist"] {{
    gap:1.2rem; overflow-x:auto; scrollbar-width:none;
  }}
}}
</style>
"""


def inject(page="home"):
    """Shared rules, plus the current page's spectral line as --tool."""
    colour = LINES.get(page, LINES["home"])[0]
    if page == "home":
        colour = BRASS
    st.markdown(CSS + f"<style>:root {{ --tool:{colour}; }}</style>",
                unsafe_allow_html=True)
