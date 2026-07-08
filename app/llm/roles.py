"""LLM roles and their ordered failover routes (reference data).

Transcribed from agents-seo-okf/components/model-router.md. Each role has an
ordered chain: primary -> alt1 -> alt2 -> backup. `backend` is "local" (vLLM on
ROCm) or "fireworks" (remote). This is config only — no call logic here.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CRAWLABILITY = "crawlability"
    CONTENT_SIGNAL = "content_signal"
    STRUCTURED_DATA = "structured_data"
    ENTITY_TOPIC = "entity_topic"
    AGGREGATOR = "aggregator"


# Ordered failover chain per role. Each entry: (model, backend).
ROLE_ROUTES: dict[Role, list[tuple[str, str]]] = {
    Role.ORCHESTRATOR: [
        ("gemma-4-e4b", "local"),
        ("qwen3-4b", "local"),
        ("llama-3.2-3b", "local"),
        ("gemma-4-26b-a4b", "fireworks"),
    ],
    Role.CRAWLABILITY: [
        ("gemma-4-e4b", "local"),
        ("qwen3-4b", "local"),
        ("phi-4-mini", "local"),
        ("gemma-4-e4b", "fireworks"),
    ],
    Role.CONTENT_SIGNAL: [
        ("gemma-4-31b", "fireworks"),
        ("qwen3-32b", "fireworks"),
        ("gpt-oss-120b", "fireworks"),
        ("gemma-4-26b-a4b", "local"),
    ],
    Role.STRUCTURED_DATA: [
        ("gemma-4-26b-a4b", "local"),
        ("qwen3-14b", "local"),
        ("gpt-oss-20b", "local"),
        ("gemma-4-e4b", "local"),
    ],
    Role.ENTITY_TOPIC: [
        ("qwen3-14b", "local"),
        ("gemma-4-26b-a4b", "local"),
        ("llama-3.1-8b", "local"),
        ("gemma-4", "fireworks"),
    ],
    Role.AGGREGATOR: [
        ("gemma-4-31b", "fireworks"),
        ("qwen3-32b", "fireworks"),
        ("deepseek-v3", "fireworks"),
        ("gemma-4-e4b", "local"),
    ],
}
