"""Resource-safety tests for the crawlability sub-agent."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.agents.crawlability.sub_agent import _pass1


async def test_pass1_uses_one_domain_traffic_lookup():
    """Internal links must not trigger one expensive Tranco load per URL."""
    links = [f"https://example.com/page-{i}" for i in range(10)]

    with (
        patch(
            "app.agents.crawlability.sub_agent.crawl_page_impl",
            AsyncMock(return_value={"status": 200, "js_ratio": 0.1}),
        ),
        patch(
            "app.agents.crawlability.sub_agent.fetch_links_impl",
            AsyncMock(return_value={"internal": links}),
        ),
        patch(
            "app.agents.crawlability.sub_agent.estimate_page_traffic_impl",
            AsyncMock(return_value={"tranco_rank": 42}),
        ) as traffic,
    ):
        report, selected = await _pass1("https://example.com")

    assert selected == links[:4]
    assert traffic.await_count == 1
    assert "domain Tranco rank 42" in report.summary
