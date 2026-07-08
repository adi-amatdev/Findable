"""Crawl & Fetch — retrieves the raw material the extractor turns into SiteFacts.

- firecrawl.py — rendered HTML, markdown, metadata, links (JS executed).
- fetch.py     — direct httpx fetch of raw HTML, robots.txt, sitemap.xml, llms.txt.
- fetcher.py   — CrawlFetcher.crawl(url) -> RawCrawl (combines both, cached).
"""

from .models import RawCrawl

__all__ = ["RawCrawl"]
