"""
Model Router — dual-endpoint vLLM + Fireworks + Ollama with startup discovery.

Priority (highest → lowest):
  1. vLLM (remote GPU, two separate cloudflared tunnels — heavy and light)
  2. Fireworks API  (cloud fallback, key required)
  3. Ollama         (local last resort)

Role → tier mapping:
  Light (2B) : orchestrator, crawlability_subagent, structured_data, entity_topic
  Heavy (9B) : crawlability_judgment, content_signal, report_writer

Configuration (all via env vars):
  VLLM_URL               heavy vLLM endpoint (cloudflared URL)
  VLLM_LIGHT_URL         light vLLM endpoint (cloudflared URL)
  VLLM_HEAVY_MODEL_NAME  served-model-name for heavy server  (default: "heavy")
  VLLM_LIGHT_MODEL_NAME  served-model-name for light server  (default: "light")
  FIREWORKS_KEY          Fireworks API key (omit to skip Fireworks)
  FIREWORKS_HEAVY_MODEL  Fireworks model for heavy roles
  FIREWORKS_LIGHT_MODEL  Fireworks model for light roles
  OLLAMA_URL             Ollama base URL  (default: http://localhost:11434)
  LOCAL_LIGHT_MODEL      Ollama model name for light roles  (default: gemma4:e2b)
  LOCAL_HEAVY_MODEL      Ollama model name for heavy roles  (default: gemma4:e2b)
  LOCAL_ONLY             Set to "1" to strip Fireworks from all chains
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

from app.models.client import AsyncLLMClient

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend config from environment
# ---------------------------------------------------------------------------

VLLM_HEAVY_BASE       = os.getenv("VLLM_URL", "").rstrip("/")
VLLM_LIGHT_BASE       = os.getenv("VLLM_LIGHT_URL", "").rstrip("/")
VLLM_HEAVY_MODEL_NAME = os.getenv("VLLM_HEAVY_MODEL_NAME", "heavy")
VLLM_LIGHT_MODEL_NAME = os.getenv("VLLM_LIGHT_MODEL_NAME", "light")

OLLAMA_BASE        = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_LIGHT_MODEL = os.getenv("LOCAL_LIGHT_MODEL", "gemma4:e2b")
OLLAMA_HEAVY_MODEL = os.getenv("LOCAL_HEAVY_MODEL", "gemma4:e2b")

FIREWORKS_BASE        = "https://api.fireworks.ai/inference"
FIREWORKS_KEY         = os.getenv("FIREWORKS_KEY", "")
FIREWORKS_HEAVY_MODEL = os.getenv(
    "FIREWORKS_HEAVY_MODEL", "accounts/fireworks/models/gemma-4-27b-it"
)
FIREWORKS_LIGHT_MODEL = os.getenv(
    "FIREWORKS_LIGHT_MODEL", "accounts/fireworks/models/gemma-4-e4b-it"
)

_local_only = os.getenv("LOCAL_ONLY", "0") == "1"

# ---------------------------------------------------------------------------
# Mutable backend availability state — updated by probe_backends()
# ---------------------------------------------------------------------------

_backend_ok: dict[str, bool] = {
    "vllm_heavy": False,
    "vllm_light": False,
    "fireworks":  False,
    "ollama":     False,
}

# Roles that use the heavy (9B) model
HEAVY_ROLES: frozenset[str] = frozenset(
    {"crawlability_judgment", "content_signal", "report_writer"}
)


# ---------------------------------------------------------------------------
# Startup probe — called once from FastAPI lifespan
# ---------------------------------------------------------------------------

async def probe_backends() -> dict[str, bool]:
    """Probe each backend and update _backend_ok. Returns a copy of the state."""
    async with httpx.AsyncClient() as client:
        for key, url, path in [
            ("vllm_heavy", VLLM_HEAVY_BASE, "/v1/models"),
            ("vllm_light", VLLM_LIGHT_BASE, "/v1/models"),
            ("ollama",     OLLAMA_BASE,      "/api/tags"),
        ]:
            if not url:
                _backend_ok[key] = False
                log.info("Backend %-12s not configured (env var empty)", key)
                continue
            try:
                r = await client.get(f"{url}{path}", timeout=8.0)
                _backend_ok[key] = r.status_code < 400
                log.info(
                    "Backend %-12s %s  (%s%s → %s)",
                    key,
                    "OK" if _backend_ok[key] else "UNREACHABLE",
                    url, path, r.status_code,
                )
            except Exception as exc:
                _backend_ok[key] = False
                log.warning("Backend %-12s UNREACHABLE  %s%s — %s", key, url, path, exc)

        _backend_ok["fireworks"] = bool(FIREWORKS_KEY) and not _local_only
        log.info(
            "Backend %-12s %s",
            "fireworks",
            "OK (key set)" if _backend_ok["fireworks"] else "skipped (no key or LOCAL_ONLY)",
        )

    log.info("Backend availability: %s", _backend_ok)
    return dict(_backend_ok)


# ---------------------------------------------------------------------------
# Model spec + chain builder
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    base_url: str
    model: str
    api_key: str = ""


def _build_chain(role: str) -> list[ModelSpec]:
    """Build a fallback chain for *role* based on current _backend_ok state.

    Priority: vLLM → Fireworks → Ollama.
    Heavy roles use the heavy vLLM endpoint; all others use the light endpoint.
    """
    heavy = role in HEAVY_ROLES
    specs: list[ModelSpec] = []

    if heavy:
        if _backend_ok["vllm_heavy"] and VLLM_HEAVY_BASE:
            specs.append(ModelSpec(VLLM_HEAVY_BASE, VLLM_HEAVY_MODEL_NAME))
        if _backend_ok["fireworks"]:
            specs.append(ModelSpec(FIREWORKS_BASE, FIREWORKS_HEAVY_MODEL, FIREWORKS_KEY))
        if _backend_ok["ollama"]:
            specs.append(ModelSpec(OLLAMA_BASE, OLLAMA_HEAVY_MODEL))
    else:
        if _backend_ok["vllm_light"] and VLLM_LIGHT_BASE:
            specs.append(ModelSpec(VLLM_LIGHT_BASE, VLLM_LIGHT_MODEL_NAME))
        if _backend_ok["fireworks"]:
            specs.append(ModelSpec(FIREWORKS_BASE, FIREWORKS_LIGHT_MODEL, FIREWORKS_KEY))
        if _backend_ok["ollama"]:
            specs.append(ModelSpec(OLLAMA_BASE, OLLAMA_LIGHT_MODEL))

    if not specs:
        log.warning(
            "No backends available for role '%s' (all probes failed). "
            "Check VLLM_URL / VLLM_LIGHT_URL / FIREWORKS_KEY / OLLAMA_URL.",
            role,
        )

    return specs


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------

class ModelRouter:
    def get_chain(self, role: str) -> list[tuple[AsyncLLMClient, str]]:
        return [
            (AsyncLLMClient(s.base_url, s.api_key), s.model)
            for s in _build_chain(role)
        ]

    async def call_with_fallback(self, role: str, **kwargs) -> dict:
        chain = self.get_chain(role)
        if not chain:
            raise RuntimeError(
                f"No model backend available for role '{role}'. "
                "All backends are unreachable — check VLLM_URL, FIREWORKS_KEY, OLLAMA_URL."
            )

        last_exc: Exception | None = None
        for client, model in chain:
            try:
                return await client.chat_completion(model=model, **kwargs)
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                log.warning(
                    "Role '%s' model '%s' at '%s' failed (%s) — trying next fallback",
                    role, model, client._base_url, type(exc).__name__,
                )
                last_exc = exc
                continue

        raise RuntimeError(
            f"All model fallbacks exhausted for role '{role}'"
        ) from last_exc


router = ModelRouter()
