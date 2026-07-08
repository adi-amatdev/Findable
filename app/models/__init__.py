"""Data contracts shared across the pipeline.

`contracts.py` holds the canonical shapes from the agents-seo-okf spec:
- SiteFacts   — the deterministic, LLM-free page snapshot (IMPLEMENTED output).
- AgentResult — what each agent returns (contract only; agents are scaffolded).
- AuditReport — the final aggregated report (contract only; not yet built).
"""
