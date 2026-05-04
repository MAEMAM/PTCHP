"""
Meta (Facebook + Instagram) Graph API adapter.

Auth: long-lived Page Access Token (per-page) + App Review for relevant scopes.
Endpoint family: https://graph.facebook.com/v21.0
Important constraint: Meta only exposes posts/comments on Pages YOU own — for
listening to public mentions of your Page, use:
   - GET /{page-id}/tagged           (posts that tag the Page)
   - GET /{page-id}/posts/comments   (comments on your own posts)
   - Instagram: /{ig-user-id}/tags   (posts tagging your IG account)
For broader public listening, RTA would license a partner like Brandwatch
or Sprinklr who have firehose access; this adapter covers the owned-channel case.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from adapters import BaseAdapter
from models import Mention, Platform


META_GRAPH = "https://graph.facebook.com/v21.0"
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID    = os.environ.get("FB_PAGE_ID")
IG_USER_ID    = os.environ.get("IG_USER_ID")
IG_TOKEN      = os.environ.get("IG_ACCESS_TOKEN")  # often same as FB token


class FacebookAdapter(BaseAdapter):
    name = "facebook"
    rate_limit_per_minute = 200  # Graph API rate limits are app-level, generous

    def is_configured(self) -> bool:
        return bool(FB_PAGE_TOKEN and FB_PAGE_ID)

    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        if not self.is_configured():
            return []

        # Pull recent comments on the Page's own posts. Each comment is treated
        # as a public mention of the Page (RTA) for sentiment purposes.
        url = f"{META_GRAPH}/{FB_PAGE_ID}/posts"
        params = {
            "access_token": FB_PAGE_TOKEN,
            "fields": "id,message,created_time,permalink_url,"
                      "comments{id,message,created_time,from,like_count,permalink_url}",
            "limit": 25,
        }
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        out: list[Mention] = []
        for post in data.get("data", []):
            for comment in (post.get("comments", {}).get("data") or []):
                created = datetime.fromisoformat(comment["created_time"])
                if since and created < since:
                    continue
                text = comment.get("message", "")
                # Filter by keywords ourselves — Graph doesn't support text search on comments
                if keywords and not any(k.lower() in text.lower() for k in keywords):
                    # Still keep it if commenting on RTA's own page — those are by definition mentions
                    pass
                from_ = comment.get("from") or {}
                out.append(Mention(
                    id=f"facebook:{comment['id']}",
                    platform=Platform.FACEBOOK,
                    native_id=comment["id"],
                    url=comment.get("permalink_url"),
                    author_handle=from_.get("name"),
                    author_followers=0,  # not exposed for commenters by Graph API
                    text=text,
                    created_at=created,
                    fetched_at=datetime.now(timezone.utc),
                    likes=comment.get("like_count", 0),
                    shares=0,
                    replies=0,
                    reach_estimate=0,
                ))
                if len(out) >= limit:
                    return out
        return out


class InstagramAdapter(BaseAdapter):
    name = "instagram"
    rate_limit_per_minute = 200

    def is_configured(self) -> bool:
        return bool(IG_USER_ID and IG_TOKEN)

    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        if not self.is_configured():
            return []

        # Fetch IG media tagged with @rta_dubai (or whatever the IG handle is)
        url = f"{META_GRAPH}/{IG_USER_ID}/tags"
        params = {
            "access_token": IG_TOKEN,
            "fields": "id,caption,timestamp,permalink,like_count,comments_count,username",
            "limit": min(limit, 50),
        }
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        out: list[Mention] = []
        for post in data.get("data", []):
            created = datetime.fromisoformat(post["timestamp"])
            if since and created < since:
                continue
            out.append(Mention(
                id=f"instagram:{post['id']}",
                platform=Platform.INSTAGRAM,
                native_id=post["id"],
                url=post.get("permalink"),
                author_handle=f"@{post['username']}" if post.get("username") else None,
                text=post.get("caption", ""),
                created_at=created,
                fetched_at=datetime.now(timezone.utc),
                likes=post.get("like_count", 0),
                shares=0,
                replies=post.get("comments_count", 0),
                reach_estimate=0,
            ))
        return out
