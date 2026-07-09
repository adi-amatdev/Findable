# Findable

> Can AI actually read, trust, and cite your website?

Findable audits a URL the way an AI crawler sees it — not classic SEO. It checks what content is JS-gated, which AI bots are blocked by robots.txt, how strong the schema markup is, and what the page is actually about.

## What it does

Given a URL, it runs a deterministic pipeline and returns a `SiteFacts` snapshot — same input, same output, no LLM guesswork:

```
POST /api/sitefacts {url}
   Firecrawl  → rendered HTML, markdown, links
   httpx      → raw HTML, robots.txt, sitemap.xml, llms.txt
   ↓
 SiteFacts  →  per-bot robots access · JS-dependency ratio · schema.org types
               title/meta/canonical · link graph · authorship · entities
```

Results are cached in Redis by URL hash — repeat calls never re-crawl.

Four agents then judge the `SiteFacts` and produce an `AuditReport` with an AI Readiness Score (0–100), before/after visibility estimates per AI model, and ranked findings.

## Quickstart

```bash
uv sync --group dev
cp .env.example .env      # set your API keys (see below)
uv run uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) or the frontend at [http://localhost:3000](http://localhost:3000).

## API keys

| Key | Where to get it | Required for |
|---|---|---|
| `FIRECRAWL_API_KEY` | [firecrawl.dev/app/api-keys](https://www.firecrawl.dev/app/api-keys) | `POST /api/sitefacts`, full audit |
| `FIREWORKS_KEY` | [fireworks.ai](https://fireworks.ai) | Cloud LLM fallback (optional) |
| `VLLM_URL` | Run `agents/jupyter_vllm_setup.py` on a GPU server | Heavy model inference (optional) |

Set them in `.env` — see `.env.example` for all options.

To run without any LLM (frontend demo only): set `MOCK_STREAM=true` in `.env`.

## Docker (full stack)

```bash
docker compose up --build
```

Starts: backend (8000), agents-api (8080), Redis, frontend (3000). Requires Ollama running locally for LLM calls.

## Docs

- [USAGE.md](USAGE.md) — run, test, curl
- [VALIDATION.md](VALIDATION.md) — architecture conformance map
- [okf/](okf/index.md) — full system architecture

## Stack

FastAPI · Next.js · Firecrawl · Ollama/vLLM · Fireworks · Redis · Docker · uv
