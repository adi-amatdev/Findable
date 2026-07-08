---
type: Agent
title: Crawlability and Access Agent
status: implemented
description: Judges how much content is blocked or invisible to AI crawlers — robots.txt restrictions, JS-gated content, latency, sitemap gaps — via a 3-pass deterministic sub-agent plus one LLM judgment call.
tags: [agent, crawlability, robots, js, sub-agent, tranco]
timestamp: 2026-07-08T00:00:00Z
---

# Crawlability and Access Agent

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md), **out** = [AgentResult](/data/agent-result.md). Implemented in `agents/app/agents/crawlability/`.

## 3-pass deterministic sub-agent

Unlike the other agents, Crawlability runs a **programmatic sub-agent** (`sub_agent.py`) before the LLM judgment call. The sub-agent uses httpx + Tranco — no Firecrawl dependency.

| Pass | What it does |
|---|---|
| **Pass 1** — Seed + discovery | Fetches the seed URL, extracts internal links (skipping non-HTML assets: images, CSS, JS, PDFs), ranks each link's domain via Tranco library, selects top 4 pages by traffic rank. |
| **Pass 2** — Deep crawl | For each top-ranked page: fetches full HTML, runs concurrent robots.txt check against 4 AI bots (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `OAI-SearchBot`). |
| **Pass 3** — Synthesis | Deterministic merge of Pass 1 + 2 results into `CrawlReport` objects (no LLM). |

Tranco unranked domains (`rank == -1`) are treated as `None` and sorted last, preventing unranked favicon/asset URLs from being promoted.

## LLM judgment

After the sub-agent, one call via the [Model Router](/components/model-router.md) (Ollama local, light model). Prompt (`prompts/crawlability_judgment.md`) asks:

- How accessible is this site to AI crawlers and AI agents (DOM + accessibility tree)?
- Are there latency or JS-gating issues that would prevent agentic access?
- Concrete plain-language fixes ranked by impact.

Latency cap: page with >5000 ms response time is capped at score 80.

## Hard gates it feeds

Two of the [AI Readiness Score](/scoring/ai-readiness-score.md) hard gates depend on this agent:
- Robots blocks all AI bots → crawlability capped at ~10; overall capped at ~35.
- `content_visible_without_js == false` → crawlability capped at ~25.

## Weight in overall score

30% of the [AI Readiness Score](/scoring/ai-readiness-score.md).
