"""
FastAPI service — receives SiteFacts, runs 4 agents + aggregator, returns AuditReport.

POST /audit          → run full pipeline (sync, waits for result)
POST /audit/batch    → run multiple SiteFacts (list)
GET  /health         → liveness check
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.agents.content_signal import ContentSignalAgent
from app.agents.crawlability.agent import run_crawlability_agent
from app.agents.entity_topic import EntityTopicAgent
from app.agents.structured_data import StructuredDataAgent
from app.report.aggregator import aggregate
from app.schemas import AgentResult, AuditReport, SiteFacts

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Agents SEO — Inference Layer", version="0.1.0")


async def _run_agents(sitefacts: SiteFacts) -> list[AgentResult]:
    """Run all 4 agents concurrently."""
    results = await asyncio.gather(
        run_crawlability_agent(sitefacts),
        ContentSignalAgent().run(sitefacts),
        StructuredDataAgent().run(sitefacts),
        EntityTopicAgent().run(sitefacts),
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


@app.post("/audit", response_model=AuditReport)
async def audit(sitefacts: SiteFacts) -> AuditReport:
    """Run the full 4-agent pipeline on a single SiteFacts object."""
    try:
        agent_results = await _run_agents(sitefacts)
        report = await aggregate([(sitefacts, agent_results)])
        return report
    except Exception as exc:
        log.exception("Audit failed for %s", sitefacts.url)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/audit/batch", response_model=list[AuditReport])
async def audit_batch(sitefacts_list: list[SiteFacts]) -> list[AuditReport]:
    """Run pipeline on multiple pages — returns one AuditReport per SiteFacts."""
    if len(sitefacts_list) > 10:
        raise HTTPException(status_code=400, detail="Max 10 pages per batch")
    tasks = [_run_single(sf) for sf in sitefacts_list]
    return await asyncio.gather(*tasks)


async def _run_single(sitefacts: SiteFacts) -> AuditReport:
    agent_results = await _run_agents(sitefacts)
    return await aggregate([(sitefacts, agent_results)])


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
