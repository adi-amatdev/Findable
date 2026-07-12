"""Findable - FastAPI app. Implements the URL -> SiteFacts pipeline."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .cache import get_cache
from .config import get_settings
from .ratelimit import RateLimiter, RateLimitMiddleware

settings = get_settings()
logger = logging.getLogger(__name__)


def _build_rate_limiter() -> RateLimiter:
    whitelist = {
        ip.strip() for ip in settings.rate_limit_whitelist.split(",") if ip.strip()
    }
    return RateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_hours * 3600,
        whitelist=whitelist,
    )


rate_limiter = _build_rate_limiter()


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task = asyncio.create_task(_periodic_cleanup(rate_limiter))
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await get_cache().close()


async def _periodic_cleanup(limiter: RateLimiter) -> None:
    """Background task that prunes expired buckets at a fixed interval."""
    interval = settings.rate_limit_cleanup_interval_seconds
    while True:
        await asyncio.sleep(interval)
        removed = await limiter.cleanup()
        if removed:
            logger.debug("Rate limiter: cleaned up %d expired buckets", removed)


app = FastAPI(
    title=f"{settings.app_name} - Agents SEO/AEO",
    version="0.1.0",
    description=(
        "URL in, SiteFacts out. A URL is crawled (Firecrawl rendered + direct "
        "fetch of raw HTML / robots.txt / sitemap.xml / llms.txt) and parsed "
        "deterministically into a SiteFacts snapshot. Downstream agent, scoring, "
        "and aggregation layers are scaffolded (see okf/)."
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

if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.include_router(router)
