"""
PTCHP Social Listening Service — FastAPI app.

Endpoints
  GET  /api/mentions          recent mentions (filtered)
  GET  /api/mentions/stats    aggregate stats for dashboard panel
  GET  /api/mentions/stream   Server-Sent Events for live updates
  GET  /api/health            adapter status + last poll time
  POST /api/poll              trigger a poll cycle now (admin)

Run:  uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import asyncio
import logging
import os
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from models import Mention, MentionStats, Platform, Sentiment
from sentiment import enrich
from cache import store_mention, list_mentions, get_cache

from adapters import BaseAdapter
from adapters.x_adapter import XAdapter
from adapters.meta_adapter import FacebookAdapter, InstagramAdapter
from adapters.reddit_adapter import RedditAdapter
from adapters.rss_adapter import RssAdapter


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("ptchp")


# --- Configuration -------------------------------------------------------

KEYWORDS = [
    "RTA Dubai", "RTA", "Dubai bus", "Hala taxi", "Dubai taxi",
    "nol card", "Dubai abra", "Dubai metro feeder", "Dubai marine transport",
    "هيئة الطرق والمواصلات", "تاكسي دبي", "حافلات دبي",
]
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL", "60"))

ADAPTERS: list[BaseAdapter] = [
    XAdapter(),
    FacebookAdapter(),
    InstagramAdapter(),
    RedditAdapter(),
    RssAdapter(),
]


# --- Polling -------------------------------------------------------------

last_poll: dict[str, datetime] = {}
poll_errors: dict[str, str] = {}


async def poll_once() -> int:
    """Run one fetch cycle across all adapters. Returns count of new mentions."""
    since = datetime.now(timezone.utc) - timedelta(minutes=15)
    new_count = 0
    for adapter in ADAPTERS:
        if not adapter.is_configured():
            continue
        try:
            mentions = await adapter.fetch(KEYWORDS, since=since, limit=50)
            for m in mentions:
                m = await enrich(m)
                store_mention(m)
                new_count += 1
            last_poll[adapter.name] = datetime.now(timezone.utc)
            poll_errors.pop(adapter.name, None)
            log.info("Adapter %s: %d mentions", adapter.name, len(mentions))
        except Exception as e:  # noqa: BLE001
            poll_errors[adapter.name] = str(e)
            log.exception("Adapter %s failed", adapter.name)
    return new_count


async def poll_loop() -> None:
    while True:
        try:
            await poll_once()
        except Exception:  # noqa: BLE001
            log.exception("Poll cycle failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the scheduled poller alongside the API server."""
    if any(a.is_configured() for a in ADAPTERS):
        task = asyncio.create_task(poll_loop())
        log.info("Started social listener — polling every %ss", POLL_INTERVAL_SECONDS)
    else:
        task = None
        log.warning("No adapters configured — running in demo mode. "
                    "Use POST /api/seed-demo to populate sample mentions.")
    yield
    if task:
        task.cancel()


# --- App -----------------------------------------------------------------

app = FastAPI(title="PTCHP Social Listening Service", version="1.0.0", lifespan=lifespan)

# In production, restrict origins to the dashboard's domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Endpoints -----------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "adapters": [
            {
                "name": a.name,
                "configured": a.is_configured(),
                "lastPoll": last_poll.get(a.name).isoformat() if last_poll.get(a.name) else None,
                "lastError": poll_errors.get(a.name),
            }
            for a in ADAPTERS
        ],
        "pollIntervalSeconds": POLL_INTERVAL_SECONDS,
    }


@app.get("/api/mentions")
async def mentions(
    since: str = Query("60m", description="e.g. 30m, 2h, 24h"),
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    cutoff = _parse_since(since)
    items = list_mentions(since=cutoff, platform=platform, limit=limit)
    return {
        "since": cutoff.isoformat(),
        "count": len(items),
        "mentions": [m.to_dashboard_dict() for m in items],
    }


@app.get("/api/mentions/stats")
async def stats(window: str = "60m") -> MentionStats:
    cutoff = _parse_since(window)
    items = list_mentions(since=cutoff, limit=1000)

    by_platform = Counter(m.platform.value for m in items)
    by_sentiment = Counter(m.sentiment.value for m in items)
    by_service = Counter(m.service_match.value for m in items)

    avg = sum(m.sentiment_score for m in items) / len(items) if items else 0.0

    # Spike detection: negative-sentiment volume in last 15min vs previous hour
    last_15 = [m for m in items if (datetime.now(timezone.utc) - m.created_at).total_seconds() < 900]
    last_15_neg = sum(1 for m in last_15 if m.sentiment == Sentiment.NEGATIVE)
    spike = last_15_neg >= 5  # tunable threshold
    spike_reason = None
    if spike:
        kws = Counter(k for m in last_15 for k in m.matched_keywords)
        peak = kws.most_common(1)
        spike_reason = (
            f"{last_15_neg} negative mentions in 15 min" +
            (f" — peak topic: {peak[0][0]}" if peak else "")
        )

    return MentionStats(
        total=len(items),
        window_minutes=int((datetime.now(timezone.utc) - cutoff).total_seconds() / 60),
        by_platform=dict(by_platform),
        by_sentiment=dict(by_sentiment),
        by_service=dict(by_service),
        avg_sentiment=round(avg, 3),
        spike_alert=spike,
        spike_reason=spike_reason,
        last_updated=datetime.now(timezone.utc),
    )


@app.get("/api/mentions/stream")
async def stream():
    """Server-Sent Events — emits new mentions as they arrive."""
    async def event_gen():
        seen: set[str] = set()
        while True:
            items = list_mentions(limit=50)
            for m in items:
                if m.id in seen:
                    continue
                seen.add(m.id)
                yield f"event: mention\ndata: {_json(m.to_dashboard_dict())}\n\n"
            await asyncio.sleep(5)
    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/poll")
async def trigger_poll() -> dict:
    """Admin: force a fetch cycle now."""
    n = await poll_once()
    return {"newMentions": n}


@app.post("/api/seed-demo")
async def seed_demo() -> dict:
    """Insert a handful of plausible-looking mentions for local UI work.
    DOES NOT call any external API. Marks each mention with platform='reddit'
    or platform='news_rss' which require no live credentials."""
    from demo_seed import SAMPLE_MENTIONS
    n = 0
    for raw in SAMPLE_MENTIONS:
        m = Mention.model_validate(raw)
        m = await enrich(m)
        store_mention(m)
        n += 1
    return {"seeded": n}


# --- Helpers -------------------------------------------------------------

def _parse_since(s: str) -> datetime:
    if s.endswith("m"):
        delta = timedelta(minutes=int(s[:-1]))
    elif s.endswith("h"):
        delta = timedelta(hours=int(s[:-1]))
    elif s.endswith("d"):
        delta = timedelta(days=int(s[:-1]))
    else:
        raise HTTPException(400, "since must be like '30m', '2h', '7d'")
    return datetime.now(timezone.utc) - delta


def _json(obj) -> str:
    import json
    return json.dumps(obj, default=str)
