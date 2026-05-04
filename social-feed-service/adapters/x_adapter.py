"""
X (Twitter) v2 Recent Search adapter.

Auth: OAuth 2.0 Bearer Token (App-only).
Endpoint: GET https://api.twitter.com/2/tweets/search/recent
Pricing: Basic tier — $200/mo for 10k posts/month. Pro tier — $5k/mo for 1M.
Docs:    https://docs.x.com/x-api/posts/recent-search
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from adapters import BaseAdapter
from models import Mention, Platform


X_BEARER = os.environ.get("X_BEARER_TOKEN")
X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class XAdapter(BaseAdapter):
    name = "x"
    rate_limit_per_minute = 60  # Basic tier — 60 req/15min, but we cap conservatively

    def is_configured(self) -> bool:
        return bool(X_BEARER)

    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        if not self.is_configured():
            # Return empty rather than crashing the poller — health endpoint
            # surfaces the misconfiguration separately.
            return []

        # Build the X query operator. Quote multi-word terms; OR-join.
        # Filter out retweets to reduce duplication; we'll add them back via
        # the Reddit-style "shares" engagement metric.
        terms = [f'"{k}"' if " " in k else k for k in keywords]
        query = "(" + " OR ".join(terms) + ") -is:retweet lang:en OR lang:ar"

        params = {
            "query": query,
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,public_metrics,lang,author_id,entities",
            "expansions": "author_id",
            "user.fields": "username,verified,public_metrics",
        }
        if since:
            # X requires RFC 3339 with Z suffix
            params["start_time"] = since.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        headers = {"Authorization": f"Bearer {X_BEARER}"}

        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(X_SEARCH_URL, params=params, headers=headers)
            if r.status_code == 429:
                # Rate limited — caller will see empty list this cycle and retry
                return []
            r.raise_for_status()
            data = r.json()

        users_by_id = {
            u["id"]: u for u in (data.get("includes", {}).get("users") or [])
        }

        out: list[Mention] = []
        for t in data.get("data") or []:
            user = users_by_id.get(t.get("author_id"), {})
            metrics = t.get("public_metrics", {})
            user_metrics = user.get("public_metrics", {})

            out.append(Mention(
                id=f"x:{t['id']}",
                platform=Platform.X,
                native_id=t["id"],
                url=f"https://x.com/{user.get('username','i')}/status/{t['id']}",
                author_handle=f"@{user.get('username')}" if user.get("username") else None,
                author_followers=user_metrics.get("followers_count", 0),
                author_verified=user.get("verified", False),
                text=t["text"],
                language=t.get("lang", "en")[:2],
                created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
                fetched_at=datetime.now(timezone.utc),
                likes=metrics.get("like_count", 0),
                shares=metrics.get("retweet_count", 0) + metrics.get("quote_count", 0),
                replies=metrics.get("reply_count", 0),
                reach_estimate=user_metrics.get("followers_count", 0),
            ))
        return out
