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

## Built on

FastAPI · Firecrawl · httpx · BeautifulSoup/lxml · Redis · uv · Docker

## Docs

- **[USAGE.md](USAGE.md)** — how to run, test, and curl the API
- **[VALIDATION.md](VALIDATION.md)** — how this maps to the architecture spec
- **[agents-seo-okf/](agents-seo-okf/index.md)** — the full system architecture

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
