from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResult, SiteFacts

_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "entity_topic.md").read_text(encoding="utf-8")


class EntityTopicAgent(BaseAgent):
    role = "entity_topic"
    agent_name = "entity_topic"

    def build_messages(self, sitefacts: SiteFacts) -> list[dict[str, Any]]:
        entities_text = "\n".join(
            f"- {e.text} ({e.label})" for e in sitefacts.entities_raw[:50]
        ) or "none detected"

        prompt = _PROMPT.format(
            url=sitefacts.url,
            internal_links=sitefacts.links.internal,
            entities=entities_text,
            page_excerpt=sitefacts.page_markdown[:3000],
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are an entity and topic authority auditor. Build a knowledge graph "
                    "and identify entity disambiguation gaps. Return only valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]

    def parse_result(
        self,
        data: dict,
        latency_ms: float,
        model_used: str,
        tokens: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> AgentResult:
        return AgentResult(
            agent=self.agent_name,
            score=max(0, min(100, int(data.get("score", 50)))),
            findings=self._parse_findings(data.get("findings", [])),
            artifacts=data.get("artifacts", {}),
            model_used=model_used,
            latency_ms=round(latency_ms, 1),
            tokens=tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
