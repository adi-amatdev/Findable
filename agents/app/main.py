"""
FastAPI service - receives SiteFacts, runs 4 agents + aggregator, returns AuditReport.

POST /audit                  → run full pipeline (sync, waits for result)
POST /audit/start            → fire-and-forget, returns agent_ids immediately for SSE streaming
POST /audit/batch            → run multiple SiteFacts (list)
GET  /agent/stream/{id}      → SSE stream of AgentStatusEvents for a running agent
GET  /audit/{id}/result      → poll for AuditReport once streaming completes
GET  /health                 → liveness check
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.content_signal import ContentSignalAgent
from app.agents.crawlability.agent import run_crawlability_agent
from app.agents.entity_topic import EntityTopicAgent
from app.agents.structured_data import StructuredDataAgent
import app.models.router as router_module
from app.report.aggregator import aggregate
from app.schemas import AgentResult, AuditReport, AuditStartRequest, SiteFacts
import app.state as state

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    availability = await router_module.probe_backends()
    available = [k for k, v in availability.items() if v]
    log.info("Model backends ready: %s", available or ["none - all requests will fail"])
    yield


app = FastAPI(title="Agents SEO - Inference Layer", version="0.1.0", lifespan=lifespan)


async def _run_agents(sitefacts: SiteFacts, audit_id: str | None = None) -> list[AgentResult]:
    """Run all 4 agents concurrently (no streaming)."""
    results = await asyncio.gather(
        run_crawlability_agent(sitefacts, audit_id=audit_id),
        ContentSignalAgent().run(sitefacts, audit_id=audit_id),
        StructuredDataAgent().run(sitefacts, audit_id=audit_id),
        EntityTopicAgent().run(sitefacts, audit_id=audit_id),
        return_exceptions=True,
    )
    agent_results: list[AgentResult] = []
    names = ["crawlability", "content_signal", "structured_data", "entity_topic"]
    for name, r in zip(names, results):
        if isinstance(r, Exception):
            log.warning("Agent %s failed: %s", name, r)
            agent_results.append(AgentResult(agent=name, score=50))
        else:
            agent_results.append(r)
    return agent_results


async def _run_agents_tracked(
    audit_id: str,
    sitefacts: SiteFacts,
    agent_ids: dict[str, str],
) -> None:
    """Run all 4 agents concurrently, emitting SSE events per agent."""
    names = ["crawlability", "content_signal", "structured_data", "entity_topic"]
    for aid in agent_ids.values():
        state.register_agent(aid)

    try:
        results = await asyncio.gather(
            run_crawlability_agent(sitefacts, agent_id=agent_ids.get("crawlability"), audit_id=audit_id),
            ContentSignalAgent().run(sitefacts, agent_id=agent_ids.get("content_signal"), audit_id=audit_id),
            StructuredDataAgent().run(sitefacts, agent_id=agent_ids.get("structured_data"), audit_id=audit_id),
            EntityTopicAgent().run(sitefacts, agent_id=agent_ids.get("entity_topic"), audit_id=audit_id),
            return_exceptions=True,
        )
        agent_results: list[AgentResult] = []
        for name, r in zip(names, results):
            if isinstance(r, Exception):
                log.warning("Agent %s failed: %s", name, r)
                agent_results.append(AgentResult(agent=name, score=50))
            else:
                agent_results.append(r)

        report = await aggregate([(sitefacts, agent_results)])
        state.store_result(audit_id, report)
    except Exception as exc:
        log.exception("Tracked audit %s failed", audit_id)
        state.store_result(audit_id, exc)
    finally:
        for aid in agent_ids.values():
            await state.close_agent(aid)


@app.post("/audit", response_model=AuditReport)
async def audit(sitefacts: SiteFacts) -> AuditReport:
    """Run the full 4-agent pipeline on a single SiteFacts object."""
    try:
        audit_id = str(uuid.uuid4())
        agent_results = await _run_agents(sitefacts, audit_id=audit_id)
        report = await aggregate([(sitefacts, agent_results)])
        return report
    except Exception as exc:
        log.exception("Audit failed for %s", sitefacts.url)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/audit/batch", response_model=list[AuditReport])
async def audit_batch(sitefacts_list: list[SiteFacts]) -> list[AuditReport]:
    """Run pipeline on multiple pages - returns one AuditReport per SiteFacts."""
    if len(sitefacts_list) > 10:
        raise HTTPException(status_code=400, detail="Max 10 pages per batch")
    tasks = [_run_single(sf) for sf in sitefacts_list]
    return await asyncio.gather(*tasks)


async def _run_single(sitefacts: SiteFacts) -> AuditReport:
    audit_id = str(uuid.uuid4())
    agent_results = await _run_agents(sitefacts, audit_id=audit_id)
    return await aggregate([(sitefacts, agent_results)])


@app.post("/audit/start")
async def audit_start(req: AuditStartRequest) -> JSONResponse:
    """Fire-and-forget: start agents in background, return agent_ids immediately."""
    asyncio.create_task(
        _run_agents_tracked(req.audit_id, req.sitefacts, req.agent_ids)
    )
    return JSONResponse({"audit_id": req.audit_id, "agent_ids": req.agent_ids})


@app.get("/agent/stream/{agent_id}")
async def agent_stream(agent_id: str) -> StreamingResponse:
    """SSE stream of AgentStatusEvents for a single running agent."""
    queue = state.get_queue(agent_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Unknown agent_id - audit not started or already expired")

    async def generate():
        while True:
            event = await queue.get()
            if event is None:   # sentinel: agent finished
                break
            yield f"event: agent_status\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/audit/{audit_id}/result")
async def audit_result(audit_id: str):
    """Poll for the completed AuditReport. Returns 202 while still running."""
    result = state.get_result(audit_id)
    if result is None:
        return JSONResponse({"status": "running"}, status_code=202)
    if isinstance(result, BaseException):
        raise HTTPException(status_code=500, detail=str(result))
    return result


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
