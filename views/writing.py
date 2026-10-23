"""
Writing: Avin's Substack inside PRISM.

List view   featured latest article, the rest as a card grid, subscribe.
Reader view ?post=<slug>: the opening third of the article with images,
            then "Continue reading on Substack" (so every read counts in
            Substack's stats; links carry utm_source=prism), a subscribe box, a "try it in
            PRISM" prompt when the article relates to one of the tools,
            and more articles.

Each article has its own URL inside PRISM (?post=...), so it can be
shared directly.
"""

import streamlit as st

from core import substack as sb

# Set by app.py so the reader can link to related tools
PAGES = {}

RELATED = [
    (("fama", "factor analysis", "factor model"), "factor-analysis",
     "Run a factor analysis on any Indian mutual fund",
     "See what really drives a fund's returns with the same Fama-French method."),
    (("nifty", "factor index", "smart beta", "momentum"), "fbi-intelligence",
     "Compare factor indices in FBI Intelligence",
     "Returns, risk and consistency for every Nifty factor and strategy index."),
]

CSS = """
<style>
.pw-eyebrow {font-size:0.78rem; letter-spacing:0.08em; text-transform:uppercase;
  color:#1F4E79; font-weight:600; margin:0 0 0.35rem 0;}
.pw-title {font-size:2.1rem; font-weight:600; color:#1B2533; line-height:1.15;
  margin:0 0 0.5rem 0; letter-spacing:-0.01em;}
.pw-sub {color:#6B7480; font-size:1rem; margin:0 0 1.2rem 0; max-width:44rem;}
.pw-meta {font-size:0.8rem; color:#8A939E; letter-spacing:0.02em; margin:0 0 0.35rem 0;}
.pw-card-title {font-size:1.12rem; font-weight:600; color:#1B2533; line-height:1.3;
  margin:0.2rem 0 0.35rem 0;}
.pw-card-sub {font-size:0.92rem; color:#6B7480; line-height:1.5; margin:0 0 0.6rem 0;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;}
.pw-feat-title {font-size:1.7rem; font-weight:600; color:#1B2533; line-height:1.2;
  margin:0.3rem 0 0.6rem 0; letter-spacing:-0.01em;}
.pw-feat-sub {font-size:1.02rem; color:#4A5562; line-height:1.55; margin:0 0 1rem 0;}
.pw-pill {display:inline-block; background:#FBF3E4; color:#9A6B1E; font-size:0.72rem;
  font-weight:600; letter-spacing:0.06em; text-transform:uppercase; padding:3px 9px;
  border-radius:999px; margin-bottom:0.4rem;}
.pw-section {font-size:0.82rem; color:#6B7480; font-weight:500; margin:2.2rem 0 0.6rem 0;}
.pw-a-title {font-size:2.4rem; font-weight:700; color:#1B2533; line-height:1.15;
  letter-spacing:-0.015em; margin:0.6rem 0 0.6rem 0; max-width:46rem;}
.pw-a-sub {font-size:1.2rem; color:#4A5562; line-height:1.5; margin:0 0 1rem 0; max-width:46rem;}
.pw-byline {font-size:0.9rem; color:#6B7480; margin:0 0 1.2rem 0;}
.pw-byline b {color:#1B2533; font-weight:600;}
.pw-cta {border:1px solid #E6E9ED; border-left:3px solid #C08A2E; border-radius:10px;
  padding:16px 20px; background:#FFFBF4; margin:1.6rem 0 0.6rem 0;}
.pw-cta b {display:block; color:#1B2533; font-size:1rem; margin-bottom:2px;}
.pw-cta span {color:#6B7480; font-size:0.9rem;}
.pw-continue {border:1px solid #E6E9ED; border-radius:14px; padding:22px 24px 6px 24px;
  margin:0.4rem 0 0.8rem 0; max-width:46rem;
  background:linear-gradient(180deg, #FFFFFF 0%, #F7F9FB 100%);}
.pw-continue-meta {font-size:0.78rem; color:#9A6B1E; font-weight:600; letter-spacing:0.04em;
  text-transform:uppercase; margin-bottom:4px;}
.pw-continue-title {font-size:1.35rem; font-weight:600; color:#1B2533; margin-bottom:4px;}
.pw-continue-sub {font-size:0.95rem; color:#6B7480; margin-bottom:12px;}
.pw-empty {border:1px dashed #D5DAE0; border-radius:12px; padding:28px; text-align:center;
  color:#6B7480;}
</style>
"""

ARTICLE_CSS = """
<style>
.pw-article {max-width: 46rem; font-family: Inter, sans-serif; color: #1B2533;
  font-size: 1.08rem; line-height: 1.75;}
.pw-article p {margin: 0 0 1.15em 0;}
.pw-article.pw-fade {position: relative; max-height: none;}
.pw-article.pw-fade::after {content: ""; position: absolute; left: 0; right: 0; bottom: 0;
  height: 140px; pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #FFFFFF 92%);}
.pw-article img.pw-cover {margin: 0 0 1.6em 0; width: 100%;}
.pw-article h1, .pw-article h2, .pw-article h3, .pw-article h4 {
  font-weight: 650; line-height: 1.3; margin: 1.8em 0 0.6em 0; color: #1B2533;}
.pw-article h2 {font-size: 1.5rem;} .pw-article h3 {font-size: 1.25rem;}
.pw-article a {color: #1F4E79; text-decoration: underline; text-underline-offset: 2px;}
.pw-article img {max-width: 100%; height: auto; border-radius: 10px; display: block;
  margin: 0.4em auto;}
.pw-article figure, .pw-article .captioned-image-container {margin: 1.6em 0;}
.pw-article figcaption, .pw-article .image-caption {font-size: 0.86rem; color: #8A939E;
  text-align: center; margin-top: 0.5em;}
.pw-article blockquote {border-left: 3px solid #C08A2E; margin: 1.4em 0; padding: 0.2em 0 0.2em 1.1em;
  color: #4A5562; font-style: italic;}
.pw-article ul, .pw-article ol {padding-left: 1.4em; margin: 0 0 1.15em 0;}
.pw-article li {margin: 0.3em 0;}
.pw-article table {border-collapse: collapse; width: 100%; font-size: 0.95rem; margin: 1.2em 0;}
.pw-article th, .pw-article td {border-bottom: 1px solid #E6E9ED; padding: 0.5em 0.6em; text-align: left;}
.pw-article pre, .pw-article code {background: #F4F6F8; border-radius: 6px; font-size: 0.9em;}
.pw-article pre {padding: 0.8em 1em; overflow-x: auto;}
.pw-article hr {border: none; border-top: 1px solid #E6E9ED; margin: 2em 0;}
.pw-article .subscription-widget-wrap, .pw-article .subscription-widget,
.pw-article .button-wrapper, .pw-article .image-link-expand,
.pw-article [class*="subscribe"] {display: none !important;}
</style>
"""


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    posts, error = sb.load_posts()
    slug = st.query_params.get("post")
    post = next((p for p in posts if p.slug == slug), None) if slug else None
    if post:
        _reader(post, posts)
    else:
        _list(posts, error)


def _meta(p):
    date = f"{p.date:%d %b %Y}" if p.date else ""
    return " · ".join(x for x in [date, f"{p.read_minutes} min read"] if x)


def _open(slug):
    st.query_params["post"] = slug


def _close():
    st.query_params.clear()


# ---------------------------------------------------------------------
# List
# ---------------------------------------------------------------------

def _list(posts, error):
    st.markdown(
        "<div class='pw-eyebrow'>Writing</div>"
        "<div class='pw-title'>Articles by Avin Bhagwani</div>"
        "<div class='pw-sub'>Essays on factor investing and markets, the thinking "
        f"behind PRISM. Published on {sb.PUBLICATION}.</div>",
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1.3, 1.3, 4])
    c1.link_button("Subscribe free", sb.tracked(sb.SUBSCRIBE_URL, "list-subscribe"), type="primary",
                   icon=":material/mail:", width="stretch")
    c2.link_button("Open Substack", sb.tracked(sb.SUBSTACK_URL, "list-open"), icon=":material/open_in_new:",
                   width="stretch")

    if not posts:
        st.markdown(
            "<div class='pw-empty'>Articles couldn't be loaded just now. "
            f"You can read them on <a href='{sb.tracked(sb.SUBSTACK_URL, 'empty')}' target='_blank'>"
            f"{sb.PUBLICATION}</a>.</div>",
            unsafe_allow_html=True,
        )
        return

    st.write("")
    first, rest = posts[0], posts[1:]
    with st.container(border=True):
        a, b = st.columns([1.15, 1], gap="large", vertical_alignment="center")
        with a:
            if first.cover:
                st.image(first.cover, width="stretch")
        with b:
            st.markdown(
                "<span class='pw-pill'>Latest</span>"
                f"<div class='pw-meta'>{_meta(first)}</div>"
                f"<div class='pw-feat-title'>{first.title}</div>"
                f"<div class='pw-feat-sub'>{first.subtitle}</div>",
                unsafe_allow_html=True,
            )
            st.button("Read article", key=f"read_{first.slug}", type="primary",
                      icon=":material/arrow_forward:", icon_position="right",
                      on_click=_open, args=(first.slug,))

    if rest:
        st.markdown("<div class='pw-section'>More articles</div>", unsafe_allow_html=True)
        for i in range(0, len(rest), 2):
            cols = st.columns(2, gap="medium")
            for col, p in zip(cols, rest[i:i + 2]):
                with col, st.container(border=True):
                    if p.cover:
                        st.image(p.cover, width="stretch")
                    st.markdown(
                        f"<div class='pw-meta'>{_meta(p)}</div>"
                        f"<div class='pw-card-title'>{p.title}</div>"
                        f"<div class='pw-card-sub'>{p.subtitle}</div>",
                        unsafe_allow_html=True,
                    )
                    st.button("Read", key=f"read_{p.slug}", icon=":material/arrow_forward:",
                              icon_position="right", on_click=_open, args=(p.slug,))

    _subscribe_box("Get new articles by email")


# ---------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------

def _reader(post, posts):
    st.button("All articles", icon=":material/arrow_back:", type="tertiary",
              on_click=_close)
    st.markdown(
        "<div class='pw-meta'>MY SUBSTACK</div>"
        f"<div class='pw-a-title'>{post.title}</div>"
        f"<div class='pw-a-sub'>{post.subtitle}</div>"
        f"<div class='pw-byline'><b>Avin Bhagwani</b> · {_meta(post)}</div>",
        unsafe_allow_html=True,
    )

    body = post.body_html
    if not body:
        try:
            body = sb.load_body(post.slug)
        except Exception:
            body = ""
    if not body:
        st.info("This article couldn't be loaded here. Read it on Substack instead.")
    else:
        # Show the cover inside the article column unless the body already
        # opens with the same image
        cover_id = post.cover.rsplit("/", 1)[-1][:40] if post.cover else ""
        cover = (f"<img class='pw-cover' src='{post.cover}' alt=''>"
                 if post.cover and cover_id not in body else "")
        # Preview only: the full article is read on Substack, so every read
        # counts in Substack's stats and readers can like, comment and subscribe
        excerpt, remaining = sb.preview(body)
        fade = " pw-fade" if remaining else ""
        st.html(ARTICLE_CSS
                + f"<article class='pw-article{fade}'>{cover}{excerpt}</article>")
    _continue_card(post, remaining if body else post.words)

    _related_tool(post)

    others = [p for p in posts if p.slug != post.slug][:3]
    if others:
        st.markdown("<div class='pw-section'>More articles</div>", unsafe_allow_html=True)
        cols = st.columns(len(others), gap="medium")
        for col, p in zip(cols, others):
            with col, st.container(border=True):
                if p.cover:
                    st.image(p.cover, width="stretch")
                st.markdown(
                    f"<div class='pw-meta'>{_meta(p)}</div>"
                    f"<div class='pw-card-title'>{p.title}</div>",
                    unsafe_allow_html=True,
                )
                st.button("Read", key=f"more_{p.slug}", icon=":material/arrow_forward:",
                          icon_position="right", on_click=_open, args=(p.slug,))


def _continue_card(post, remaining_words):
    minutes = max(1, round(remaining_words / 230)) if remaining_words else 0
    left = f"{minutes} more min" if minutes else "Full article"
    st.markdown(
        "<div class='pw-continue'>"
        f"<div class='pw-continue-meta'>{left} · on Substack</div>"
        "<div class='pw-continue-title'>Continue reading on Substack</div>"
        "<div class='pw-continue-sub'>Read the rest, then like, comment or "
        "subscribe to get the next one by email.</div></div>",
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1.7, 1.2, 3])
    c1.link_button("Continue reading", sb.tracked(post.url, "continue"),
                   type="primary", icon=":material/arrow_outward:",
                   width="stretch")
    c2.link_button("Subscribe", sb.tracked(sb.SUBSCRIBE_URL, "reader-subscribe"),
                   icon=":material/mail:", width="stretch")


def _related_tool(post):
    text = f"{post.title} {post.subtitle}".lower()
    for keywords, path, headline, blurb in RELATED:
        if any(k in text for k in keywords) and path in PAGES:
            st.markdown(f"<div class='pw-cta'><b>Try it in PRISM: {headline}</b>"
                        f"<span>{blurb}</span></div>", unsafe_allow_html=True)
            st.page_link(PAGES[path], label="Open the tool", icon=":material/arrow_forward:")
            return


def _subscribe_box(heading):
    st.markdown(f"<div class='pw-section'>{heading}</div>", unsafe_allow_html=True)
    st.iframe(sb.EMBED_URL, height=300)
