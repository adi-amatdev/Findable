"""Findable — FastAPI app exposing Firecrawl-backed SEO/AEO endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .cache import Cache, get_cache, make_key
from .config import Settings, get_settings
from .firecrawl_client import FirecrawlClient, FirecrawlError
from .schemas import AuditRequest, ScrapeOptions, ScrapeRequest
from .seo import build_audit

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Close the Redis connection pool cleanly on shutdown.
    await get_cache().close()


app = FastAPI(
    title=f"{settings.app_name} — SEO/AEO Audit API",
    version="0.1.0",
    description=(
        "Pass a URL, Firecrawl fetches the page, and you get the best signals "
        "for a search-engine (SEO) and answer-engine/agent (AEO) audit. "
        "Results are cached in Redis, so repeat requests never re-scrape "
        "(no wasted tokens). Send `refresh: true` to force a fresh scrape.\n\n"
        "- `POST /scrape` — raw Firecrawl passthrough; tweak any option.\n"
        "- `POST /audit` — opinionated, structured SEO + AEO report."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client(cfg: Settings = Depends(get_settings)) -> FirecrawlClient:
    return FirecrawlClient(cfg)


def _raise(err: FirecrawlError) -> None:
    raise HTTPException(
        status_code=err.status_code or 502,
        detail={"error": str(err), "firecrawl": err.payload},
    )


async def get_or_scrape(
    url: str,
    options: dict[str, Any],
    *,
    client: FirecrawlClient,
    cache: Cache,
    refresh: bool,
) -> tuple[dict[str, Any], bool]:
    """Return (data, cached). Check Redis first; only scrape on a miss."""
    key = make_key(url, options)
    if not refresh:
        hit = await cache.get(key)
        if hit is not None:
            return hit, True
    data = await client.scrape(url, options)
    await cache.set(key, data)
    return data, False


@app.get("/", tags=["meta"])
async def root():
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "endpoints": ["POST /scrape", "POST /audit", "GET /health"],
    }


@app.get("/health", tags=["meta"])
async def health(cache: Cache = Depends(get_cache)):
    return {
        "status": "ok",
        "service": settings.app_name,
        "firecrawl_configured": bool(settings.firecrawl_api_key),
        "firecrawl_endpoint": settings.scrape_endpoint,
        "cache_enabled": cache.enabled,
        "cache_connected": await cache.ping(),
    }


@app.post("/scrape", tags=["firecrawl"])
async def scrape(
    req: ScrapeRequest,
    client: FirecrawlClient = Depends(get_client),
    cache: Cache = Depends(get_cache),
):
    """Raw Firecrawl scrape. Send `options` to control formats and behaviour."""
    options = req.options.model_dump(by_alias=True, exclude_none=True)
    try:
        data, cached = await get_or_scrape(
            str(req.url), options, client=client, cache=cache, refresh=req.refresh
        )
    except FirecrawlError as err:
        _raise(err)
    return {"url": str(req.url), "cached": cached, "options": options, "data": data}


@app.post("/audit", tags=["audit"])
async def audit(
    req: AuditRequest,
    client: FirecrawlClient = Depends(get_client),
    cache: Cache = Depends(get_cache),
):
    """Fetch the page with the optimal format set and return an SEO + AEO audit."""
    # rawHtml -> full <head> for SEO/schema; markdown -> content depth & what
    # agents read; links -> internal/external analysis; summary -> AEO preview.
    formats = ["markdown", "rawHtml", "links", "summary"]
    if req.include_screenshot:
        formats.append("screenshot")

    options = ScrapeOptions(
        formats=formats,
        only_main_content=True,
        wait_for=req.wait_for,
        mobile=req.mobile,
    ).model_dump(by_alias=True, exclude_none=True)

    try:
        data, cached = await get_or_scrape(
            str(req.url), options, client=client, cache=cache, refresh=req.refresh
        )
    except FirecrawlError as err:
        _raise(err)

    result = build_audit(str(req.url), data, include_raw=req.include_raw_result)
    result["cached"] = cached
    return result
