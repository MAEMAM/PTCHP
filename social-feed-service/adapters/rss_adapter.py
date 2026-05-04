"""
RSS adapter — pulls customer feedback signal from:
  1. Google Alerts RSS feeds (set up at google.com/alerts → "Deliver to: RSS feed")
  2. UAE news outlet RSS (Khaleej Times, The National, Gulf News)
  3. Internal RTA WhatsApp Business feed exported as RSS by middleware

Why RSS matters: news mentions of incidents (e.g. "RTA bus accident on
Sheikh Zayed Road") must surface in the same listening pipeline as social
posts so ops sees the full picture.

No auth required for public RSS. For Google Alerts, the URL is the user-
specific feed URL emitted at setup time.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
import xml.etree.ElementTree as ET

import httpx

from adapters import BaseAdapter
from models import Mention, Platform


# Comma-separated list of RSS feed URLs in env. One Google Alert per feed.
RSS_FEEDS = [u.strip() for u in os.environ.get("RSS_FEEDS", "").split(",") if u.strip()]


class RssAdapter(BaseAdapter):
    name = "rss"
    rate_limit_per_minute = 30

    def is_configured(self) -> bool:
        return len(RSS_FEEDS) > 0

    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        if not self.is_configured():
            return []
        out: list[Mention] = []
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            for feed_url in RSS_FEEDS:
                try:
                    r = await c.get(feed_url)
                    if r.status_code != 200:
                        continue
                    root = ET.fromstring(r.text)
                except (httpx.RequestError, ET.ParseError):
                    continue

                # Handle both RSS 2.0 (<item>) and Atom (<entry>)
                items = root.findall(".//item") or root.findall(
                    ".//{http://www.w3.org/2005/Atom}entry"
                )

                for item in items:
                    title = (
                        _findtext(item, "title")
                        or _findtext(item, "{http://www.w3.org/2005/Atom}title")
                        or ""
                    )
                    desc = (
                        _findtext(item, "description")
                        or _findtext(item, "{http://www.w3.org/2005/Atom}summary")
                        or ""
                    )
                    link = (
                        _findtext(item, "link")
                        or _link_atom(item)
                        or ""
                    )
                    pub = (
                        _findtext(item, "pubDate")
                        or _findtext(item, "{http://www.w3.org/2005/Atom}published")
                    )
                    try:
                        created = parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
                    except (TypeError, ValueError):
                        created = datetime.now(timezone.utc)
                    if since and created < since:
                        continue

                    text = f"{title}\n{desc}".strip()
                    if keywords and not any(k.lower() in text.lower() for k in keywords):
                        continue

                    native_id = (link or title)[:200]
                    out.append(Mention(
                        id=f"rss:{abs(hash(native_id))}",
                        platform=Platform.NEWS_RSS,
                        native_id=native_id,
                        url=link,
                        author_handle=None,  # filled by feed source name in production
                        text=text,
                        created_at=created,
                        fetched_at=datetime.now(timezone.utc),
                        likes=0, shares=0, replies=0,
                        reach_estimate=50_000,  # rough average for UAE news outlet reach
                    ))
                    if len(out) >= limit:
                        return out
        return out


def _findtext(el, tag) -> Optional[str]:
    n = el.find(tag)
    return (n.text or "").strip() if n is not None and n.text else None


def _link_atom(el) -> Optional[str]:
    n = el.find("{http://www.w3.org/2005/Atom}link")
    return n.attrib.get("href") if n is not None else None
