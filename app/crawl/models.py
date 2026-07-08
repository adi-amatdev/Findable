"""RawCrawl — the raw material for one page, before any parsing.

The rendered side comes from Firecrawl (JS executed); the raw side and the
sidecar files (robots/sitemap/llms.txt) come from a direct httpx fetch. The
raw+rendered pair is what lets the extractor compute `js_dependency_ratio`.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RawCrawl(BaseModel):
    url: str
    final_url: str = ""
    fetched_at: str = ""  # ISO8601

    # HTTP facts from the direct fetch of the page.
    http_status: int = 0
    latency_ms: int = 0
    redirects: int = 0
    content_type: str = ""

    # Rendered side (Firecrawl).
    rendered_html: str = ""
    markdown: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)
    screenshot: Optional[str] = None

    # Raw side + sidecar files (direct httpx fetch); None = fetch not attempted/failed.
    raw_html: str = ""
    robots_txt: Optional[str] = None
    sitemap_xml: Optional[str] = None
    llms_txt: Optional[str] = None
