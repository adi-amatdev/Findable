"""
Crawlability sub-agent tool implementations.

All tools use httpx + stdlib. No Firecrawl dependency.
TOOL_SCHEMAS are kept for optional vLLM tool-calling mode.
"""
from __future__ import annotations

import re
import urllib.robotparser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SEOAuditBot/1.0)",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

_SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
              ".css", ".js", ".woff", ".woff2", ".ttf", ".pdf", ".zip",
              ".mp4", ".mp3", ".mov", ".avi"}


def _is_page_url(url: str) -> bool:
    """Return True if URL is likely an HTML page (not an asset)."""
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in _SKIP_EXTS):
        return False
    return True


def _extract_links(html: str, base_url: str) -> list[str]:
    """Return absolute hrefs found in raw HTML, filtering non-page assets."""
    hrefs = re.findall(r'href=["\']([^"\'#?]+)["\']', html)
    base = urlparse(base_url)
    links: list[str] = []
    for h in hrefs:
        if h.startswith("http"):
            candidate = h
        elif h.startswith("/"):
            candidate = f"{base.scheme}://{base.netloc}{h}"
        else:
            continue
        if _is_page_url(candidate):
            links.append(candidate)
    return links


def _js_ratio_from_html(html: str) -> float:
    """Rough JS-dependency ratio: script content vs total content."""
    script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    script_len = sum(len(s) for s in script_blocks)
    total_len = max(len(html), 1)
    return round(min(1.0, script_len / total_len), 3)


def _text_from_html(html: str) -> str:
    """Very lightweight HTML→text (no lxml required)."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Tool implementations (all async)
# ---------------------------------------------------------------------------

async def crawl_page_impl(url: str) -> dict[str, Any]:
    """
    Fetch a page with httpx, return cleaned text, links, and JS ratio.
    This is the sub-agent's page-loading tool.
    """
    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers=_HEADERS
        ) as client:
            resp = await client.get(url)
        html = resp.text
        text = _text_from_html(html)
        links = _extract_links(html, str(resp.url))
        js_ratio = _js_ratio_from_html(html)
        return {
            "url": str(resp.url),
            "status": resp.status_code,
            "text_length": len(text),
            "js_ratio": js_ratio,
            "excerpt": text[:3000],
            "links": links[:80],
        }
    except Exception as exc:
        return {"url": url, "status": 0, "error": str(exc), "links": [], "excerpt": ""}


async def fetch_links_impl(url: str, base_url: str | None = None) -> dict[str, Any]:
    """Fetch a page and return internal links (same-domain)."""
    result = await crawl_page_impl(url)
    if "error" in result:
        return result
    base = urlparse(base_url or url)
    internal = [
        l for l in result["links"]
        if urlparse(l).netloc == base.netloc
    ]
    external = [
        l for l in result["links"]
        if urlparse(l).netloc != base.netloc
    ]
    return {"internal": internal[:50], "external": external[:10], "url": url}


async def check_bot_access_impl(base_url: str, bot: str = "GPTBot") -> dict[str, Any]:
    """Check robots.txt for a specific bot."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(robots_url)
            rp.parse(resp.text.splitlines())
        allowed = rp.can_fetch(bot, base_url)
        return {"url": base_url, "bot": bot, "allowed": allowed, "robots_url": robots_url}
    except Exception as exc:
        return {"url": base_url, "bot": bot, "allowed": True, "error": str(exc)}


async def get_http_status_impl(url: str) -> dict[str, Any]:
    """Return HTTP status + latency for a URL."""
    import time
    try:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.head(url, headers=_HEADERS)
        return {
            "url": str(resp.url),
            "status": resp.status_code,
            "latency_ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        return {"url": url, "status": 0, "error": str(exc), "latency_ms": 0}


def get_tranco_rank_sync(domain: str) -> int | None:
    """Return Tranco rank for a domain (None if not in top 1M). Tranco returns -1 for unranked."""
    try:
        from tranco import Tranco  # type: ignore
        t = Tranco(cache=True, cache_dir=".tranco_cache")
        lst = t.list()
        rank = lst.rank(domain)
        return rank if (rank and rank > 0) else None
    except Exception:
        return None


async def estimate_page_traffic_impl(url: str) -> dict[str, Any]:
    """Estimate traffic rank via Tranco (sync in thread)."""
    import asyncio
    domain = urlparse(url).netloc.lstrip("www.")
    loop = asyncio.get_event_loop()
    rank = await loop.run_in_executor(None, get_tranco_rank_sync, domain)
    return {
        "domain": domain,
        "tranco_rank": rank,
        "traffic_tier": (
            "top-10k" if rank and rank <= 10_000 else
            "top-100k" if rank and rank <= 100_000 else
            "top-1m" if rank else
            "unranked"
        ),
    }


# ---------------------------------------------------------------------------
# OpenAI-compatible tool schemas (for vLLM tool-calling mode)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "crawl_page",
            "description": "Fetch and render a page. Returns text content, JS ratio, and discovered links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to crawl"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_links",
            "description": "Extract internal links from a page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "base_url": {"type": "string", "description": "Root domain for internal/external classification"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_bot_access",
            "description": "Check robots.txt to see if a bot is allowed to crawl a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_url": {"type": "string"},
                    "bot": {"type": "string", "description": "Bot name e.g. GPTBot, ClaudeBot"},
                },
                "required": ["base_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_http_status",
            "description": "Get HTTP status code and latency for a URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_page_traffic",
            "description": "Estimate traffic rank for a URL's domain via Tranco.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
]

TOOL_IMPLS = {
    "crawl_page": lambda args: crawl_page_impl(args["url"]),
    "fetch_links": lambda args: fetch_links_impl(args["url"], args.get("base_url")),
    "check_bot_access": lambda args: check_bot_access_impl(args["base_url"], args.get("bot", "GPTBot")),
    "get_http_status": lambda args: get_http_status_impl(args["url"]),
    "estimate_page_traffic": lambda args: estimate_page_traffic_impl(args["url"]),
}


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a tool call by name, return JSON string result."""
    import json
    impl = TOOL_IMPLS.get(name)
    if not impl:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = await impl(arguments)
    return json.dumps(result)
