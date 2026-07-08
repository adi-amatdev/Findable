"""Direct httpx fetch of the raw (unrendered) page and its sidecar files.

The raw HTML (no JS executed) is paired with Firecrawl's rendered HTML to compute
the JS-dependency ratio. robots.txt / sitemap.xml / llms.txt are best-effort:
a failure yields None, never an exception.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from ..config import Settings


@dataclass
class DirectFetchResult:
    final_url: str
    http_status: int
    latency_ms: int
    redirects: int
    content_type: str
    raw_html: str
    robots_txt: Optional[str]
    sitemap_xml: Optional[str]
    llms_txt: Optional[str]


class DirectFetcher:
    def __init__(self, settings: Settings):
        self._settings = settings

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._settings.fetch_timeout,
            follow_redirects=True,
            headers={"User-Agent": self._settings.fetch_user_agent},
        )

    async def fetch(self, url: str) -> DirectFetchResult:
        origin = _origin(url)
        async with self._client() as client:
            start = time.perf_counter()
            page = await self._get_page(client, url)
            latency_ms = int((time.perf_counter() - start) * 1000)

            robots, sitemap, llms = await asyncio.gather(
                self._get_text(client, urljoin(origin, "/robots.txt")),
                self._get_text(client, urljoin(origin, "/sitemap.xml")),
                self._get_text(client, urljoin(origin, "/llms.txt")),
            )

        if page is None:
            return DirectFetchResult(
                final_url=url, http_status=0, latency_ms=latency_ms, redirects=0,
                content_type="", raw_html="", robots_txt=robots,
                sitemap_xml=sitemap, llms_txt=llms,
            )

        return DirectFetchResult(
            final_url=str(page.url),
            http_status=page.status_code,
            latency_ms=latency_ms,
            redirects=len(page.history),
            content_type=page.headers.get("content-type", ""),
            raw_html=page.text,
            robots_txt=robots,
            sitemap_xml=sitemap,
            llms_txt=llms,
        )

    async def _get_page(self, client: httpx.AsyncClient, url: str) -> Optional[httpx.Response]:
        try:
            return await client.get(url)
        except httpx.HTTPError:
            return None

    async def _get_text(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Best-effort fetch of a sidecar file; None on any failure or non-2xx."""
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        return resp.text


def _origin(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"
