"""
PRISM house style, injected once per run from app.py so every page
shares one set of type, spacing and widget rules. Page modules keep
only what is specific to them.

Design rules (see README for the short version):
  * Light and minimal, navy and rust. Navy is the action and "better"
    colour; rust is kept for losses and warnings only.
  * One typeface (Inter), one type scale, tabular numbers everywhere.
  * Structure through space and surface, not boxes: control panels sit
    on a soft mist surface, results sit on white with no frame.
  * Sentence case throughout; no all-caps labels.
"""

import streamlit as st

INK = "#17212D"
MUTED = "#66707C"
FAINT = "#98A1AC"
LINE = "#E6EAEF"
MIST = "#F4F6F9"
NAVY = "#1F4E79"
RUST = "#B54A3C"

CSS = f"""
<style>
:root {{
  --ink:{INK}; --muted:{MUTED}; --faint:{FAINT}; --line:{LINE};
  --mist:{MIST}; --navy:{NAVY}; --rust:{RUST};
}}

/* ---------- page frame ---------- */
[data-testid="stMainBlockContainer"] {{
  max-width:1120px; padding-top:2.6rem; padding-bottom:4rem;
}}
html, body, [data-testid="stApp"] {{ font-variant-numeric:tabular-nums; }}

/* ---------- page header (shared by every tool) ---------- */
[data-testid="stMain"] .fbi-eyebrow, [data-testid="stMain"] .pw-eyebrow {{ display:none; }}
[data-testid="stMain"] .fbi-title, [data-testid="stMain"] .pw-title {{
  font-size:2.25rem; font-weight:600; color:var(--ink); line-height:1.12;
  letter-spacing:-0.025em; margin:0 0 0.55rem 0; max-width:40rem;
}}
[data-testid="stMain"] .fbi-sub, [data-testid="stMain"] .pw-sub {{
  font-size:1.02rem; line-height:1.55; color:var(--muted);
  margin:0 0 1.8rem 0; max-width:38rem;
}}

/* findings: the computed sentence that opens each result */
[data-testid="stMain"] .fbi-headline {{
  font-size:1.38rem; line-height:1.42; font-weight:400; color:var(--ink);
  letter-spacing:-0.012em; margin:1.6rem 0 0.5rem 0; max-width:46rem;
}}
[data-testid="stMain"] .fbi-headline b {{ font-weight:600; }}
[data-testid="stMain"] .fbi-label {{
  font-size:0.86rem; font-weight:500; color:var(--ink);
  margin:2rem 0 0.35rem 0;
}}
[data-testid="stMain"] .fbi-note {{
  font-size:0.86rem; line-height:1.5; color:var(--faint);
  margin:0.25rem 0 0 0; max-width:44rem;
}}
[data-testid="stMain"] .fbi-section {{ height:1px; background:var(--line); margin:3rem 0 0.2rem 0; }}
[data-testid="stMain"] .fbi-source {{ font-size:0.8rem; color:var(--faint); margin-top:3rem; }}

/* ---------- control panels ---------- */
[class*="st-key-controls"] {{
  background:var(--mist); border-radius:14px; padding:18px 20px 20px 20px;
  gap:0.9rem;
}}
[class*="st-key-controls"] [data-testid="stWidgetLabel"] p {{
  font-size:0.8rem; font-weight:500; color:var(--muted);
}}
[class*="st-key-controls"] .react-aria-ComboBox > div,
[class*="st-key-controls"] [data-baseweb="input"],
[class*="st-key-controls"] [data-baseweb="select"] > div {{
  background:#fff !important;
}}

/* ---------- cards (home, writing): mist surface, no frame ---------- */
[class*="st-key-card_"] {{
  background:var(--mist); border-radius:16px; padding:14px 16px 16px 16px;
  transition:background 150ms ease;
}}
[class*="st-key-card_"]:hover {{ background:#EDF1F5; }}

/* ---------- inputs ---------- */
[data-testid="stWidgetLabel"] p {{ font-weight:500; }}
.react-aria-ComboBox > div {{
  border-radius:9px !important; border:1px solid var(--line) !important;
  box-shadow:none !important;
}}
.react-aria-ComboBox > div:focus-within {{ border-color:var(--navy) !important; }}

/* segmented controls: quiet track, navy when chosen */
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
  background:var(--navy) !important; border-color:var(--navy) !important;
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
  font-size:1rem !important; font-weight:500 !important; color:var(--muted) !important;
}}
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
  text-transform:none !important; letter-spacing:0 !important;
  font-size:0.8rem !important; color:var(--muted) !important;
}}

/* KPI tiles: a mist surface and a series dot instead of a coloured frame */
.kpi, .ef-card, .fa-card {{
  border:none !important; background:var(--mist) !important;
  border-radius:14px !important;
}}
.kpi-name::before, .ef-card h4::before {{
  content:""; display:inline-block; width:9px; height:9px; border-radius:50%;
  background:var(--c); margin-right:8px; vertical-align:1px;
}}
.ef-card h4 {{ color:var(--ink) !important; }}
.kpi-meta {{ border-top:1px solid #E3E8EE !important; }}

/* ---------- buttons ---------- */
button[kind="primary"], button[data-testid="stBaseButton-primary"] {{
  background:var(--navy) !important; border-color:var(--navy) !important;
  border-radius:999px !important;
}}
button[data-testid="stBaseButton-secondary"] {{
  border-radius:999px !important; border-color:var(--line) !important;
}}

/* ---------- dialogs ---------- */
div[role="dialog"] {{ border-radius:18px !important; }}

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


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
