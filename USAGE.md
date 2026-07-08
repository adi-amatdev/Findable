# Usage

How to run, test, and call Findable. For what it is, see the [README](ReadMe.md).

## Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Firecrawl API key — get one at <https://www.firecrawl.dev/app/api-keys>
- Docker (optional, only for the containerized run)

## Setup

```bash
uv sync --group dev          # create .venv + install deps
cp .env.example .env         # then set FIRECRAWL_API_KEY=fc-...
```

## Run

**Local**
```bash
uv run uvicorn app.main:app --reload --port 8000
```

**Docker** (api + Redis, cache persists across restarts)
```bash
docker compose up --build
```

Then open the interactive docs at <http://localhost:8000/docs>.

## Test

```bash
uv run pytest -q             # 19 tests, fully offline (no network/key needed)
```

## Endpoints & curl

**Health**
```bash
curl http://localhost:8000/health
```

**`POST /api/sitefacts` — the main endpoint: URL → SiteFacts**
```bash
curl -X POST http://localhost:8000/api/sitefacts \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.firecrawl.dev"}'
```
Add `"refresh": true` to bypass the cache and re-crawl:
```bash
curl -X POST http://localhost:8000/api/sitefacts \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.firecrawl.dev", "refresh": true}'
```

**`POST /scrape` — raw Firecrawl passthrough (debug)**
```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.firecrawl.dev"}'
```

## Good to know

- **Firecrawl key is required** for `/api/sitefacts` and `/scrape` (it does the
  crawl). Tests don't need it — they run offline with a fake crawler.
- **Redis is optional locally** — if it's not running, the cache degrades to a
  miss and the pipeline still works (`docker compose` provides Redis for you).
- **Caching:** results are keyed by URL hash, so repeat calls don't re-crawl (no
  wasted Firecrawl credits). Use `"refresh": true` to force a fresh crawl.
- **Scope:** `/api/sitefacts` is the implemented pipeline. The agent, scoring,
  and aggregation layers are scaffolded — see [VALIDATION.md](VALIDATION.md).
