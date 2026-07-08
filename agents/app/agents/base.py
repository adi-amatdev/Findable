from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.models.router import router
from app.schemas import AgentResult, AgentStatusEvent, Finding, SiteFacts
import app.state as state

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

    async def run(self, sitefacts: SiteFacts, agent_id: str | None = None) -> AgentResult:
        async def _emit(phase: str, detail: str | None = None, score: int | None = None) -> None:
            if agent_id:
                await state.emit(agent_id, AgentStatusEvent(
                    agent_id=agent_id, agent=self.agent_name,
                    phase=phase, detail=detail, score=score,
                ))

        await _emit("started")
        t0 = time.monotonic()

        await _emit("building_prompt")
        messages = self.build_messages(sitefacts)

        last_exc: Exception | None = None
        for attempt in range(2):
            if attempt > 0:
                await _emit("retry", detail=str(attempt + 1))
            await _emit("llm_call", detail=self.role)
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
            await _emit("error", detail=str(last_exc))
            raise RuntimeError(f"{self.agent_name} failed after retries") from last_exc

        latency_ms = (time.monotonic() - t0) * 1000
        model_used = response["choices"][0].get("model", "unknown")
        tokens = response.get("usage", {}).get("total_tokens", 0)

        from app.models.client import _strip_markdown_fences
        raw = _strip_markdown_fences(response["choices"][0]["message"]["content"] or "{}")

        await _emit("parsing_result")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("%s returned invalid JSON; using defaults.", self.agent_name)
            data = {}

        result = self.parse_result(data, latency_ms, model_used, tokens)
        await _emit("complete", score=result.score)
        return result

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
