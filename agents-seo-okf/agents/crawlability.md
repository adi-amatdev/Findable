---
type: Agent
title: Crawlability and Access Agent
status: scaffold
description: Judges how much content is blocked or invisible to AI crawlers — robots.txt restrictions, JS-gated content, sitemap gaps — and produces plain-language fixes.
tags: [agent, crawlability, robots, js]
timestamp: 2026-07-08T00:00:00Z
---

# Crawlability and Access Agent

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md).

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `robots.allows` — per-bot allow/deny for `GPTBot`, `ClaudeBot`, `PerplexityBot`, `OAI-SearchBot`, `Google-Extended`, `CCBot`.
- `sitemap.exists` / `sitemap.valid` / `sitemap.url_count`
- `http.status`, `http.latency_ms`
- `render.js_dependency_ratio`, `render.content_visible_without_js`

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: Gemma 4 E4B local). The prompt asks: *how much meaningful content is JS-gated? What are the plain-language blockers and how should they be fixed?*

## Hard gates it feeds

Two of the [AI Readiness Score](/scoring/ai-readiness-score.md) hard gates depend on findings from this agent:
- Robots blocks all AI bots → crawlability capped at ~10; overall capped at ~35.
- `content_visible_without_js == false` → crawlability capped at ~25.

## Weight in overall score

30% of the [AI Readiness Score](/scoring/ai-readiness-score.md).
