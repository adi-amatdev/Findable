---
type: Service
title: Mock Stream Passthrough
status: implemented
description: A zero-cost development mode (MOCK_STREAM=true) that bypasses Firecrawl and agents entirely, substituting static fixtures and a timed SSE emitter so the frontend streaming UI can be built without consuming any API credits.
tags: [dev, testing, sse, streaming, mock]
timestamp: 2026-07-08T00:00:00Z
---

# Mock Stream Passthrough

`MOCK_STREAM=true` in the environment activates a passthrough inside the backend. No Firecrawl requests are made, no agents-api is contacted, and no LLM is called. The three streaming-related routes behave identically to their real counterparts from the frontend's perspective — same paths, same SSE wire format, same JSON shapes — but all data is static and all timing is simulated.

## Activation

Add to `.env` (or set the env var directly):

```
MOCK_STREAM=true
```

The field is `mock_stream: bool = False` in `Settings` (`app/config.py`). Default is `false` — production and staging are unaffected unless the flag is explicitly set.

## What changes when enabled

| Route | Real behaviour | Mock behaviour |
|---|---|---|
| `POST /api/audit/start` | Runs Firecrawl → SiteFacts pipeline, then POSTs to agents-api | Skips both; registers in-process queues, fires `run_mock_audit()` background task |
| `GET /agent/stream/{agent_id}` | Proxies SSE bytes from agents-api | Drains an in-process `asyncio.Queue` fed by the mock background task |
| `GET /api/audit/{audit_id}` | Proxies result from agents-api | Reads from in-process result dict; returns `202` until ~6 s, then the static report |

Both mock responses include `"mock": true` so callers can detect the mode.

## Implementation (`app/mock.py`)

A single module owns all mock state and data:

### In-process state

```python
_queues:  dict[str, asyncio.Queue]   # agent_id  -> event queue
_results: dict[str, dict | None]     # audit_id  -> report (None = still running)
```

Functions: `register_agent`, `get_queue`, `store_result`, `get_result`, `clear` (for tests).

### Static fixtures

- **`MOCK_SITEFACTS`** — a fully populated [SiteFacts](/data/site-facts.md) instance representing a realistic mid-scoring site: HTTP 200, robots.txt present (Google-Extended blocked), JS dependency ratio 0.59, no llms.txt, two structured-data schema types, no author byline.
- **`MOCK_REPORT`** — a hardcoded [AuditReport](/data/audit-report.md) dict: overall score 62, five findings (two crawlability, one content-signal, one structured-data, one entity-topic), visibility before/after for GPT / Claude / Perplexity / Gemini.

### Background task (`run_mock_audit`)

Fires four coroutines in parallel via `asyncio.gather`, one per agent. Each coroutine walks a per-agent phase schedule (list of `(delay_s, phase, detail, score)` tuples), sleeping between entries and putting the event JSON into the agent's queue. When all four finish, the static report is stored in `_results`.

### Phase timeline

| Agent | Phases emitted | Finishes at |
|---|---|---|
| `crawlability` | started → sub_agent_pass_1 → sub_agent_pass_2 → sub_agent_pass_3 → judgment_call → parsing_result → complete | ~5.5 s |
| `content_signal` | started → building_prompt → llm_call → parsing_result → complete | ~3.8 s |
| `structured_data` | started → building_prompt → llm_call → parsing_result → complete | ~2.5 s |
| `entity_topic` | started → building_prompt → llm_call → parsing_result → complete | ~4.2 s |

### Report timing

`_REPORT_DELAY` in `app/mock.py` controls when the mock report is stored (default **4.0 s**). The report must be stored before the frontend polls `GET /api/audit/{audit_id}` at ~5.5 s (when the last SSE `complete` event fires). If the frontend receives `202 {"status":"running"}` (report not ready yet), it retries up to 10 times at 1.5 s intervals.

### SSE generator (`sse_stream`)

```python
async def sse_stream(agent_id: str) -> AsyncIterator[bytes]:
```

Drains the agent's `asyncio.Queue` and yields standard SSE frames until the `None` sentinel arrives. Consumed directly by `GET /agent/stream/{agent_id}` in mock mode — no proxy hop, no network.

## What is NOT mocked

- `POST /api/sitefacts` — still runs the real pipeline (useful for pipeline-only testing).
- `POST /api/audit` — still calls agents-api (the blocking legacy path is untouched).
- `POST /scrape` — still hits Firecrawl.

Only the three SSE streaming routes are intercepted.

## Related

- [FastAPI Application Layer](/components/api.md) — where the mock branch lives in `routes.py`
- [Agent SSE Streaming](/components/streaming.md) — the real streaming infrastructure this mirrors
- [SiteFacts](/data/site-facts.md) — schema of `MOCK_SITEFACTS`
- [AuditReport](/data/audit-report.md) — schema of `MOCK_REPORT`
