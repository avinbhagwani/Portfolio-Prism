"""
Avin's Substack, read through its public RSS feed.

The feed carries every post's title, subtitle, date, cover image and
full HTML body, so PRISM can list and render articles without scraping.
If the feed is unreachable we fall back to Substack's public archive API
(titles and covers only; bodies are fetched per post on demand), and if
both fail the page shows a "read on Substack" link instead of an error.

Results are cached for an hour, so new posts show up on their own.
"""

import email.utils
import html
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests
import streamlit as st

SUBSTACK_URL = "https://avinb.substack.com"
FEED_URL = f"{SUBSTACK_URL}/feed"
SUBSCRIBE_URL = f"{SUBSTACK_URL}/subscribe"
EMBED_URL = f"{SUBSTACK_URL}/embed"
PUBLICATION = "my Substack"  # shown in the author's own voice

# For local testing without network: point this at a saved feed.xml
FEED_FILE_ENV = "PRISM_SUBSTACK_FEED_FILE"

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PRISM/1.0; +https://avinb.substack.com)"}
MIN_WORDS = 60  # hides placeholders like "Coming soon"


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    subtitle: str
    url: str
    date: object          # datetime
    cover: str
    body_html: str
    words: int

    @property
    def read_minutes(self):
        return max(1, round(self.words / 230))


def _strip_tags(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _slug(url):
    m = re.search(r"/p/([^/?#]+)", url or "")
    return m.group(1) if m else re.sub(r"\W+", "-", url or "post").strip("-")


def _parse_feed(xml_text):
    root = ET.fromstring(xml_text)
    posts = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        body = item.findtext("content:encoded", default="", namespaces=NS) or ""
        enclosure = item.find("enclosure")
        cover = enclosure.get("url", "") if enclosure is not None else ""
        if not cover:
            m = re.search(r'<img[^>]+src="([^"]+)"', body)
            cover = m.group(1) if m else ""
        pub = item.findtext("pubDate") or ""
        try:
            date = email.utils.parsedate_to_datetime(pub)
        except (TypeError, ValueError):
            date = None
        words = len(_strip_tags(body).split())
        posts.append(Post(
            slug=_slug(link),
            title=html.unescape((item.findtext("title") or "").strip()),
            subtitle=html.unescape(_strip_tags(item.findtext("description") or "")),
            url=link,
            date=date,
            cover=cover,
            body_html=body,
            words=words,
        ))
    return posts


def _from_archive_api():
    r = requests.get(f"{SUBSTACK_URL}/api/v1/archive",
                     params={"sort": "new", "limit": 24}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    posts = []
    for p in r.json():
        url = p.get("canonical_url") or f"{SUBSTACK_URL}/p/{p.get('slug', '')}"
        date = None
        if p.get("post_date"):
            try:
                from datetime import datetime
                date = datetime.fromisoformat(p["post_date"].replace("Z", "+00:00"))
            except ValueError:
                pass
        posts.append(Post(
            slug=p.get("slug") or _slug(url),
            title=p.get("title") or "",
            subtitle=p.get("subtitle") or p.get("description") or "",
            url=url,
            date=date,
            cover=p.get("cover_image") or "",
            body_html="",
            words=int(p.get("wordcount") or MIN_WORDS),
        ))
    return posts


@st.cache_data(ttl=3600, show_spinner=False)
def load_posts():
    """Newest first. Returns (posts, error_message_or_None)."""
    try:
        path = os.environ.get(FEED_FILE_ENV)
        if path:
            with open(path, encoding="utf-8") as fh:
                posts = _parse_feed(fh.read())
        else:
            r = requests.get(FEED_URL, headers=HEADERS, timeout=10)
            r.raise_for_status()
            posts = _parse_feed(r.text)
    except Exception as feed_error:
        try:
            posts = _from_archive_api()
        except Exception:
            return [], f"Couldn't reach the Substack feed ({type(feed_error).__name__})."
    posts = [p for p in posts if p.words >= MIN_WORDS and p.title]
    posts.sort(key=lambda p: (p.date is not None, p.date), reverse=True)
    return posts, None


@st.cache_data(ttl=3600, show_spinner=False)
def load_body(slug):
    """Full HTML for one post when the feed didn't include it."""
    r = requests.get(f"{SUBSTACK_URL}/api/v1/posts/{slug}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json().get("body_html") or ""


# ---------------------------------------------------------------------
# Preview and attribution
# ---------------------------------------------------------------------

UTM = {"utm_source": "prism", "utm_medium": "referral", "utm_campaign": "writing"}


def tracked(url, content=None):
    """Add utm tags so Substack's stats show traffic coming from PRISM."""
    from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query))
    q.update(UTM)
    if content:
        q["utm_content"] = content
    return urlunsplit(parts._replace(query=urlencode(q)))


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
         "meta", "source", "track", "wbr"}


def _top_level_blocks(body):
    """Split article HTML into its top-level elements (paragraphs, headings,
    image blocks, quotes, lists) without breaking any element in half."""
    from html.parser import HTMLParser

    line_starts = [0]
    for m in re.finditer("\n", body):
        line_starts.append(m.end())

    class Splitter(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.depth, self.start, self.ends = 0, 0, []

        def _offset(self):
            line, col = self.getpos()
            return line_starts[line - 1] + col

        def handle_starttag(self, tag, attrs):
            if self.depth == 0:
                self.start = self._offset()
            if tag not in _VOID:
                self.depth += 1
            elif self.depth == 0:
                self.ends.append((self.start, self._offset() + len(self.get_starttag_text())))

        def handle_endtag(self, tag):
            if tag in _VOID:
                return
            self.depth = max(0, self.depth - 1)
            if self.depth == 0:
                end = body.find(">", self._offset()) + 1
                self.ends.append((self.start, end))

    s = Splitter()
    s.feed(body)
    s.close()
    return [body[a:b] for a, b in s.ends if b > a]


def preview(body, share=0.33, min_words=120):
    """
    The opening of an article: whole top-level blocks until about `share`
    of the words (at least `min_words`), always ending on a text block.
    Returns (preview_html, remaining_words); remaining_words is 0 when the
    article is short enough to show in full.
    """
    blocks = _top_level_blocks(body) or [body]
    counts = [len(_strip_tags(b).split()) for b in blocks]
    total = sum(counts)
    target = max(min_words, int(total * share))
    if total <= target * 1.4:
        return body, 0
    taken, words = [], 0
    for block, n in zip(blocks, counts):
        taken.append(block)
        words += n
        if words >= target and n > 0:
            break
    while taken and len(_strip_tags(taken[-1]).split()) == 0:
        taken.pop()
    return "".join(taken), max(0, total - words)
