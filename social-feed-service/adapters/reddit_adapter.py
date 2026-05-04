"""
Reddit adapter — public JSON endpoints, no auth needed for read-only.

Endpoint: https://www.reddit.com/r/{subreddit}/search.json
Rate limit: 60 req/min from a single User-Agent. Set REDDIT_USER_AGENT to a
descriptive string per Reddit API rules ("rta-ptchp/1.0 by u/yourname").

For higher volume or stable access, register a script app and use OAuth:
  https://www.reddit.com/prefs/apps
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from adapters import BaseAdapter
from models import Mention, Platform


REDDIT_UA = os.environ.get("REDDIT_USER_AGENT", "rta-ptchp/1.0 (PTCHP listener)")
SUBREDDITS = ["dubai", "uae", "Bahrain"]  # Bahrain occasionally mentions RTA Dubai


class RedditAdapter(BaseAdapter):
    name = "reddit"
    rate_limit_per_minute = 60

    def is_configured(self) -> bool:
        # Public endpoint — always considered configured.
        return True

    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        out: list[Mention] = []
        per_sub = max(limit // max(len(SUBREDDITS), 1), 5)

        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": REDDIT_UA},
        ) as c:
            for sub in SUBREDDITS:
                # Reddit search treats spaces as AND, so OR-join terms explicitly
                q = " OR ".join(f'"{k}"' if " " in k else k for k in keywords)
                params = {
                    "q": q,
                    "restrict_sr": "on",
                    "sort": "new",
                    "limit": per_sub,
                    "t": "day",
                }
                try:
                    r = await c.get(
                        f"https://www.reddit.com/r/{sub}/search.json",
                        params=params,
                    )
                    if r.status_code != 200:
                        continue
                    data = r.json()
                except (httpx.RequestError, ValueError):
                    continue

                for child in data.get("data", {}).get("children", []):
                    p = child["data"]
                    created = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
                    if since and created < since:
                        continue
                    text = (p.get("title") or "") + "\n" + (p.get("selftext") or "")
                    out.append(Mention(
                        id=f"reddit:{p['id']}",
                        platform=Platform.REDDIT,
                        native_id=p["id"],
                        url=f"https://www.reddit.com{p['permalink']}",
                        author_handle=f"u/{p['author']}" if p.get("author") else None,
                        author_followers=0,
                        text=text.strip(),
                        created_at=created,
                        fetched_at=datetime.now(timezone.utc),
                        likes=p.get("ups", 0),
                        shares=0,
                        replies=p.get("num_comments", 0),
                        reach_estimate=p.get("subreddit_subscribers", 0),
                    ))
                    if len(out) >= limit:
                        return out
        return out
