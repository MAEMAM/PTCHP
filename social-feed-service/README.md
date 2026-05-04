# PTCHP Social Listening Service

Backend service that aggregates customer feedback from public social media platforms, scores it, and exposes it to the PTCHP dashboard.

## Why a backend is required

Social media APIs **cannot** be called from a browser:

- **OAuth keys** would be exposed in client HTML
- **CORS** policies block direct calls
- **Rate limits** must be coordinated across users

This service holds the credentials, polls the platforms on a schedule, normalizes the data into a single `Mention` record shape, scores sentiment, and exposes one clean endpoint (`/api/mentions`) that the dashboard calls.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    PUBLIC SOCIAL PLATFORMS                    │
│   X/Twitter   ·   Meta (FB/IG)   ·   Reddit   ·   RSS/News   │
└────────┬─────────────┬─────────────┬─────────────┬───────────┘
         │             │             │             │
         ▼             ▼             ▼             ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ X        │ │ Meta     │ │ Reddit   │ │ RSS      │
   │ adapter  │ │ adapter  │ │ adapter  │ │ adapter  │
   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
        └────────────┴────────────┴────────────┘
                          │
                  ┌───────▼────────┐
                  │  Normalizer    │   → unified Mention schema
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  Sentiment     │   → AR/EN sentiment + emotion
                  │  Classifier    │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  Deduplicator  │   → merge cross-platform repeats
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  Cache (Redis) │   ← scheduled poller writes here
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  FastAPI       │   → /api/mentions
                  │  (this service)│   → /api/mentions/stats
                  └───────┬────────┘
                          │
                          ▼
                ┌─────────────────┐
                │  PTCHP          │
                │  Dashboard      │   (browser fetches every 30s)
                └─────────────────┘
```

## Data flow

1. **Scheduled poller** (every 60s) calls each adapter for new mentions matching RTA-related keywords/handles.
2. **Each adapter** authenticates with its own OAuth tokens, fetches recent posts, and returns a list of platform-native records.
3. **Normalizer** converts platform-specific shapes into a unified `Mention` model.
4. **Sentiment classifier** scores each mention (-1.0 to +1.0) and tags emotions.
5. **Deduplicator** merges cross-platform reposts (same content, multiple platforms).
6. **Cache** stores the rolling window (last 24h) in Redis — the API reads from cache, never hits social APIs on user requests.
7. **Dashboard** polls `/api/mentions` every 30s for the live panel.

## Production deployment

- AWS Lambda (or equivalent) for adapters — one Lambda per platform, scheduled by EventBridge
- ElastiCache Redis for the rolling window
- API Gateway → Lambda for the FastAPI endpoint
- Secrets Manager for OAuth tokens (rotated quarterly)
- CloudWatch for adapter error rates + sentiment-spike alerts
- Estimated monthly cost at RTA volume: ~$400–800 (X Basic tier dominates)

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app, endpoints, scheduler |
| `models.py` | Unified `Mention` schema |
| `sentiment.py` | AR/EN sentiment + emotion tagging |
| `cache.py` | Redis-backed cache (with in-memory fallback for dev) |
| `adapters/x_adapter.py` | X/Twitter v2 API |
| `adapters/meta_adapter.py` | Facebook + Instagram Graph API |
| `adapters/reddit_adapter.py` | Reddit (no auth required for public reads) |
| `adapters/rss_adapter.py` | News + Google Alerts RSS |
| `.env.example` | Required environment variables |
| `requirements.txt` | Python deps |

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in tokens
uvicorn main:app --reload --port 8000
```

Endpoints:

- `GET /api/mentions?since=30m&platform=x` — recent mentions
- `GET /api/mentions/stats` — counts, sentiment split, peak channel
- `GET /api/mentions/stream` — Server-Sent Events for true live updates
- `GET /api/health` — adapter status + last poll time
