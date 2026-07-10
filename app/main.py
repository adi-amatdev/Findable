"""Findable - FastAPI app. Implements the URL -> SiteFacts pipeline."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .cache import get_cache
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await get_cache().close()


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

app.include_router(router)
