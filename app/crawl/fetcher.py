"""CrawlFetcher — combines the rendered (Firecrawl) and raw (httpx) fetches
into a single RawCrawl blob, cached by URL hash.

Dependencies (Firecrawl client, direct fetcher) are injectable so the pipeline
can be exercised offline in tests with a fake crawler.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, Protocol

from ..cache import Cache, make_key
from ..config import Settings
from .fetch import DirectFetcher
from .firecrawl import FirecrawlClient
from .models import RawCrawl

# Formats we ask Firecrawl for: rawHtml = full rendered DOM (JS executed) for the
# render diff + structured-data parse; markdown = clean main content; links = graph.
FIRECRAWL_FORMATS = ["markdown", "rawHtml", "links"]


class Crawler(Protocol):
    async def crawl(self, url: str, refresh: bool = False) -> RawCrawl: ...


class CrawlFetcher:
    def __init__(
        self,
        settings: Settings,
        cache: Cache,
        firecrawl: Optional[FirecrawlClient] = None,
        direct: Optional[DirectFetcher] = None,
    ):
        self._settings = settings
        self._cache = cache
        self._firecrawl = firecrawl or FirecrawlClient(settings)
        self._direct = direct or DirectFetcher(settings)

    async def crawl(self, url: str, refresh: bool = False) -> RawCrawl:
        key = make_key(url, "crawl")
        if not refresh:
            hit = await self._cache.get(key)
            if hit is not None:
                return RawCrawl(**hit)

        options = {"formats": FIRECRAWL_FORMATS, "onlyMainContent": True}
        fc_data, direct = await asyncio.gather(
            self._firecrawl.scrape(url, options),
            self._direct.fetch(url),
        )

        metadata = fc_data.get("metadata") or {}
        raw = RawCrawl(
            url=url,
            final_url=direct.final_url or metadata.get("sourceURL") or url,
            fetched_at=_now_iso(),
            http_status=direct.http_status or int(metadata.get("statusCode") or 0),
            latency_ms=direct.latency_ms,
            redirects=direct.redirects,
            content_type=direct.content_type,
            rendered_html=fc_data.get("rawHtml") or fc_data.get("html") or "",
            markdown=fc_data.get("markdown") or "",
            metadata=metadata,
            links=fc_data.get("links") or [],
            screenshot=fc_data.get("screenshot"),
            raw_html=direct.raw_html,
            robots_txt=direct.robots_txt,
            sitemap_xml=direct.sitemap_xml,
            llms_txt=direct.llms_txt,
        )

        await self._cache.set(key, raw.model_dump())
        return raw


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
