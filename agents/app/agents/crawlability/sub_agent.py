"""
Crawlability Sub-Agent — 3-pass deterministic orchestration.

The orchestration is programmatic (not LLM-driven tool-calling):
  Pass 1: Fetch seed URL → extract internal links → rank by Tranco traffic → select top-N
  Pass 2: Fetch each top-ranked page → measure JS ratio, bot access
  Pass 3: Synthesise cross-page findings

Each pass emits a CrawlReport. All 3 reports are passed to the judgment model.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from urllib.parse import urlparse

from app.agents.crawlability.tools import (
    check_bot_access_impl,
    crawl_page_impl,
    estimate_page_traffic_impl,
    fetch_links_impl,
)
from app.schemas import CrawlReport, SiteFacts

log = logging.getLogger(__name__)

AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot"]
TOP_N_PAGES = 4          # pages to deep-crawl in pass 2
MAX_LINK_CANDIDATES = 30  # links to rank before selecting top-N


def _same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _dedupe(links: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for l in links:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out


# ---------------------------------------------------------------------------
# Pass 1: Seed page → link discovery → Tranco ranking
# ---------------------------------------------------------------------------

async def _pass1(seed_url: str) -> tuple[CrawlReport, list[str]]:
    """
    Fetch seed page, collect internal links, rank by Tranco, return top-N.
    """
    log.info("Sub-agent pass 1: crawling seed %s", seed_url)
    seed = await crawl_page_impl(seed_url)

    if seed.get("error"):
        return (
            CrawlReport(
                depth=1, url=seed_url, reachable=False, js_dependent=False,
                bot_blocked=None, notable_links=[],
                summary=f"Failed to fetch seed page: {seed['error']}",
            ),
            [],
        )

    # Extract internal links from seed page
    links_result = await fetch_links_impl(seed_url, seed_url)
    internal_links = _dedupe(links_result.get("internal", []))[:MAX_LINK_CANDIDATES]

    # Rank by Tranco (run concurrently)
    traffic_tasks = [estimate_page_traffic_impl(u) for u in internal_links]
    traffic_results = await asyncio.gather(*traffic_tasks, return_exceptions=True)

    ranked: list[tuple[int, str]] = []
    for url, tresult in zip(internal_links, traffic_results):
        if isinstance(tresult, Exception):
            rank = 999_999
        else:
            rank = tresult.get("tranco_rank") or 999_999
        ranked.append((rank, url))
    ranked.sort(key=lambda x: x[0])

    top_urls = [u for _, u in ranked[:TOP_N_PAGES]]
    tier_str = ", ".join(
        f"{u} (rank {r if r < 999999 else 'unranked'})"
        for r, u in ranked[:TOP_N_PAGES]
    ) or "none"

    summary = (
        f"Seed page fetched (HTTP {seed['status']}, "
        f"JS ratio {seed.get('js_ratio', '?')}, "
        f"{len(internal_links)} internal links found). "
        f"Top {len(top_urls)} by Tranco traffic rank selected for deep crawl: {tier_str}."
    )

    report = CrawlReport(
        depth=1,
        url=seed_url,
        reachable=seed["status"] < 400,
        js_dependent=seed.get("js_ratio", 0) > 0.5,
        bot_blocked=None,
        notable_links=top_urls,
        summary=summary,
    )
    return report, top_urls


# ---------------------------------------------------------------------------
# Pass 2: Deep crawl top-ranked pages
# ---------------------------------------------------------------------------

async def _crawl_one_page(url: str) -> dict:
    """Fetch a page + check bot access for all AI bots concurrently."""
    page_task = crawl_page_impl(url)
    bot_tasks = [check_bot_access_impl(url, bot) for bot in AI_BOTS]
    results = await asyncio.gather(page_task, *bot_tasks, return_exceptions=True)

    page = results[0] if not isinstance(results[0], Exception) else {"url": url, "status": 0, "error": str(results[0]), "js_ratio": 0}
    bot_results = []
    for bot, bres in zip(AI_BOTS, results[1:]):
        if isinstance(bres, Exception):
            bot_results.append({"bot": bot, "allowed": True})
        else:
            bot_results.append({"bot": bot, "allowed": bres.get("allowed", True)})

    blocked = [r["bot"] for r in bot_results if not r["allowed"]]
    return {
        "url": url,
        "status": page.get("status", 0),
        "js_ratio": page.get("js_ratio", 0),
        "text_length": page.get("text_length", 0),
        "blocked_bots": blocked,
        "error": page.get("error"),
    }


async def _pass2(top_urls: list[str], seed_url: str) -> CrawlReport:
    """Crawl each top-ranked page, check bot access and JS ratio."""
    log.info("Sub-agent pass 2: crawling %d pages", len(top_urls))

    if not top_urls:
        return CrawlReport(
            depth=2, url=seed_url, reachable=True, js_dependent=False,
            bot_blocked=None, notable_links=[],
            summary="No follow-up pages selected in pass 1.",
        )

    page_results = await asyncio.gather(
        *[_crawl_one_page(u) for u in top_urls], return_exceptions=True
    )

    successes, js_heavy, bot_blocked_pages = [], [], []
    for r in page_results:
        if isinstance(r, Exception):
            continue
        if r.get("error"):
            continue
        successes.append(r)
        if r["js_ratio"] > 0.5:
            js_heavy.append(r["url"])
        if r["blocked_bots"]:
            bot_blocked_pages.append((r["url"], r["blocked_bots"]))

    blocked_summary = ""
    if bot_blocked_pages:
        blocked_summary = " Bot blocks: " + "; ".join(
            f"{u} blocks {', '.join(bots)}" for u, bots in bot_blocked_pages
        ) + "."

    js_summary = ""
    if js_heavy:
        js_summary = f" JS-heavy pages (ratio>0.5): {', '.join(js_heavy)}."

    summary = (
        f"Deep-crawled {len(successes)} of {len(top_urls)} pages."
        f"{js_summary}"
        f"{blocked_summary}"
        f" Avg text length: {round(sum(r['text_length'] for r in successes) / max(len(successes), 1))} chars."
    )

    first_blocked = bot_blocked_pages[0][1][0] if bot_blocked_pages else None

    return CrawlReport(
        depth=2,
        url=seed_url,
        reachable=bool(successes),
        js_dependent=bool(js_heavy),
        bot_blocked=first_blocked,
        notable_links=[r["url"] for r in successes],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Pass 3: Cross-page synthesis
# ---------------------------------------------------------------------------

async def _pass3(
    report1: CrawlReport,
    report2: CrawlReport,
    sitefacts: SiteFacts,
) -> CrawlReport:
    """Build a synthesis CrawlReport from passes 1+2 and the original SiteFacts."""
    issues: list[str] = []

    # JS-gating
    if sitefacts.render.js_dependency_ratio > 0.7:
        issues.append(
            f"Landing page is heavily JS-gated (ratio={sitefacts.render.js_dependency_ratio:.2f})"
        )
    if report2.js_dependent:
        issues.append("Multiple internal pages are JS-heavy — content invisible to crawlers")

    # Bot blocking
    allows = sitefacts.robots.allows.model_dump(by_alias=True)
    blocked_bots = [bot for bot, ok in allows.items() if not ok]
    if blocked_bots:
        issues.append(f"Robots.txt blocks these AI bots: {', '.join(blocked_bots)}")
    if report2.bot_blocked:
        issues.append(f"Active crawl found bot blocks on sub-pages: {report2.bot_blocked}")

    # HTTP issues
    if sitefacts.http.status >= 400:
        issues.append(f"Seed URL returns HTTP {sitefacts.http.status}")

    # Sitemap
    if not sitefacts.sitemap.valid:
        issues.append("No valid sitemap found — crawlers must discover pages via links only")

    if not issues:
        issues.append("No critical crawlability blockers detected")

    pages_crawled = len(report2.notable_links) if report2.notable_links else 0

    summary = (
        f"Synthesis across {pages_crawled + 1} pages (seed + {pages_crawled} follow-up). "
        f"Key issues: {'; '.join(issues)}."
    )

    return CrawlReport(
        depth=3,
        url=sitefacts.url,
        reachable=report1.reachable and sitefacts.http.status < 400,
        js_dependent=report1.js_dependent or report2.js_dependent,
        bot_blocked=blocked_bots[0] if blocked_bots else report2.bot_blocked,
        notable_links=[],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

EmitFn = Callable[..., Coroutine[Any, Any, None]]


async def run_sub_agent(
    sitefacts: SiteFacts,
    max_depth: int = 3,
    emit_fn: EmitFn | None = None,
) -> list[CrawlReport]:
    """
    Run the 3-pass deterministic crawl sub-agent.

    Returns up to max_depth CrawlReports.
    emit_fn is called at the start of passes 2 and 3 if provided.
    """
    reports: list[CrawlReport] = []

    async def _notify(phase: str, detail: str) -> None:
        if emit_fn is not None:
            await emit_fn(phase, detail)

    try:
        report1, top_urls = await _pass1(sitefacts.url)
        reports.append(report1)

        if max_depth >= 2:
            await _notify("sub_agent_pass_2", f"deep crawl {len(top_urls)} pages")
            report2 = await _pass2(top_urls, sitefacts.url)
            reports.append(report2)

            if max_depth >= 3:
                await _notify("sub_agent_pass_3", "cross-page synthesis")
                report3 = await _pass3(report1, report2, sitefacts)
                reports.append(report3)

    except Exception as exc:
        log.error("Sub-agent error: %s", exc, exc_info=True)
        if not reports:
            reports.append(CrawlReport(
                depth=1, url=sitefacts.url, reachable=False, js_dependent=False,
                bot_blocked=None, notable_links=[],
                summary=f"Sub-agent failed: {exc}",
            ))

    return reports
