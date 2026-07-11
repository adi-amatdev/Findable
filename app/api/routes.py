"""API routes.

Implemented:
- POST /api/sitefacts        - the URL -> SiteFacts pipeline (the deliverable).
- POST /api/audit            - SiteFacts pipeline + forward to agents-api for full audit (blocking).
- POST /api/audit/start      - async variant: returns agent_ids immediately for SSE streaming.
- GET  /agent/stream/{id}    - SSE proxy: streams AgentStatusEvents from agents-api to frontend.
- GET  /api/audit/{id}       - poll proxy: returns AuditReport once agents finish (or 202).
- POST /scrape               - raw Firecrawl passthrough (debug utility).
- GET  /health, GET /        - meta.
"""

from __future__ import annotations

import asyncio
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..cache import Cache, get_cache
from ..config import Settings, get_settings
from ..crawl.firecrawl import FirecrawlClient, FirecrawlError
from .. import mock as mock_state
from ..models.api_models import ScrapeRequest, SiteFactsRequest
from ..models.contracts import SiteFacts
from ..pdf import build_pdf
from ..pipeline import SiteFactsPipeline
from .deps import get_firecrawl, get_pipeline

router = APIRouter()
MAX_AGENT_MARKDOWN_CHARS = 12_000


def _agent_sitefacts_payload(sitefacts: SiteFacts) -> dict:
    """Send agents the bounded content slice their prompts are designed to use."""
    payload = sitefacts.model_dump(by_alias=True)
    markdown = payload.get("markdown")
    if isinstance(markdown, str) and len(markdown) > MAX_AGENT_MARKDOWN_CHARS:
        payload["markdown"] = markdown[:MAX_AGENT_MARKDOWN_CHARS]
    return payload


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
                json=_agent_sitefacts_payload(sf),
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
    """Crawl URL -> SiteFacts -> fire agents async -> return agent_ids for SSE streaming.

    When MOCK_STREAM=true: skips Firecrawl and agents-api entirely.
    Uses a static SiteFacts + static AuditReport. SSE events still stream on
    a realistic schedule so the frontend UI can be developed without API costs.
    """
    audit_id = str(uuid.uuid4())
    agent_ids = {
        name: str(uuid.uuid4())
        for name in ["crawlability", "content_signal", "structured_data", "entity_topic"]
    }

    if settings.mock_stream:
        # Register in-process queues for each agent, fire background emitter.
        for aid in agent_ids.values():
            mock_state.register_agent(aid)
        asyncio.create_task(mock_state.run_mock_audit(audit_id, agent_ids))
        return JSONResponse({"audit_id": audit_id, "agent_ids": agent_ids, "mock": True})

    # ── Real path ────────────────────────────────────────────────────────────
    if not settings.agents_url:
        raise HTTPException(status_code=503, detail="AGENTS_URL not configured")
    try:
        sf = await pipeline.run(str(req.url), refresh=req.refresh)
    except FirecrawlError as err:
        _raise_firecrawl(err)

    payload = {
        "sitefacts": _agent_sitefacts_payload(sf),
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
    """SSE stream for one agent.

    Mock mode: drains the in-process asyncio.Queue registered by /api/audit/start.
    Real mode: transparent byte-for-byte proxy to agents-api.
    """
    if settings.mock_stream:
        q = mock_state.get_queue(agent_id)
        if q is None:
            raise HTTPException(status_code=404, detail=f"Unknown agent_id: {agent_id}")
        return StreamingResponse(
            mock_state.sse_stream(agent_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Real path ────────────────────────────────────────────────────────────
    # Open and validate the upstream response before returning StreamingResponse.
    # Previously an upstream 404 was wrapped in a successful 200 SSE response;
    # EventSource then reconnected forever and the UI never reached a terminal
    # state.  Keep this connection open for the generator after validation.
    client = httpx.AsyncClient(timeout=None)
    response: httpx.Response | None = None
    try:
        request = client.build_request(
            "GET", f"{settings.agents_url.rstrip('/')}/agent/stream/{agent_id}"
        )
        response = await client.send(request, stream=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = (await exc.response.aread()).decode("utf-8", errors="replace")[:200]
        await client.aclose()
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"agents-api stream unavailable: {body}",
        )
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Could not reach agents-api: {exc}")

    async def generate():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        except httpx.HTTPError as exc:
            # A running agents-api can disappear (for example, during a
            # container restart). The browser will receive a closed SSE stream
            # and enter its bounded fallback path; do not turn that normal
            # transport failure into an unhandled ASGI exception.
            import logging
            logging.getLogger(__name__).warning("agents-api stream ended: %s", exc)
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/audit/{audit_id}", tags=["pipeline"])
async def audit_result_proxy(
    audit_id: str,
    settings: Settings = Depends(get_settings),
):
    """Returns AuditReport or 202 while still running.

    Mock mode: reads from in-process result store.
    Real mode: proxies to agents-api.
    """
    if settings.mock_stream:
        report = mock_state.get_result(audit_id)
        if report is None:
            return JSONResponse({"status": "running", "mock": True}, status_code=202)
        return report

    # ── Real path ────────────────────────────────────────────────────────────
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


@router.get("/api/audit/{audit_id}/pdf", tags=["report"])
async def audit_pdf(
    audit_id: str,
    settings: Settings = Depends(get_settings),
):
    """Generate and return a verbose PDF report for the given audit.

    Works for both mock-stream audits (in-process result store) and
    real agents-api audits (proxied from agents-api).
    """
    if settings.mock_stream:
        report_data = mock_state.get_result(audit_id)
        if report_data is None:
            raise HTTPException(status_code=202, detail="Audit still running")
    else:
        if not settings.agents_url:
            raise HTTPException(status_code=503, detail="AGENTS_URL not configured")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.agents_url.rstrip('/')}/audit/{audit_id}/result"
                )
                if resp.status_code == 202:
                    raise HTTPException(status_code=202, detail="Audit still running")
                resp.raise_for_status()
                report_data = resp.json()
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"agents-api returned {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach agents-api: {exc}")

    try:
        pdf_bytes = build_pdf(report_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    url = report_data.get("url", audit_id) if isinstance(report_data, dict) else audit_id
    try:
        from urllib.parse import urlparse
        safe_name = urlparse(url).hostname or audit_id
    except Exception:
        safe_name = audit_id

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="findable-{safe_name}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post("/scrape", tags=["debug"])
async def scrape(
    req: ScrapeRequest,
    client: FirecrawlClient = Depends(get_firecrawl),
):
    """Raw Firecrawl passthrough - inspect exactly what the crawler returns."""
    options = req.options.model_dump(by_alias=True, exclude_none=True)
    try:
        data = await client.scrape(str(req.url), options)
    except FirecrawlError as err:
        _raise_firecrawl(err)
    return {"url": str(req.url), "options": options, "data": data}
