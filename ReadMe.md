# Findable

FastAPI service that takes a **URL**, fetches the page via **[Firecrawl](https://www.firecrawl.dev/)**, and returns the best signals for a **search-engine (SEO)** and **answer-engine / agent (AEO)** audit.

## Endpoints

| Method | Path      | Purpose |
|--------|-----------|---------|
| `GET`  | `/health` | Liveness + whether Firecrawl is configured. |
| `POST` | `/scrape` | Raw Firecrawl passthrough — send any `options` to experiment. |
| `POST` | `/audit`  | Opinionated, structured SEO + AEO report (scored). |
| —      | `/docs`   | Interactive Swagger UI. |

### `POST /audit`
```jsonc
// request
{ "url": "https://example.com", "wait_for": 0, "mobile": false, "include_screenshot": false }
```
Returns `overview`, a scored `seo` block, a scored `aeo` block (with detected
`structured_data_types`), and `links` stats. Each check has a
`status` (`pass` / `warn` / `fail` / `info`), a `detail`, and a `recommendation`.

### `POST /scrape`
```jsonc
// request
{ "url": "https://example.com", "options": { "formats": ["markdown", "links", "summary"], "onlyMainContent": true } }
```

## Firecrawl options (what to use for an audit)

`options` maps 1:1 to the Firecrawl scrape body. The ones that matter here:

| Option | What it gives you | Why it matters for SEO/AEO |
|--------|-------------------|----------------------------|
| `formats: ["rawHtml"]` | Untouched HTML | Full `<head>`: title, meta, canonical, robots, hreflang, **JSON-LD schema**, OG/Twitter tags. |
| `formats: ["markdown"]` | Clean, reader-mode text | **This is what an LLM agent actually reads** — measures real content depth. |
| `formats: ["links"]` | Every link on the page | Internal vs external link analysis. |
| `formats: ["summary"]` | Firecrawl's AI summary | Preview of what an answer engine might distil. |
| `formats: ["html"]` | Sanitised HTML | Lighter than rawHtml when you don't need `<head>`. |
| `formats: ["screenshot"]` | PNG (viewport / full page) | Visual/layout & mobile checks. |
| `formats: [{type:"json", schema, prompt}]` | LLM-extracted structured data | Pull FAQs, entities, prices, etc. on demand. |
| `onlyMainContent` | `true` strips nav/footer/ads | `true` for content depth; `false` to inspect boilerplate. |
| `waitFor` | ms to wait for JS | Bump it for client-rendered (React/Vue) pages. |
| `mobile` | Mobile viewport render | Audit mobile-first indexing. |
| `location` | `{country, languages}` | Audit the page as a local/geo user sees it. |
| `proxy` | `basic` / `stealth` / `auto` | `stealth` for bot-protected sites. |
| `includeTags` / `excludeTags` | Keep/drop selectors | Focus or clean the capture. |

`/audit` uses `["markdown", "rawHtml", "links", "summary"]` — the optimal set.

## Caching (Redis)

To avoid burning Firecrawl credits/tokens, every scrape is cached in Redis:

- The API **checks Redis first** (key = `sha256(url + options)`) and only calls
  Firecrawl on a miss. `/scrape` and `/audit` share the cache, and re-running an
  audit re-analyses cached HTML **without re-scraping**.
- Responses include a `"cached": true|false` flag. Send **`"refresh": true`** in
  the request body to bypass the cache and force a fresh scrape.
- If Redis is down the API still works — it just re-scrapes (logged as
  `cache_connected: false` on `/health`).
- **Persistence:** the `redis` service writes **RDB snapshots** to a named Docker
  volume (`redis-data`) and auto-loads `dump.rdb` on startup, so your cache
  **survives `docker compose down` / `up` and reboots** — no re-scraping after a
  restart. Snapshot policy: save after 60s if ≥1 key changed, or 300s if ≥10.

> ⚠️ `docker compose down -v` deletes the volume (and your cache). Use plain
> `docker compose down` to keep it.

Tune with `CACHE_ENABLED` and `CACHE_TTL_SECONDS` (`0` = never expire).

## Setup (uv)

```bash
uv sync                       # create .venv and install deps
cp .env.example .env          # then add your FIRECRAWL_API_KEY
uv run uvicorn app.main:app --reload --port 8000
# open http://localhost:8000/docs
```

## Run with Docker

```bash
cp .env.example .env          # add your FIRECRAWL_API_KEY
docker compose up --build     # serves on http://localhost:${APP_PORT:-8000}
```

## Configuration

All config is env-driven — see [`.env.example`](.env.example). Key vars:
`APP_PORT`, `CORS_ORIGINS`, `FIRECRAWL_API_KEY`, `FIRECRAWL_API_URL`,
`FIRECRAWL_API_VERSION`, `FIRECRAWL_TIMEOUT`, `REDIS_URL`, `CACHE_ENABLED`,
`CACHE_TTL_SECONDS`.

## Layout

```
app/
  main.py             FastAPI app + routes
  config.py           env-driven settings (pydantic-settings)
  schemas.py          request models + Firecrawl option mapping
  firecrawl_client.py async Firecrawl wrapper
  cache.py            Redis cache (check-first, graceful degradation)
  seo.py              SEO + AEO analysis / scoring
```
