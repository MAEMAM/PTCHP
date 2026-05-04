"""
Cache for normalized mentions.

Production: Redis with TTL (24h rolling window).
Dev: in-memory dict — same interface, no infra required.
"""
from __future__ import annotations
import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from models import Mention


class _MemoryCache:
    """Dev-mode cache. Not threadsafe enough for production."""
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, dict]] = {}

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self._items[key] = (time.time() + ttl_seconds, value)

    def get(self, key: str) -> Optional[dict]:
        v = self._items.get(key)
        if not v:
            return None
        expires, payload = v
        if time.time() > expires:
            del self._items[key]
            return None
        return payload

    def scan_prefix(self, prefix: str) -> list[dict]:
        now = time.time()
        out = []
        for k, (exp, val) in list(self._items.items()):
            if exp < now:
                del self._items[k]
                continue
            if k.startswith(prefix):
                out.append(val)
        return out


class _RedisCache:
    """Production cache. Requires `redis` package + REDIS_URL env var."""
    def __init__(self, url: str) -> None:
        import redis  # type: ignore
        self.r = redis.Redis.from_url(url, decode_responses=True)

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self.r.setex(key, ttl_seconds, json.dumps(value, default=str))

    def get(self, key: str) -> Optional[dict]:
        v = self.r.get(key)
        return json.loads(v) if v else None

    def scan_prefix(self, prefix: str) -> list[dict]:
        out = []
        for k in self.r.scan_iter(match=f"{prefix}*", count=500):
            v = self.r.get(k)
            if v:
                out.append(json.loads(v))
        return out


# Singleton — built lazily so import-time doesn't require Redis.
_cache: Optional[object] = None


def get_cache():
    global _cache
    if _cache is not None:
        return _cache
    url = os.environ.get("REDIS_URL")
    _cache = _RedisCache(url) if url else _MemoryCache()
    return _cache


# --- Domain-level helpers used by main.py and the poller ----------------

MENTION_TTL_SECONDS = 24 * 3600  # 24h rolling window


def store_mention(m: Mention) -> None:
    key = f"mention:{m.id}"
    get_cache().set(key, m.model_dump(mode="json"), MENTION_TTL_SECONDS)


def list_mentions(
    since: Optional[datetime] = None,
    platform: Optional[str] = None,
    limit: int = 200,
) -> list[Mention]:
    raw = get_cache().scan_prefix("mention:")
    mentions = [Mention.model_validate(r) for r in raw]
    if since:
        mentions = [m for m in mentions if m.created_at >= since]
    if platform:
        mentions = [m for m in mentions if m.platform.value == platform]
    mentions.sort(key=lambda m: m.created_at, reverse=True)
    return mentions[:limit]
