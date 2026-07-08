from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResult, SiteFacts

_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "structured_data.md").read_text(encoding="utf-8")


class StructuredDataAgent(BaseAgent):
    role = "structured_data"
    agent_name = "structured_data"

    def build_messages(self, sitefacts: SiteFacts) -> list[dict[str, Any]]:
        prompt = _PROMPT.format(
            url=sitefacts.url,
            schema_types=", ".join(sitefacts.structured_data.schema_types) or "none",
            jsonld_valid=sitefacts.structured_data.jsonld_valid,
            jsonld_errors=", ".join(sitefacts.structured_data.errors) or "none",
            llms_txt_exists=sitefacts.llms_txt.exists,
            llms_txt_valid=sitefacts.llms_txt.valid,
            llms_txt_has_summary=sitefacts.llms_txt.has_summary,
            og_title=sitefacts.html.og.get("title", ""),
            og_description=sitefacts.html.og.get("description", ""),
            meta_description=sitefacts.html.meta_description,
            twitter_card=sitefacts.html.twitter.get("card", ""),
            jsonld_raw="none detected",
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are a structured data specialist. Evaluate schema markup and "
                    "meta tags for AI-search readiness. Return only valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]

    def parse_result(self, data: dict, latency_ms: float, model_used: str, tokens: int) -> AgentResult:
        return AgentResult(
            agent=self.agent_name,
            score=max(0, min(100, int(data.get("score", 50)))),
            findings=self._parse_findings(data.get("findings", [])),
            model_used=model_used,
            latency_ms=round(latency_ms, 1),
            tokens=tokens,
        )
