"""API routes.

Implemented:
- POST /api/sitefacts        — the URL -> SiteFacts pipeline (the deliverable).
- POST /api/audit            — SiteFacts pipeline + forward to agents-api for full audit (blocking).
- POST /api/audit/start      — async variant: returns agent_ids immediately for SSE streaming.
- GET  /agent/stream/{id}    — SSE proxy: streams AgentStatusEvents from agents-api to frontend.
- GET  /api/audit/{id}       — poll proxy: returns AuditReport once agents finish (or 202).
- POST /scrape               — raw Firecrawl passthrough (debug utility).
- GET  /health, GET /        — meta.
"""

from __future__ import annotations

import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..cache import Cache, get_cache
from ..config import Settings, get_settings
from ..crawl.firecrawl import FirecrawlClient, FirecrawlError
from ..models.api_models import ScrapeRequest, SiteFactsRequest
from ..models.contracts import SiteFacts
from ..pipeline import SiteFactsPipeline
from .deps import get_firecrawl, get_pipeline

router = APIRouter()


def _raise_firecrawl(err: FirecrawlError) -> None:
    raise HTTPException(
        status_code=err.status_code or 502,
        detail={"error": str(err), "firecrawl": err.payload},
    )


@router.get("/", tags=["meta"])
async def root(settings: Settings = Depends(get_settings)):
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "implemented": ["POST /api/sitefacts", "POST /scrape", "GET /health"],
        "scaffolded_next": ["agents", "model-router", "scoring", "aggregation", "orchestrator"],
    }


@router.get("/health", tags=["meta"])
async def health(
    settings: Settings = Depends(get_settings),
    cache: Cache = Depends(get_cache),
):
    return {
        "status": "ok",
        "service": settings.app_name,
        "firecrawl_configured": bool(settings.firecrawl_api_key),
        "cache_enabled": cache.enabled,
        "cache_connected": await cache.ping(),
    }


@router.post("/api/sitefacts", response_model=SiteFacts, tags=["pipeline"])
async def sitefacts(
    req: SiteFactsRequest,
    pipeline: SiteFactsPipeline = Depends(get_pipeline),
) -> SiteFacts:
    """Crawl a URL and return its deterministic SiteFacts snapshot."""
    try:
        return await pipeline.run(str(req.url), refresh=req.refresh)
    except FirecrawlError as err:
        _raise_firecrawl(err)


@router.post("/api/audit", tags=["pipeline"])
async def audit(
    req: SiteFactsRequest,
    pipeline: SiteFactsPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
):
    """Crawl URL -> SiteFacts -> agents-api for full AI readiness audit."""
    if not settings.agents_url:
        raise HTTPException(status_code=503, detail="AGENTS_URL not configured")
    try:
        sf = await pipeline.run(str(req.url), refresh=req.refresh)
    except FirecrawlError as err:
        _raise_firecrawl(err)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.agents_url.rstrip('/')}/audit",
                content=sf.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"agents-api returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach agents-api: {exc}")


@router.post("/api/audit/start", tags=["pipeline"])
async def audit_start(
    req: SiteFactsRequest,
    pipeline: SiteFactsPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
):
    """Crawl URL → SiteFacts → fire agents async → return agent_ids immediately for SSE streaming."""
    if not settings.agents_url:
        raise HTTPException(status_code=503, detail="AGENTS_URL not configured")
    try:
        sf = await pipeline.run(str(req.url), refresh=req.refresh)
    except FirecrawlError as err:
        _raise_firecrawl(err)

    audit_id = str(uuid.uuid4())
    agent_ids = {
        name: str(uuid.uuid4())
        for name in ["crawlability", "content_signal", "structured_data", "entity_topic"]
    }

    payload = {
        "sitefacts": sf.model_dump(by_alias=True),
        "audit_id": audit_id,
        "agent_ids": agent_ids,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.agents_url.rstrip('/')}/audit/start",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"agents-api returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach agents-api: {exc}")

    return {"audit_id": audit_id, "agent_ids": agent_ids}


@router.get("/agent/stream/{agent_id}", tags=["streaming"])
async def agent_stream_proxy(
    agent_id: str,
    settings: Settings = Depends(get_settings),
):
    """Transparent SSE proxy — forwards agents-api stream to the frontend."""
    async def generate():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    f"{settings.agents_url.rstrip('/')}/agent/stream/{agent_id}",
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.RequestError:
            yield b"event: error\ndata: {\"detail\": \"lost connection to agents-api\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/api/audit/{audit_id}", tags=["pipeline"])
async def audit_result_proxy(
    audit_id: str,
    settings: Settings = Depends(get_settings),
):
    """Poll proxy — returns AuditReport or 202 while still running."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.agents_url.rstrip('/')}/audit/{audit_id}/result"
            )
            if resp.status_code == 202:
                return resp.json()
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"agents-api returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach agents-api: {exc}")


@router.post("/scrape", tags=["debug"])
async def scrape(
    req: ScrapeRequest,
    client: FirecrawlClient = Depends(get_firecrawl),
):
    """Raw Firecrawl passthrough — inspect exactly what the crawler returns."""
    options = req.options.model_dump(by_alias=True, exclude_none=True)
    try:
        data = await client.scrape(str(req.url), options)
    except FirecrawlError as err:
        _raise_firecrawl(err)
    return {"url": str(req.url), "options": options, "data": data}
