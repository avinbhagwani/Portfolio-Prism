"""
PRISM's left navigation: a navy panel with the wordmark and byline,
pages grouped into sections (each with an icon tile and a one-line
description), a clear active state, a "coming soon" item, and a footer
with contact details pinned to the bottom.

Links are st.page_link, so moving between pages is instant and keeps
the session (the intro does not replay).
"""

import streamlit as st

from core.substack import SUBSTACK_URL, tracked


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
    ]),
    ("Read", [
        ("writing", "Writing", ":material/edit_note:",
         "My Substack"),
    ]),
    ("Coming soon", [
        ("efficient-frontier", "Efficient Frontier", ":material/scatter_plot:",
         "Best risk-return mix"),
    ]),
]
DISABLED = {"efficient-frontier"}

BASE_CSS = """
<style>
section[data-testid="stSidebar"] {border-right: none;}
section[data-testid="stSidebar"] > div {padding-top: 0.4rem;}
[data-testid="stSidebarHeader"] {padding: 1.4rem 1.4rem 0.2rem 1.4rem;}
[data-testid="stSidebarUserContent"] {padding: 0 1rem 1.2rem 1rem;}
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
  min-height: calc(100vh - 120px); gap: 0.45rem;}
[data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:last-child {
  margin-top: auto;}

/* byline tucked under the PRISM wordmark, aligned with its first letter */
.ps-by {color:#C9A25A; font-size:0.74rem; font-weight:500; letter-spacing:0.03em;
  margin:-1.55rem 0 1.5rem 44px; line-height:1;}
.ps-sec {color:#6F89A3; font-size:0.68rem; font-weight:600; letter-spacing:0.12em;
  text-transform:uppercase; margin:1.3rem 0 0.55rem 0.55rem;}

[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  display:grid; grid-template-columns: 34px 1fr; column-gap: 12px; row-gap: 1px;
  align-items:center; padding: 9px 10px; border-radius: 10px;
  border-left: 3px solid transparent; text-decoration:none;
  transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {background:#17324A;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a > span:first-child {
  grid-row: 1 / span 2; width:34px; height:34px; border-radius:9px;
  background:#1A3953; color:#9FC0DE !important; display:flex;
  align-items:center; justify-content:center; font-size:19px;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,
[data-testid="stSidebar"] [data-testid="stPageLink"] a span[data-testid="stMarkdownContainer"] {
  color:#E6ECF2; font-size:0.93rem; font-weight:500; margin:0; line-height:1.2;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a::after {
  grid-column: 2; font-size:0.76rem; color:#7F98B0; line-height:1.25;}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-disabled="true"],
[data-testid="stSidebar"] [data-testid="stPageLink"] span[disabled] {opacity:0.55;}

.ps-foot {border-top:1px solid #22405B; padding-top:1rem; margin-top:1.2rem;
  font-size:0.78rem; color:#7F98B0; line-height:1.55;}
.ps-foot a {color:#B9CCDD; text-decoration:none; border-bottom:1px solid #3A5874;}
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
            if path in DISABLED:
                rules.append(f'{sel}::after {{content:"{desc}";}}')
            else:
                rules.append(f'{sel}::after {{content:"{desc}";}}')
    a = _sel(active)
    rules.append(
        f'{a} {{background:#1C3D5A; border-left-color:#E0B15C;}}'
        f'{a} > span:first-child {{background:#E0B15C; color:#0F2436 !important;}}'
        f'{a} p {{color:#FFFFFF; font-weight:600;}}'
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
