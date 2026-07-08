"""ModelRouter interface. SCAFFOLD — call path not implemented yet.

When built, `complete()` will: resolve the role's failover chain from
ROLE_ROUTES, try each (model, backend) in order over an OpenAI-compatible HTTP
call (vLLM locally, Fireworks remotely), cache responses by prompt hash, and
return the first success. Today it raises so callers fail loudly rather than
silently returning fake text.
"""

from __future__ import annotations

from typing import Optional

from ..config import Settings
from .roles import ROLE_ROUTES, Role


class ModelRouter:
    def __init__(self, settings: Settings):
        self._settings = settings

    def route(self, role: Role) -> list[tuple[str, str]]:
        """Return the ordered (model, backend) failover chain for a role."""
        return ROLE_ROUTES[role]

    async def complete(self, role: Role, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError(
            "ModelRouter is scaffolded. Wire vLLM/Fireworks and set LLM_ENABLED=true "
            "to enable. See okf/components/model-router.md."
        )
