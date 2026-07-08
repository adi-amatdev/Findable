"""LLM Model Router — SCAFFOLD (not implemented).

One OpenAI-compatible interface in front of all model calls, with per-role model
selection and ordered failover (local vLLM -> remote Fireworks). Agents, the
orchestrator page-ranker, and the aggregator writer all call through it.
See okf/components/model-router.md.

`roles.py` already encodes the role->model routing table (reference data);
`router.py` defines the interface but does not perform calls yet.
"""

from .roles import ROLE_ROUTES, Role
from .router import ModelRouter

__all__ = ["Role", "ROLE_ROUTES", "ModelRouter"]
