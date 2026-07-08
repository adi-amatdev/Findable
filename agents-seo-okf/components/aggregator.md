---
type: Service
title: Aggregator
description: Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
tags: [scoring, aggregation, report]
timestamp: 2026-07-08T00:00:00Z
---

# Aggregator

Runs after all four [agents](/agents/) return their [AgentResults](/data/agent-result.md). Two jobs:

## 1. Deterministic scoring

Applies the [AI Readiness Score](/scoring/ai-readiness-score.md) rubric (hard gates + weighted formula) to produce the headline score and the [Before/After Visibility Estimate](/scoring/visibility-estimate.md). Findings from all agents are merged and sorted by **impact ÷ effort** so the top items are the cheapest big wins. Systemic findings (issues appearing across most pages) are collapsed into single recommendations.

## 2. Executive summary (one LLM call)

Calls the [Model Router](/components/model-router.md) with Gemma 4 31B on [Fireworks](/external/fireworks-api.md) to write a short, grounded executive summary *from* the structured findings — synthesis, not fact generation. This is the aggregator's only LLM call.

## Output

A fully populated [AuditReport](/data/audit-report.md) that the [API](/components/api.md) returns and the [Frontend](/components/frontend.md) renders.
