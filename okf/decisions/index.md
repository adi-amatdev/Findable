# decisions

## Concepts
- [derived-visibility](derived-visibility.md) -- The before/after visibility numbers are computed deterministically from SiteFacts signals, not measured via embedding/retrieval — locked for POC scope.
- [deterministic-llm-separation](deterministic-llm-separation.md) -- All parsing happens in plain code producing SiteFacts; LLMs only judge on top of the facts — never parse. Makes audits fast, cheap, and reproducible.
- [frontend-choice](frontend-choice.md) -- Next.js 13.5 (App Router) was chosen as the frontend framework. The API contract is framework-agnostic.
- [google-aio-alignment](google-aio-alignment.md) -- Scoring weights, visibility signals, and agent prompts were updated to reflect Google's official AI Optimization Guide after finding divergences between the original spec and Google's published recommendations.
- [parallel-inference-amd](parallel-inference-amd.md) -- One vLLM server handles concurrent agent requests via continuous batching — not N model copies — which is how real GPU parallelism works and what makes the AMD/Gemma story defensible.
- [scope-sitefacts-first](scope-sitefacts-first.md) -- The first build target is the deterministic URL→SiteFacts pipeline; agents, scoring, and aggregation are scaffolded on top.
