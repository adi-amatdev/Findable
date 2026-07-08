"""BaseAgent interface. SCAFFOLD — concrete agents are not implemented yet."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.contracts import AgentResult, SiteFacts


class BaseAgent(ABC):
    """Contract every agent implements: SiteFacts in, AgentResult out.

    Subclasses set `name` (matches AgentResult.agent) and `weight` (its share of
    the AI Readiness Score). See okf/data/agent-result.md.
    """

    name: str = ""
    weight: float = 0.0

    @abstractmethod
    async def run(self, facts: SiteFacts) -> AgentResult:
        """Judge the facts (+ facts.markdown) and return an AgentResult.

        NOT IMPLEMENTED — this is the next layer to build. See the per-agent
        specs under okf/agents/.
        """
        raise NotImplementedError
