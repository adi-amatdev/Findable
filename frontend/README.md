# Findable - Frontend

Minimal Next.js (App Router) UI for the Findable backend. Enter a URL, it calls
`POST /api/sitefacts` and renders the **SiteFacts** as a clean panel dashboard -
AI-crawler access, JS-dependency, structured data, meta, links, authorship,
sitemap/llms.txt, entities.

No chart libraries, no CSS framework - plain CSS, deliberately non-bloat.

> The audit dashboard (score, radar, knowledge graph) and live SSE streaming are
> planned; only the implemented `/api/sitefacts` route is wired today.
> See `../agents-seo-okf/components/frontend.md`.

## Requirements

- **Node 18+ recommended.** Pinned to **Next.js 13.5** so it also runs on Node 16.
- The backend running (default `http://localhost:8000`).

## Setup

```bash
npm install
cp .env.local.example .env.local     # set NEXT_PUBLIC_API_BASE_URL if not localhost:8000
npm run dev                          # http://localhost:3000
```

Build / serve:

```bash
npm run build && npm start
```

## Config

- `NEXT_PUBLIC_API_BASE_URL` - backend base URL (default `http://localhost:8000`).

The backend enables permissive CORS, so the dev server on `:3000` can call it on
`:8000` directly.
