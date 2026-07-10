# Findable

> Can AI actually read, trust, and cite your website?

Findable audits a URL the way AI crawlers see it - not classic SEO. It tells you what content is JS-gated, which AI bots are blocked, how strong your schema markup is, and whether your page is citation-worthy for ChatGPT, Claude, Perplexity, and Gemini.

**Built by Team Dhridhata** - Aaditya Acharya · Rohit Neeraje

---

## How it works

```
URL → Firecrawl (rendered) + httpx (raw) → SiteFacts
         ↓
  Four AI agents run in parallel (asyncio.gather)
  ├── Crawlability     (30%) - robots.txt, JS-gating, latency, sitemaps
  ├── Content Signal   (35%) - E-E-A-T, commodity check, citation-worthiness
  ├── Structured Data  (15%) - schema.org, llms.txt, meta extraction
  └── Entity & Topic   (20%) - knowledge graph, disambiguation, authority
         ↓
  Weighted score (0–100) + score caps on critical failures + estimated before/after visibility per AI bot
         ↓
  AuditReport → live SSE dashboard → PDF / Markdown export
```

Results stream live to the frontend via SSE as each agent completes.

---

## AMD + Gemma - the inference stack

Findable's reasoning engine runs entirely on **AMD ROCm + vLLM + Gemma**:

| Layer | Detail |
|---|---|
| Hardware | AMD Radeon PRO W7900 · 48 GB VRAM · ROCm 7.2.1 |
| Light model | `google/gemma-2-2b-it` - served via vLLM on port 8000 |
| Heavy model | `google/gemma-2-9b-it` - served via vLLM on port 8001 |
| Cloud fallback | Fireworks AI - `gemma-4-27b-it` (heavy) · `gemma-4-e4b-it` (light) |
| Local fallback | Ollama - `gemma4:e2b` |

All four agents fire **concurrent async requests** that vLLM batches via continuous batching on the AMD GPU - real parallelism, not N model copies. Fireworks (also Gemma) handles the two heaviest roles as a quality fallback. Gemma models serve every LLM role in the system.

---

## Setup

### Prerequisites

- Docker + Docker Compose
- A Firecrawl API key (free tier works)
- Optional: Fireworks API key for cloud LLM fallback
- Optional: AMD GPU server running `server_files/serve.sh` for local inference

### 1. Clone and configure

```bash
git clone https://github.com/<your-org>/Findable.git
cd Findable
cp .env.example .env
```

Edit `.env`:

| Variable | Where to get it | Purpose |
|---|---|---|
| `FIRECRAWL_API_KEY` | [firecrawl.dev/app/api-keys](https://www.firecrawl.dev/app/api-keys) | Page crawling (required for real audits) |
| `FIREWORKS_KEY` | [fireworks.ai](https://fireworks.ai) | Gemma cloud fallback (optional) |
| `VLLM_URL` | Publicly accessible URL of your running vLLM heavy instance | AMD GPU heavy model (optional) |
| `VLLM_LIGHT_URL` | Publicly accessible URL of your running vLLM light instance | AMD GPU light model (optional) |
| `MOCK_STREAM` | Set `true` | Zero-cost demo - no API keys needed |

### 2. Run

```bash
docker compose up --build
```

This starts frontend, backend, agents-api, and Redis - everything is included.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/docs |
| Agents API | http://localhost:8080/docs |

### 3. Zero-cost demo (no API keys)

```bash
MOCK_STREAM=true docker compose up --build
```

Streams a full mock audit with realistic SSE events - no Firecrawl, no LLM calls.

---

## Running Gemma on AMD (optional)

If you have access to an AMD ROCm GPU server, spin up two vLLM instances on it:

```bash
# Light model (port 8000)
vllm serve google/gemma-2-2b-it --served-model-name light --port 8000

# Heavy model (port 8001)
vllm serve google/gemma-2-9b-it --served-model-name heavy --port 8001
```

Expose both ports publicly (e.g. via cloudflared or ngrok), then set the resulting URLs in `.env` as `VLLM_LIGHT_URL` and `VLLM_URL`. Restart the agents container.

---

## Live deployment

The full stack (frontend, backend, agents-api, Redis) is hosted on an AWS EC2 `t3.small` instance at **[https://findable.duckdns.org](https://findable.duckdns.org)**. All LLM inference is offloaded to the AMD ROCm GPU server (vLLM) and Fireworks AI — the EC2 instance handles only routing, orchestration, and serving the frontend.

---

## Tech stack

| Category | Technologies |
|---|---|
| AI models | Gemma 2 2B + 9B (AMD/vLLM), Gemma 4 via Fireworks AI |
| Inference | vLLM on AMD ROCm 7.2.1 · Fireworks AI (Gemma 4 cloud) · Ollama (local fallback) |
| Backend | Python · FastAPI · httpx · Firecrawl |
| Agents | 4 async agents · asyncio fan-out · SSE streaming |
| Scoring | Weighted rubric · score caps on critical failures · per-bot visibility estimate derived from SiteFacts signals |
| Frontend | Next.js · React · anime.js · SSE EventSource |
| Infrastructure | Docker Compose · Redis · cloudflared tunnels |
| Dev tooling | uv · Ruff |

---

## Why it matters

AI search (ChatGPT, Perplexity, Claude, Gemini) is replacing the blue-link web. Websites that aren't readable by AI crawlers simply won't be cited - no matter how good their classic SEO is. Findable gives any site owner a concrete, actionable score and fix list before they get left out of AI answers.

---

## Docs

- [USAGE.md](USAGE.md) - full API reference, curl examples, frontend dev setup
- [VALIDATION.md](VALIDATION.md) - architecture conformance map
- [okf/](okf/index.md) - full system architecture knowledge base
