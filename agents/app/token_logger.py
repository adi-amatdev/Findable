"""
Token usage logging — single sink for every LLM call's token usage.

Every call routed through ModelRouter.call_with_fallback() (production
agents, report_writer, and the standalone benchmark script) appends one
JSON line here. Read it back with `python scripts/token_report.py` for
per-agent / per-model averages.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = Path(__file__).parent.parent / "logs" / "token_usage.jsonl"
TOKEN_LOG_PATH = Path(os.getenv("TOKEN_LOG_PATH", str(_DEFAULT_LOG_PATH)))

_write_lock = threading.Lock()


def log_token_usage(
    *,
    role: str,
    agent: str,
    model: str,
    backend: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: float,
    audit_id: str | None = None,
) -> None:
    """Append one JSON line recording a single LLM call's token usage."""
    record: dict[str, Any] = {
        "ts": time.time(),
        "role": role,
        "agent": agent,
        "model": model,
        "backend": backend,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": round(latency_ms, 1),
        "audit_id": audit_id,
    }

    log.info(
        "tokens agent=%s model=%s total=%d (prompt=%d, completion=%d)",
        agent, model, total_tokens, prompt_tokens, completion_tokens,
    )

    line = json.dumps(record)
    with _write_lock:
        TOKEN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TOKEN_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
