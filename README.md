# PTCHP — Public Transport Customer Happiness Platform

RTA Dubai Innovation / Business Track submission · complete deliverable bundle.

## What's in this folder

```
PTCHP_Bundle/
├── README.md                       ← you are here
├── PTCHP_Pitch_Deck.pptx           ← 14-slide executive pitch deck
├── PTCHP_Dashboard.html            ← live operations dashboard (open in any browser)
├── INTEGRATION.md                  ← how to wire dashboard ↔ backend
├── system_architecture.svg         ← full PTCHP system architecture (6 layers)
├── database_schema.svg             ← entity-relationship diagram (15 tables)
├── architecture.svg                ← social listening data-flow detail
├── CRM_DAX_Measures.txt            ← Power BI DAX measure definitions
└── social-feed-service/            ← FastAPI backend for live social feeds
    ├── README.md
    ├── main.py
    ├── models.py
    ├── sentiment.py
    ├── cache.py
    ├── demo_seed.py
    ├── requirements.txt
    ├── .env.example
    └── adapters/
        ├── __init__.py
        ├── x_adapter.py            ← X (Twitter) v2 API
        ├── meta_adapter.py         ← Facebook + Instagram Graph API
        ├── reddit_adapter.py       ← Reddit (no auth)
        ├── rss_adapter.py          ← Google Alerts + UAE news RSS
        └── gtfs_adapter.py         ← Swiftly GTFS-rt for bus tracking
```

## Quick start

### 1. View the dashboard

Just open `PTCHP_Dashboard.html` in any modern browser. It works offline — Chart.js and all data are inlined. The social listening panel will show `DEMO DATA · BACKEND OFFLINE` until you start the backend (see step 3).

### 2. Open the deck

`PTCHP_Pitch_Deck.pptx` — 14 slides covering problem, solution, AI engine, personas, dashboard, CHI formula, KPIs, predictive analytics, governance, roadmap, and scoring criteria alignment.

### 3. (Optional) Run the live social backend

```bash
cd social-feed-service
pip install -r requirements.txt
uvicorn main:app --port 8000
# In another terminal, seed demo data so the dashboard has something to show:
curl -X POST http://localhost:8000/api/seed-demo
```

Refresh the dashboard. The pill in the social section turns green: `LIVE · 12 mentions`.

See `INTEGRATION.md` for production deployment details.

## What this delivers

| Layer | Asset | What it does |
|---|---|---|
| Customer-facing | `PTCHP_Dashboard.html` | Live ops dashboard with **real CRM data** (100,921 cases over 4 years) — KPIs, CHI, monthly trend, root-cause Pareto, hour×day heatmap, live case feed, **live social listening** |
| Executive | `PTCHP_Pitch_Deck.pptx` | 14-slide submission deck with the full pitch, scored against the track criteria |
| Backend | `social-feed-service/` | Production-shape FastAPI service: 4 platform adapters, AR/EN sentiment scoring, priority ranking, deduplication, cache, scheduled poller, health/stats/stream endpoints |
| Architecture | `architecture.svg` | One-page data-flow diagram of the social listening pipeline |
| Integration | `INTEGRATION.md` | 5-minute setup guide for connecting dashboard to backend, plus production notes (CORS, secrets, Redis, LLM sentiment, observability, cost) |

## Data sources

- **CRM cases (2023–2026)**: 100,921 real cases analyzed; the dashboard's KPIs, charts, and heatmap are computed from these. Sources: `2023-cases.xlsx`, `2024-cases.xlsx`, `2025-cases.xlsx`, `2026-cases.xlsx` (provided separately).
- **Live social mentions**: pulled by the backend from X, Facebook/Instagram, Reddit, and RSS feeds when credentials are configured. Falls back to a curated set of representative mentions when offline.

## Key numbers (from real CRM data)

| Metric | Value |
|---|---|
| Total cases analyzed | 100,921 |
| Period | Jan 2023 – Mar 2026 |
| SLA compliance | 99.2% |
| CSAT (post-resolution) | 89.1% |
| Median resolution time | 79 hours |
| Customer Happiness Index (composite) | 91.1 / 100 |
| Top complaint reason | Staff Conduct (22,701 cases) |
| Peak complaint moment | Thursday 15:00 — 856 complaints |
