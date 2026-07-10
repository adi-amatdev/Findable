# Usage

How to run, test, and call Findable. For what it is, see the [README](ReadMe.md).

## Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Docker (for the full stack)
- Ollama running locally (for LLM calls)

## API keys

Copy `.env.example` to `.env`, then fill in:

```bash
cp .env.example .env
```

| Variable | Where to get it | Notes |
|---|---|---|
| `FIRECRAWL_API_KEY` | [firecrawl.dev/app/api-keys](https://www.firecrawl.dev/app/api-keys) | Required for crawling |
| `FIREWORKS_KEY` | [fireworks.ai](https://fireworks.ai) | Optional cloud LLM fallback |
| `VLLM_URL` | Run `agents/jupyter_vllm_setup.py` on a GPU server | Optional heavy model inference |
| `OLLAMA_URL` | Default `http://host.docker.internal:11434` | Local light model - needs Ollama running |

To skip all external services (frontend demo): set `MOCK_STREAM=true`.

## Run

**Local (backend only)**
```bash
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
```

**Full stack (backend + agents-api + Redis + frontend)**
```bash
docker compose up --build
```

Services: backend at `:8000`, agents-api at `:8080`, frontend at `:3000`.

**Frontend only**
```bash
cd frontend && npm install && npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local`.

## Test

```bash
uv run pytest -q    # 19 tests, fully offline - no keys needed
```

## Endpoints

**Health**
```bash
curl http://localhost:8000/health
```

**`POST /api/sitefacts` - URL to SiteFacts**
```bash
curl -X POST http://localhost:8000/api/sitefacts \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Add `"refresh": true` to bypass the cache.

**`POST /api/audit` - full audit (blocking)**
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**`POST /api/audit/start` - async audit with SSE streaming**
```bash
# Returns {audit_id, agent_ids} immediately; subscribe to streams per agent
curl -X POST http://localhost:8000/api/audit/start \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**`GET /agent/stream/{agent_id}` - live agent SSE stream**
```bash
curl -N http://localhost:8000/agent/stream/<agent_id>
```

**`GET /api/audit/{audit_id}` - poll for final report**
```bash
curl http://localhost:8000/api/audit/<audit_id>
# Returns 202 while running, full AuditReport when done
```

## Mock mode (zero API credits)

Set `MOCK_STREAM=true` in `.env`. The three streaming routes return static fixtures with realistic SSE timing - no Firecrawl, no agents-api, no LLM calls. All other routes remain on the real path.

## Notes

- Tests run fully offline - no keys, no network.
- Redis is optional locally; the pipeline degrades gracefully to a cache miss.
- `docker compose` wires Redis and inter-service URLs automatically.
