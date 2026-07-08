"""The implemented pipeline: URL -> RawCrawl (Firecrawl + fetch) -> SiteFacts.

This is the full extent of what is implemented today (per scope). Downstream
layers (agents, scoring, aggregation) are scaffolded and consume SiteFacts.
"""

from __future__ import annotations

from typing import Optional

from .cache import Cache
from .config import Settings
from .crawl.fetcher import Crawler, CrawlFetcher
from .extraction import build_site_facts
from .models.contracts import SiteFacts


class SiteFactsPipeline:
    def __init__(self, settings: Settings, cache: Cache, crawler: Optional[Crawler] = None):
        # `crawler` is injectable so the pipeline can run offline in tests.
        self._crawler: Crawler = crawler or CrawlFetcher(settings, cache)

    async def run(self, url: str, refresh: bool = False) -> SiteFacts:
        raw = await self._crawler.crawl(url, refresh=refresh)
        return build_site_facts(raw)
