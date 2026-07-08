"""
Standalone mock server for frontend SSE testing.

Mimics the real backend API surface exactly -- no Firecrawl, no agents, no LLM.
Designed for frontend devs to test the full streaming UI flow in isolation.

Endpoints
---------
POST /api/audit/start         -> {audit_id, agent_ids}
GET  /agent/stream?agent_id=  -> text/event-stream  (query param, not path)
GET  /api/audit/{audit_id}    -> AuditReport JSON (or 202 while "running")
GET  /health                  -> {"status": "ok", "mock": true}

Usage
-----
  python agents/mock_server.py           # runs on http://localhost:8000
  python agents/mock_server.py --port 9000

CORS is open to all origins so any local dev server can connect.
"""
from __future__ import annotations

import asyncio
import argparse
import json
import time
import uuid
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Findable Mock Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory audit store
# ---------------------------------------------------------------------------

# audit_id -> {"agent_ids": {...}, "started_at": float, "url": str, "report": dict | None}
_audits: dict[str, dict] = {}

AGENT_NAMES = ["crawlability", "content_signal", "structured_data", "entity_topic"]

# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class AuditStartRequest(BaseModel):
    url: str
    refresh: bool = False


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _mock_report(url: str) -> dict:
    return {
        "url": url,
        "ai_readiness_score": 74,
        "scores": {
            "crawlability": 68,
            "content_signal": 81,
            "structured_data": 72,
            "entity_topic": 65,
        },
        "visibility": {
            "before": {"gpt": 0.42, "claude": 0.38, "perplexity": 0.51, "gemini": 0.44},
            "after":  {"gpt": 0.71, "claude": 0.68, "perplexity": 0.74, "gemini": 0.69},
        },
        "findings": [
            {
                "agent": "crawlability",
                "issue": "Googlebot-User-Agent disallowed in robots.txt for /blog/*",
                "impact": "H",
                "effort": "S",
                "fix": "Remove or narrow the /blog/* Disallow rule for AI crawlers.",
            },
            {
                "agent": "content_signal",
                "issue": "No author byline or publication date on article pages",
                "impact": "H",
                "effort": "M",
                "fix": "Add visible authorship metadata and ISO 8601 dates.",
            },
            {
                "agent": "structured_data",
                "issue": "Missing Article schema on blog posts",
                "impact": "M",
                "effort": "S",
                "fix": "Add JSON-LD Article markup with author, datePublished, headline.",
            },
            {
                "agent": "entity_topic",
                "issue": "Primary entity (company name) not mentioned in page <title>",
                "impact": "M",
                "effort": "S",
                "fix": "Prepend brand name to <title> tags site-wide.",
            },
            {
                "agent": "crawlability",
                "issue": "JS renders 60% of body text -- not visible to text-only crawlers",
                "impact": "H",
                "effort": "L",
                "fix": "Implement SSR or add <noscript> fallback for critical content.",
            },
        ],
        "summary": (
            "The site is moderately AI-visible. The primary blockers are an over-broad "
            "robots.txt disallow rule that keeps AI crawlers out of /blog, and heavy "
            "JavaScript rendering that hides content from text-only agents. Fixing those "
            "two issues alone is projected to raise the AI readiness score to ~88."
        ),
        "generated_at": time.time(),
    }


# ---------------------------------------------------------------------------
# Phase schedules  (delay_seconds, phase, detail, score)
# ---------------------------------------------------------------------------

def _phase_schedule(agent: str) -> list[tuple[float, str, str | None, int | None]]:
    if agent == "crawlability":
        return [
            (0.0, "started",           None,                  None),
            (0.4, "sub_agent_pass_1",  "seed crawl",          None),
            (1.8, "sub_agent_pass_2",  "deep crawl 4 pages",  None),
            (3.2, "sub_agent_pass_3",  "cross-page synthesis", None),
            (4.0, "judgment_call",     "crawlability",        None),
            (5.1, "parsing_result",    None,                  None),
            (5.4, "complete",          None,                  68),
        ]
    elif agent == "content_signal":
        return [
            (0.0, "started",        None,             None),
            (0.3, "building_prompt", None,            None),
            (0.8, "llm_call",       "content_signal", None),
            (3.5, "parsing_result", None,             None),
            (3.7, "complete",       None,             81),
        ]
    elif agent == "structured_data":
        return [
            (0.0, "started",         None,               None),
            (0.2, "building_prompt", None,               None),
            (0.6, "llm_call",        "structured_data",  None),
            (2.4, "parsing_result",  None,               None),
            (2.6, "complete",        None,               72),
        ]
    else:  # entity_topic
        return [
            (0.0, "started",         None,           None),
            (0.2, "building_prompt", None,           None),
            (0.7, "llm_call",        "entity_topic", None),
            (4.1, "parsing_result",  None,           None),
            (4.3, "complete",        None,           65),
        ]


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------

async def _stream_agent(
    agent_id: str,
    agent: str,
    audit_started_at: float,
) -> AsyncIterator[bytes]:
    schedule = _phase_schedule(agent)
    last_delay = 0.0
    for (delay, phase, detail, score) in schedule:
        wait = delay - last_delay
        if wait > 0:
            await asyncio.sleep(wait)
        last_delay = delay

        payload = {
            "agent_id": agent_id,
            "agent": agent,
            "phase": phase,
            "detail": detail,
            "score": score,
            "ts": audit_started_at + delay,
        }
        yield f"event: agent_status\ndata: {json.dumps(payload)}\n\n".encode()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "mock": True, "service": "findable-mock-server"}


@app.post("/api/audit/start", tags=["audit"])
async def audit_start(req: AuditStartRequest):
    """
    Simulates the async audit start:
      1. Generates audit_id + 4 agent_ids (UUIDs)
      2. Schedules a mock report to become available after ~6.5 s
      3. Returns the IDs immediately

    Frontend flow:
      - Subscribe to /agent/stream?agent_id=<id> for each of the 4 agent_ids
      - Poll GET /api/audit/{audit_id} every 2-3 s for the final report
    """
    audit_id = str(uuid.uuid4())
    agent_ids = {name: str(uuid.uuid4()) for name in AGENT_NAMES}
    started_at = time.time()

    _audits[audit_id] = {
        "url": req.url,
        "agent_ids": agent_ids,
        "started_at": started_at,
        "report": None,
    }

    async def _finish_after_delay():
        await asyncio.sleep(6.5)
        if audit_id in _audits:
            _audits[audit_id]["report"] = _mock_report(req.url)

    asyncio.create_task(_finish_after_delay())

    return JSONResponse({"audit_id": audit_id, "agent_ids": agent_ids})


@app.get("/agent/stream", tags=["streaming"])
async def agent_stream(
    agent_id: str = Query(..., description="Agent UUID returned by POST /api/audit/start"),
):
    """
    SSE stream for a single agent -- subscribe with ?agent_id=<uuid>.

    Emits 'agent_status' events until the agent phase reaches 'complete'.
    Each event.data is an AgentStatusEvent JSON object:

      {
        "agent_id": "<uuid>",
        "agent": "crawlability" | "content_signal" | "structured_data" | "entity_topic",
        "phase": "started" | "llm_call" | ... | "complete",
        "detail": "<string or null>",
        "score": <int or null>,   // only on "complete"
        "ts": <unix float>
      }

    Connect with EventSource:
      const src = new EventSource(`/agent/stream?agent_id=${id}`);
      src.addEventListener("agent_status", (e) => {
        const ev = JSON.parse(e.data);
        console.log(ev.agent, ev.phase, ev.score);
      });
    """
    found_audit = None
    found_agent = None
    for audit_info in _audits.values():
        for agent_name, aid in audit_info["agent_ids"].items():
            if aid == agent_id:
                found_audit = audit_info
                found_agent = agent_name
                break
        if found_agent:
            break

    if not found_audit or not found_agent:
        raise HTTPException(status_code=404, detail=f"Unknown agent_id: {agent_id}")

    return StreamingResponse(
        _stream_agent(agent_id, found_agent, found_audit["started_at"]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/audit/{audit_id}", tags=["audit"])
async def audit_result(audit_id: str):
    """
    Returns the AuditReport once all agents finish, or 202 while still running.
    Poll every 2-3 s after the SSE streams have closed.
    """
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail=f"Unknown audit_id: {audit_id}")

    report = _audits[audit_id]["report"]
    if report is None:
        return JSONResponse({"status": "running"}, status_code=202)

    return report


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Findable mock server for frontend testing")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(
        "\n"
        "+----------------------------------------------------------+\n"
        "|       Findable Mock Server  --  Frontend Testing         |\n"
        "+----------------------------------------------------------+\n"
        "|  POST /api/audit/start                                   |\n"
        "|  GET  /agent/stream?agent_id=<uuid>   <- SSE stream      |\n"
        "|  GET  /api/audit/<audit_id>           <- poll for report |\n"
        "|  GET  /health                                            |\n"
        f"|  Docs  http://{args.host}:{args.port}/docs" + " " * max(0, 24 - len(str(args.port))) + "          |\n"
        "+----------------------------------------------------------+\n"
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
