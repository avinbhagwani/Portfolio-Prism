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
PUBLICATION = "Avin's Substack"

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
