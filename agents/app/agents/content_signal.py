from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResult, SiteFacts

_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "content_signal.md").read_text(encoding="utf-8")


class ContentSignalAgent(BaseAgent):
    role = "content_signal"
    agent_name = "content_signal"

    def build_messages(self, sitefacts: SiteFacts) -> list[dict[str, Any]]:
        prompt = _PROMPT.format(
            url=sitefacts.url,
            word_count=sitefacts.html.word_count,
            byline_present=sitefacts.authorship.byline_present,
            author_schema=sitefacts.authorship.author_schema,
            date_published=sitefacts.authorship.dates.published or "unknown",
            date_modified=sitefacts.authorship.dates.modified or "unknown",
            outbound_citations=sitefacts.links.outbound_citations,
            schema_types=", ".join(sitefacts.structured_data.schema_types) or "none",
            page_excerpt=sitefacts.page_markdown[:4000],
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are an E-E-A-T auditor. Evaluate the page strictly based on "
                    "Google's Quality Rater Guidelines. Return only valid JSON."
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
        sub_scores = data.get("sub_scores", {})
        if sub_scores:
            score = round(
                0.25 * sub_scores.get("experience", 50)
                + 0.25 * sub_scores.get("expertise", 50)
                + 0.25 * sub_scores.get("authority", 50)
                + 0.25 * sub_scores.get("trust", 50)
            )
        else:
            score = max(0, min(100, int(data.get("score", 50))))

        commodity = data.get("commodity_content", False)
        # Enforce commodity content cap (prompt instructs this, but guard here too)
        if commodity:
            score = min(score, 60)

        return AgentResult(
            agent=self.agent_name,
            score=score,
            sub_scores={k: int(v) for k, v in sub_scores.items()},
            findings=self._parse_findings(data.get("findings", [])),
            artifacts={
                "citation_worthy": data.get("citation_worthy", False),
                "answer_front_loaded": data.get("answer_front_loaded", False),
                "commodity_content": commodity,
            },
            model_used=model_used,
            latency_ms=round(latency_ms, 1),
            tokens=tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
