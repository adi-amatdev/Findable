---
type: Decision
title: Derived Visibility Estimate (no retrieval simulation)
description: The before/after visibility numbers are computed deterministically from SiteFacts signals, not measured via embedding/retrieval — locked for POC scope.
status: planned
tags: [decision, visibility, scope]
timestamp: 2026-07-08T00:00:00Z
---

# Derived Visibility Estimate

## Decision (locked)

The [Before/After Visibility Estimate](/scoring/visibility-estimate.md) is a **derived estimate only** — a deterministic function mapping [SiteFacts](/data/site-facts.md) signals to per-model visibility 0–1 values. It is **not** a measured retrieval simulation.

## What was ruled out (and why)

A *real* retrieval simulation would embed the page, generate questions an AI user might ask, then test whether each target model can find and answer them from the page. This would give a *measured* before/after number, not an estimate. It is noted as a post-POC direction. Reasons it is out of scope:

- Requires calling four separate AI search APIs (or simulating their retrieval) per page, per run.
- Substantially more latency and cost per audit run.
- Harder to make reproducible (model responses vary).
- The derived estimate is honest as an estimate and visually striking — the right call for a proof of concept.

## How to answer judge questions

"We compute a deterministic signal mapping, not a live retrieval test — that's explicitly noted as a post-POC direction. The estimate is honest and reproducible; a live simulation would add latency and non-determinism we didn't want in a hackathon POC."
