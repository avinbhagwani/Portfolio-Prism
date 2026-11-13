"""
PRISM's left navigation, drawn as a night sky: the wordmark and byline,
then pages grouped into sections. Each page carries its own spectral
line (the colour that also marks its page title), a one-line purpose
and an index number. The active page's line is lit. A footer with
contact details is pinned to the bottom.

Links are st.page_link, so moving between pages is instant and keeps
the session (the intro does not replay).
"""

import streamlit as st

from core.substack import SUBSTACK_URL, tracked
from views.style import LINES


SECTIONS = [
    ("", [
        ("home", "Home", ":material/home:", "What PRISM is"),
    ]),
    ("Analyse", [
        ("factor-analysis", "Factor Analysis", ":material/insights:",
         "What drives a fund"),
        ("fbi-intelligence", "FBI Intelligence", ":material/query_stats:",
         "Compare factor indices"),
        ("drawdown-analysis", "Drawdown Analysis", ":material/trending_down:",
         "Falls and recoveries"),
        ("efficient-frontier", "Efficient Frontier", ":material/scatter_plot:",
         "Best risk-return mix"),
    ]),
    ("Games", [
        ("try-to-time", "Try to Time", ":material/sports_esports:",
         "Pick next year's winner"),
        ("can-you-handle-it", "Can You Handle It?", ":material/monitor_heart:",
         "Sit through a crash"),
    ]),
    ("Read", [
        ("writing", "Writing", ":material/edit_note:",
         "My Substack"),
    ]),
]
DISABLED = set()

BASE_CSS = """
<style>
/* the night sky: deep ink, a scatter of fixed stars, a faint nebula low down */
section[data-testid="stSidebar"] {
  border-right:none;
  background:
    radial-gradient(1px 1px at 22px 64px, rgba(255,255,255,.55) 50%, transparent 51%),
    radial-gradient(1px 1px at 236px 38px, rgba(255,255,255,.45) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 262px 212px, rgba(217,179,106,.7) 50%, transparent 51%),
    radial-gradient(1px 1px at 208px 318px, rgba(255,255,255,.35) 50%, transparent 51%),
    radial-gradient(1px 1px at 18px 402px, rgba(255,255,255,.3) 50%, transparent 51%),
    radial-gradient(1px 1px at 250px 468px, rgba(255,255,255,.4) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 30px 610px, rgba(159,192,222,.6) 50%, transparent 51%),
    radial-gradient(1px 1px at 190px 660px, rgba(255,255,255,.35) 50%, transparent 51%),
    radial-gradient(1px 1px at 270px 742px, rgba(255,255,255,.3) 50%, transparent 51%),
    radial-gradient(1px 1px at 96px 790px, rgba(255,255,255,.25) 50%, transparent 51%),
    radial-gradient(420px 300px at 0% 100%, rgba(53,163,168,.13), transparent 70%),
    radial-gradient(360px 280px at 110% 82%, rgba(162,116,181,.10), transparent 70%),
    linear-gradient(180deg, #0A1522 0%, #0C1A2A 100%);
}
section[data-testid="stSidebar"] > div {padding-top:0.4rem; background:transparent;}
[data-testid="stSidebarContent"] {background:transparent;}
[data-testid="stSidebarHeader"] {padding:1.5rem 1.5rem 0.2rem 1.5rem;}
[data-testid="stSidebarUserContent"] {padding:0 1.1rem 1.2rem 1.1rem;}
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
  min-height:calc(100vh - 120px); gap:0.2rem;}
[data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:last-child {
  margin-top:auto;}

/* byline tucked under the PRISM wordmark, aligned with its first letter */
.ps-by {font-family:'IBM Plex Mono', ui-monospace, monospace; color:#D9B36A;
  font-size:0.66rem; font-weight:400; letter-spacing:0.1em; text-transform:uppercase;
  margin:-1.5rem 0 1.7rem 44px; line-height:1;}

/* section mark: a mono label with a hairline running to the edge */
.ps-sec {display:flex; align-items:center; gap:0.7rem;
  font-family:'IBM Plex Mono', ui-monospace, monospace; color:#6C8299;
  font-size:0.64rem; font-weight:500; letter-spacing:0.16em; text-transform:uppercase;
  margin:1.6rem 0 0.7rem 0.4rem;}
.ps-sec::after {content:""; flex:1; height:1px; background:#1D3147;}

/* a page link: its spectral line, its name and purpose, its index */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  --c:#9FB2C6;
  display:grid; grid-template-columns:3px 1fr auto; column-gap:13px; row-gap:2px;
  align-items:center; padding:9px 10px 9px 6px; border-radius:8px;
  text-decoration:none; position:relative;
  transition:background 0.18s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
  background:linear-gradient(90deg, rgba(255,255,255,.055), rgba(255,255,255,0) 85%);}
/* the icon slot becomes the spectral line */
[data-testid="stSidebar"] [data-testid="stPageLink"] a > span:first-child {
  grid-column:1; grid-row:1 / span 2; width:3px; height:22px; border-radius:3px;
  background:var(--c); opacity:.85; font-size:0 !important; color:transparent !important;
  overflow:hidden; justify-self:center;
  transition:height 0.2s ease, opacity 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a > span:first-child * {
  display:none !important;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover > span:first-child {
  height:30px; opacity:.95;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,
[data-testid="stSidebar"] [data-testid="stPageLink"] a span[data-testid="stMarkdownContainer"] {
  color:#C9D4DF; font-size:0.92rem; font-weight:500; margin:0; line-height:1.2;
  transition:color 0.18s ease;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p {color:#FFFFFF;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a::after {
  grid-column:2; font-size:0.75rem; color:#6C8299; line-height:1.25;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a::before {
  grid-column:3; grid-row:1 / span 2;
  font-family:'IBM Plex Mono', ui-monospace, monospace; font-size:0.64rem;
  letter-spacing:0.06em; color:#44596F; transition:color 0.18s ease;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:focus-visible {
  outline:2px solid #D9B36A; outline-offset:2px;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-disabled="true"],
[data-testid="stSidebar"] [data-testid="stPageLink"] span[disabled] {opacity:0.55;}

.ps-foot {border-top:1px solid #1D3147; padding-top:1rem; margin-top:1.4rem;
  font-size:0.76rem; color:#6C8299; line-height:1.7;}
.ps-foot a {color:#B9CCDD; text-decoration:none; border-bottom:1px solid #2C445D;
  transition:color .15s ease, border-color .15s ease;}
.ps-foot a:hover {color:#fff; border-color:#D9B36A;}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stSidebar"] [data-testid="stPageLink"] a,
  [data-testid="stSidebar"] [data-testid="stPageLink"] a * {transition:none !important;}
}
</style>
"""


def _sel(path):
    # page links use relative hrefs; the default page's href is empty
    href = "" if path == "home" else path
    return f'[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{href}"]'


def _per_link_css(active):
    rules = []
    for _, items in SECTIONS:
        for path, _, _, desc in items:
            sel = _sel(path)
            colour, index = LINES.get(path, ("#9FB2C6", ""))
            rules.append(f'{sel} {{--c:{colour};}}')
            rules.append(f'{sel}::after {{content:"{desc}";}}')
            rules.append(f'{sel}::before {{content:"{index}";}}')
    a = _sel(active)
    rules.append(
        # the active page: its line lit and glowing, light spilling right
        f'{a} {{background:linear-gradient(90deg, color-mix(in srgb, var(--c) 20%, transparent),'
        f' rgba(255,255,255,0) 92%);}}'
        f'{a} > span:first-child {{height:32px; opacity:1;'
        f' box-shadow:0 0 12px 1px color-mix(in srgb, var(--c) 70%, transparent);}}'
        f'{a} p {{color:#FFFFFF; font-weight:600;}}'
        f'{a}::after {{color:#9FB2C6;}}'
        f'{a}::before {{color:var(--c);}}'
    )
    return "<style>" + "".join(rules) + "</style>"


def render(pages, active_path):
    """pages: {url_path: st.Page}; active_path: url_path of current page."""
    with st.sidebar:
        st.markdown(BASE_CSS + _per_link_css(active_path), unsafe_allow_html=True)
        st.markdown("<div class='ps-by'>by Avin Bhagwani</div>",
                    unsafe_allow_html=True)
        for title, items in SECTIONS:
            if title:
                st.markdown(f"<div class='ps-sec'>{title}</div>", unsafe_allow_html=True)
            for path, label, icon, _ in items:
                st.page_link(pages[path], label=label, icon=icon,
                             disabled=path in DISABLED, width="stretch")
        st.markdown(
            "<div class='ps-foot'>"
            "Questions, bugs or ideas?<br>"
            f"<a href='{tracked(SUBSTACK_URL, 'sidebar')}' target='_blank'>Substack</a>"
            " &nbsp;\u00b7&nbsp; "
            "<a href='https://www.linkedin.com/in/avinbhagwani69/' target='_blank'>LinkedIn</a>"
            " &nbsp;\u00b7&nbsp; <a href='mailto:avinbhagwani69@gmail.com'>Email</a>"
            "</div>",
            unsafe_allow_html=True,
        )
