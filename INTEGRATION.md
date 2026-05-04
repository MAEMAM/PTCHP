# PTCHP — Wiring the Dashboard to the Live Social Backend

This is a 5-minute setup guide. The dashboard is **already hooked up** — it just needs the backend endpoint reachable.

## How the connection works

The dashboard tries to reach the backend at startup. If the backend doesn't respond within 2.5 seconds, the dashboard silently falls back to embedded demo data and shows a `DEMO DATA · BACKEND OFFLINE` pill in the top-right of the social section. Once the backend is reachable, the pill turns green: `LIVE · N mentions`.

The dashboard re-polls every 30 seconds, so as soon as the backend comes online, the panel upgrades automatically.

## Step 1 — Run the backend

```bash
cd social-feed-service
pip install -r requirements.txt
cp .env.example .env
# (optional) fill in X / Meta / RSS credentials in .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

If you don't add any credentials, only the Reddit adapter polls (it requires no auth). To populate the dashboard immediately for a demo:

```bash
curl -X POST http://localhost:8000/api/seed-demo
```

## Step 2 — Point the dashboard at the backend

Open `PTCHP_Dashboard.html` and search for `PTCHP_SOCIAL_API`. It defaults to `http://localhost:8000`. To change it, set the variable **before** the dashboard's `<script>` tag, e.g.:

```html
<script>window.PTCHP_SOCIAL_API = "https://api.ptchp.rta.ae";</script>
```

(In production, you'd inject this via the deploy pipeline rather than editing the HTML.)

## Step 3 — CORS

The backend's `CORS_ORIGINS` env var defaults to `*` for development. For production, restrict it to the dashboard's origin:

```bash
CORS_ORIGINS=https://dashboard.ptchp.rta.ae
```

## Endpoints the dashboard uses

| Endpoint | Used for |
|---|---|
| `GET /api/mentions?since=4h&limit=50` | Mention feed |
| `GET /api/mentions/stats?window=4h` | Right-rail aggregates + spike alert |
| `GET /api/health` | (manual) check adapter status + last poll time |

## Going to production

1. **Container**: `Dockerfile` not included — three lines (`FROM python:3.12-slim`, copy, `uvicorn ...`).
2. **Secrets**: move `.env` values into AWS Secrets Manager / Doppler / Vault.
3. **Cache**: set `REDIS_URL=redis://...` so multiple workers share state.
4. **Sentiment**: switch `SENTIMENT_BACKEND=llm` and add `ANTHROPIC_API_KEY` to use Claude Haiku 4.5 instead of the lexicon. The plumbing is already in `sentiment.py` — just uncomment the SDK call.
5. **Auth**: the dashboard reads anonymous data, so the public `/api/mentions` endpoint is fine. Lock down `/api/poll` and `/api/seed-demo` behind a token.
6. **Observability**: each adapter logs poll latency and error rate via `logging` — pipe to CloudWatch / Datadog.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Pill stays grey ("Demo data") | Backend unreachable, CORS, or wrong URL | Check `/api/health` from the dashboard host. Confirm `CORS_ORIGINS` matches. |
| Pill green but feed empty | Adapters configured but Reddit got 403 / no other adapters set up | Run `POST /api/seed-demo` to verify pipeline; check `/api/health` for `lastError`. |
| Arabic mentions misclassified | Lexicon backend can only catch obvious negatives | Switch `SENTIMENT_BACKEND=llm` for nuanced AR scoring. |
| Same mention appears twice | Poller ran on overlapping windows; deduper TTL too short | Increase `MENTION_TTL_SECONDS` in `cache.py`. |
