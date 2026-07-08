from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.models.router import router
from app.schemas import AgentResult, Finding, SiteFacts

log = logging.getLogger(__name__)


class BaseAgent:
    """
    Shared plumbing for single-LLM-call agents (content_signal, structured_data, entity_topic).

    Subclasses implement:
      role: str               - ModelRouter role name
      agent_name: str         - value for AgentResult.agent
      build_messages(sitefacts) -> list[dict]
      parse_result(data, latency_ms, model, tokens) -> AgentResult
    """

    role: str = ""
    agent_name: str = ""

    async def run(self, sitefacts: SiteFacts) -> AgentResult:
        t0 = time.monotonic()
        messages = self.build_messages(sitefacts)

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = await router.call_with_fallback(
                    self.role,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=3000,
                )
                break
            except Exception as exc:
                last_exc = exc
                log.warning("%s attempt %d failed: %s", self.agent_name, attempt, exc)
        else:
            raise RuntimeError(f"{self.agent_name} failed after retries") from last_exc

        latency_ms = (time.monotonic() - t0) * 1000
        model_used = response["choices"][0].get("model", "unknown")
        tokens = response.get("usage", {}).get("total_tokens", 0)

        from app.models.client import _strip_markdown_fences
        raw = _strip_markdown_fences(response["choices"][0]["message"]["content"] or "{}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("%s returned invalid JSON; using defaults.", self.agent_name)
            data = {}

        return self.parse_result(data, latency_ms, model_used, tokens)

    def build_messages(self, sitefacts: SiteFacts) -> list[dict[str, Any]]:
        raise NotImplementedError

    def parse_result(self, data: dict[str, Any], latency_ms: float, model_used: str, tokens: int) -> AgentResult:
        raise NotImplementedError

    @staticmethod
    def _parse_findings(raw: list[dict]) -> list[Finding]:
        findings = []
        for f in raw:
            try:
                findings.append(Finding(**f))
            except Exception:
                pass
        return findings
