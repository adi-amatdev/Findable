"""FastAPI dependency providers.

`get_pipeline` is overridable in tests (app.dependency_overrides) to inject a
pipeline backed by an offline fake crawler.
"""

from __future__ import annotations

from fastapi import Depends

from ..cache import Cache, get_cache
from ..config import Settings, get_settings
from ..crawl.firecrawl import FirecrawlClient
from ..pipeline import SiteFactsPipeline


def get_firecrawl(settings: Settings = Depends(get_settings)) -> FirecrawlClient:
    return FirecrawlClient(settings)


def get_pipeline(
    settings: Settings = Depends(get_settings),
    cache: Cache = Depends(get_cache),
) -> SiteFactsPipeline:
    return SiteFactsPipeline(settings, cache)
