"""
Model Router — dual-backend support.

Typical setups:
  1. Local only (dry run):
       OLLAMA_URL=http://localhost:11434  LOCAL_LIGHT_MODEL=gemma4:e2b  LOCAL_ONLY=1
  2. Ollama (light) + remote vLLM (heavy):
       OLLAMA_URL=http://localhost:11434
       VLLM_URL=https://<ngrok-or-cloudflared-url>  LOCAL_HEAVY_MODEL=google/gemma-4-27b-it
  3. Ollama + vLLM + Fireworks (full prod):
       all of the above + FIREWORKS_KEY=fw_...

Role assignment:
  - Light roles (sub-agent, orchestrator) → Ollama (always local, fast)
  - Heavy roles (judgment, content, writer) → vLLM if VLLM_URL set, else Ollama, else Fireworks
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.models.client import AsyncLLMClient

# ---------------------------------------------------------------------------
# Backend config from environment
# ---------------------------------------------------------------------------

OLLAMA_BASE   = os.getenv("OLLAMA_URL", "http://localhost:11434")
VLLM_BASE     = os.getenv("VLLM_URL", "")          # empty = not configured
FIREWORKS_BASE = "https://api.fireworks.ai/inference"
FIREWORKS_KEY  = os.getenv("FIREWORKS_KEY", "")

LIGHT_MODEL = os.getenv("LOCAL_LIGHT_MODEL", "gemma4:e2b")
HEAVY_MODEL = os.getenv("LOCAL_HEAVY_MODEL", "google/gemma-4-27b-it")
MID_MODEL   = os.getenv("LOCAL_MID_MODEL",   "Qwen/Qwen3-14B")

# When no VLLM_URL is set, heavy roles fall back to the light model on Ollama
_vllm_available = bool(VLLM_BASE)
_local_only = os.getenv("LOCAL_ONLY", "0") == "1"


@dataclass
class ModelSpec:
    base_url: str
    model: str
    api_key: str = ""


# ---------------------------------------------------------------------------
# Spec builders
# ---------------------------------------------------------------------------

def _ollama(model: str = LIGHT_MODEL) -> ModelSpec:
    return ModelSpec(OLLAMA_BASE, model)


def _vllm(model: str = HEAVY_MODEL) -> ModelSpec:
    """Return vLLM spec. Only call this when VLLM_URL is set."""
    return ModelSpec(VLLM_BASE, model)


def _fireworks(model: str = "accounts/fireworks/models/gemma-4-27b-it") -> ModelSpec:
    return ModelSpec(FIREWORKS_BASE, model, FIREWORKS_KEY)


def _chain(*specs: ModelSpec) -> list[ModelSpec]:
    """Drop Fireworks entries when LOCAL_ONLY=1."""
    if _local_only:
        return [s for s in specs if FIREWORKS_BASE not in s.base_url]
    return list(specs)


# ---------------------------------------------------------------------------
# Role → ordered fallback chain
# ---------------------------------------------------------------------------
# Light roles always go to Ollama (no need for vLLM for sub-agent work).
# Heavy roles: vLLM → Ollama → Fireworks

def _heavy_chain(*fw_models: str) -> list[ModelSpec]:
    """Build a fallback chain for a heavy role."""
    specs: list[ModelSpec] = []
    if _vllm_available:
        specs.append(_vllm(HEAVY_MODEL))
        specs.append(_vllm(MID_MODEL if MID_MODEL != HEAVY_MODEL else HEAVY_MODEL))
    specs.append(_ollama(LIGHT_MODEL))          # Ollama fallback for any role
    if fw_models and not _local_only:
        for m in fw_models:
            specs.append(_fireworks(m))
    return specs


ROLE_CHAIN: dict[str, list[ModelSpec]] = {
    # Light: always Ollama
    "orchestrator": _chain(_ollama()),
    "crawlability_subagent": _chain(_ollama()),

    # Heavy: vLLM → Ollama → Fireworks
    "crawlability_judgment": _heavy_chain(
        "accounts/fireworks/models/gemma-4-27b-it",
    ),
    "content_signal": _chain(
        *([_vllm(HEAVY_MODEL)] if _vllm_available else []),
        _ollama(),
        _fireworks("accounts/fireworks/models/gemma-4-27b-it"),
    ),
    "structured_data": _chain(
        *([_vllm(MID_MODEL)] if _vllm_available else []),
        _ollama(),
        _fireworks("accounts/fireworks/models/gemma-4-e4b-it"),
    ),
    "entity_topic": _chain(
        *([_vllm(MID_MODEL)] if _vllm_available else []),
        _ollama(),
        _fireworks("accounts/fireworks/models/gemma-4-27b-it"),
    ),
    "report_writer": _chain(
        *([_vllm(HEAVY_MODEL)] if _vllm_available else []),
        _ollama(),
        _fireworks("accounts/fireworks/models/gemma-4-27b-it"),
    ),
}


class ModelRouter:
    def get_chain(self, role: str) -> list[tuple[AsyncLLMClient, str]]:
        return [
            (AsyncLLMClient(s.base_url, s.api_key), s.model)
            for s in ROLE_CHAIN.get(role, [_ollama()])
        ]

    async def call_with_fallback(self, role: str, **kwargs) -> dict:
        import httpx

        chain = self.get_chain(role)
        last_exc: Exception | None = None
        for client, model in chain:
            try:
                return await client.chat_completion(model=model, **kwargs)
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                continue
        raise RuntimeError(f"All model fallbacks exhausted for role '{role}'") from last_exc


router = ModelRouter()
