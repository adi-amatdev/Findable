# Findable

> Can AI actually read, trust, and cite your website? Findable audits a page for
> the AI search era (ChatGPT, Claude, Perplexity, Gemini) — not just classic SEO.

Search is shifting from *links* to *answers*. Findable inspects a URL the way an
AI crawler sees it and turns it into hard, reproducible signals: what content is
blocked or hidden behind JavaScript, whether robots.txt lets AI bots in, how
strong the schema/structured data is, and who/what the page is actually about.

## What it does today

Given a URL, it runs a fully deterministic pipeline and returns a **`SiteFacts`**
snapshot — no LLM guesswork, same input always gives the same output:

```
POST /api/sitefacts {url}
   │  Firecrawl  → rendered HTML, markdown, links
   │  httpx      → raw HTML, robots.txt, sitemap.xml, llms.txt
   ▼
 SiteFacts  →  per-AI-bot robots access · JS-dependency ratio (raw vs rendered)
               · schema.org types · title/meta/canonical/headings · link graph
               · authorship · candidate entities
```

Results are cached in Redis by URL hash, so re-runs never re-crawl (no wasted
Firecrawl credits).

## Generate & inspect a SiteFacts object

**Where it's built:** `POST /api/sitefacts` → `SiteFactsPipeline.run()`
(`app/pipeline.py`) → `CrawlFetcher.crawl()` (`app/crawl/fetcher.py`, returns a
cached `RawCrawl`) → **`build_site_facts()`** (`app/extraction/extractor.py`) — the
deterministic parse that produces the object.

**Try it** (server running, `FIRECRAWL_API_KEY` set):

```bash
curl -sX POST http://localhost:8000/api/sitefacts \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.firecrawl.dev"}' | jq
```

Add `"refresh": true` to bypass the cache and re-crawl. No `jq`? Drop `| jq`.

**Is it deterministic?** The parse (`build_site_facts`) is a pure function — the
same crawled HTML always yields the same `SiteFacts` (there's a test for it).
Across fresh crawls only two fields move: `fetched_at` and `http.latency_ms` (plus
the page's own content if it changed). Each crawl is cached in Redis by URL hash,
so repeat calls return a **byte-identical** object until you pass `refresh: true`
(or the 7-day TTL lapses).

## Built on

FastAPI · Firecrawl · httpx · BeautifulSoup/lxml · Redis · uv · Docker

## Docs

- **[USAGE.md](USAGE.md)** — how to run, test, and curl the API
- **[VALIDATION.md](VALIDATION.md)** — how this maps to the architecture spec
- **[okf/](okf/index.md)** — the full system architecture

## Status

`SiteFacts` pipeline is **implemented and tested** (19 passing tests). The agent,
model-router, scoring, and aggregation layers are **scaffolded** on top of it —
see [VALIDATION.md](VALIDATION.md).

## Quickstart

```bash
uv sync --group dev
cp .env.example .env          # set FIRECRAWL_API_KEY
uv run uvicorn app.main:app --reload --port 8000   # → http://localhost:8000/docs
```
