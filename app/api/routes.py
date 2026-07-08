"""API routes.

Implemented:
- POST /api/sitefacts  — the URL -> SiteFacts pipeline (the deliverable).
- POST /scrape         — raw Firecrawl passthrough (debug utility).
- GET  /health, GET /  — meta.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

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
