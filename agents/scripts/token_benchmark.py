"""
Token usage benchmark — measures average tokens consumed per agent role and
per model, calling the real vLLM endpoints (heavy + light) directly.

Bypasses ModelRouter's Fireworks/Ollama fallback on purpose: this is a
targeted benchmark of the two vLLM-served Gemma models, not a production
call path.

Usage:
    python scripts/token_benchmark.py \
        --vllm-url https://heavy-tunnel.example.com \
        --vllm-light-url https://light-tunnel.example.com \
        --runs 5

Run from the `agents/` directory (or anywhere — the script fixes up
sys.path itself).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.content_signal import ContentSignalAgent  # noqa: E402
from app.agents.crawlability.agent import _build_judgment_prompt  # noqa: E402
from app.agents.entity_topic import EntityTopicAgent  # noqa: E402
from app.agents.structured_data import StructuredDataAgent  # noqa: E402
from app.models.client import AsyncLLMClient  # noqa: E402
from app.report.aggregator import build_summary_prompt  # noqa: E402
from app.schemas import Finding, PageResult, SiteFacts, TrafficSignal, Visibility, VisibilityEstimate  # noqa: E402
from app.token_logger import log_token_usage  # noqa: E402
from tests.conftest import CANNED_SITEFACTS_DICT  # noqa: E402

BenchmarkResult = dict[str, Any]


def _crawlability_messages(sf: SiteFacts) -> list[dict[str, Any]]:
    prompt = _build_judgment_prompt(sf, crawl_reports=[], traffic_signal=TrafficSignal(source="unavailable"))
    return [
        {
            "role": "system",
            "content": (
                "You are a crawlability auditor evaluating how well AI search crawlers "
                "can access and index a website. Respond only with valid JSON matching "
                "the requested schema."
            ),
        },
        {"role": "user", "content": prompt},
    ]


def _report_writer_messages(_sf: SiteFacts) -> list[dict[str, Any]]:
    dummy_findings = [
        Finding(
            id="f1", title="Missing schema markup", severity=4, effort="S",
            impact=4, detail="No Article schema detected", fix="Add JSON-LD Article schema",
            evidence="structured_data.schema_types is empty",
        ),
        Finding(
            id="f2", title="JS-gated content", severity=3, effort="M",
            impact=3, detail="30% of content requires JS to render",
            fix="Server-render primary content", evidence="js_dependency_ratio=0.3",
        ),
    ]
    empty_vis = VisibilityEstimate()
    page = PageResult(
        url="https://example.com", role="landing", ai_readiness_score=68,
        category_scores={"crawlability": 70, "content_signal": 65, "structured_data": 60, "entity_topic": 72},
        visibility=Visibility(before=empty_vis, after=empty_vis),
        fixes=dummy_findings, agent_results=[],
    )
    prompt = build_summary_prompt([page], site_score=68)
    return [
        {"role": "system", "content": "You write concise, grounded audit summaries."},
        {"role": "user", "content": prompt},
    ]


# role -> (tier, agent_label, response_format, temperature, max_tokens, messages_fn)
ROLE_SPECS: dict[str, tuple[str, str, dict | None, float, int, Callable[[SiteFacts], list[dict[str, Any]]]]] = {
    "crawlability_judgment": (
        "heavy", "crawlability", {"type": "json_object"}, 0.1, 3000, _crawlability_messages,
    ),
    "content_signal": (
        "heavy", "content_signal", {"type": "json_object"}, 0.1, 3000,
        lambda sf: ContentSignalAgent().build_messages(sf),
    ),
    "report_writer": (
        "heavy", "report_writer", None, 0.3, 300, _report_writer_messages,
    ),
    "structured_data": (
        "light", "structured_data", {"type": "json_object"}, 0.1, 3000,
        lambda sf: StructuredDataAgent().build_messages(sf),
    ),
    "entity_topic": (
        "light", "entity_topic", {"type": "json_object"}, 0.1, 3000,
        lambda sf: EntityTopicAgent().build_messages(sf),
    ),
}


async def _benchmark_role(
    role: str,
    tier: str,
    agent_label: str,
    response_format: dict | None,
    temperature: float,
    max_tokens: int,
    messages: list[dict[str, Any]],
    client: AsyncLLMClient,
    model: str,
    runs: int,
) -> BenchmarkResult:
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    total_tokens: list[int] = []
    failures = 0

    for _ in range(runs):
        try:
            response = await client.chat_completion(
                messages=messages, model=model, temperature=temperature,
                max_tokens=max_tokens, response_format=response_format,
            )
        except Exception as exc:  # noqa: BLE001 — benchmark keeps going on per-run failures
            print(f"  ! run failed for role={role}: {exc}")
            failures += 1
            continue

        usage = response.get("usage", {}) or {}
        pt, ct, tt = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0)
        prompt_tokens.append(pt)
        completion_tokens.append(ct)
        total_tokens.append(tt)

        log_token_usage(
            role=role, agent=agent_label, model=model, backend=client._base_url,
            prompt_tokens=pt, completion_tokens=ct, total_tokens=tt,
            latency_ms=response.get("_latency_ms", 0.0), audit_id="benchmark",
        )

    return {
        "role": role,
        "agent": agent_label,
        "tier": tier,
        "model": model,
        "runs_ok": len(total_tokens),
        "runs_failed": failures,
        "avg_prompt_tokens": round(statistics.mean(prompt_tokens), 1) if prompt_tokens else 0,
        "avg_completion_tokens": round(statistics.mean(completion_tokens), 1) if completion_tokens else 0,
        "avg_total_tokens": round(statistics.mean(total_tokens), 1) if total_tokens else 0,
        "min_total_tokens": min(total_tokens) if total_tokens else 0,
        "max_total_tokens": max(total_tokens) if total_tokens else 0,
    }


async def run_benchmark(
    vllm_heavy_url: str, vllm_light_url: str, heavy_model: str, light_model: str, runs: int,
) -> list[BenchmarkResult]:
    sf = SiteFacts.model_validate(CANNED_SITEFACTS_DICT)
    heavy_client = AsyncLLMClient(vllm_heavy_url)
    light_client = AsyncLLMClient(vllm_light_url)

    results: list[BenchmarkResult] = []
    for role, (tier, agent_label, response_format, temperature, max_tokens, messages_fn) in ROLE_SPECS.items():
        client = heavy_client if tier == "heavy" else light_client
        model = heavy_model if tier == "heavy" else light_model
        messages = messages_fn(sf)
        print(f"Benchmarking role={role} tier={tier} model={model} ({runs} runs)...")
        result = await _benchmark_role(
            role, tier, agent_label, response_format, temperature, max_tokens,
            messages, client, model, runs,
        )
        results.append(result)

    return results


def _print_table(results: list[BenchmarkResult]) -> None:
    header = f"{'role':<22}{'model':<10}{'runs':<8}{'avg prompt':<12}{'avg completion':<16}{'avg total':<12}{'min/max total':<14}"
    print("\n" + header)
    print("-" * len(header))
    for r in results:
        runs_str = f"{r['runs_ok']}/{r['runs_ok'] + r['runs_failed']}"
        minmax = f"{r['min_total_tokens']}/{r['max_total_tokens']}"
        print(
            f"{r['role']:<22}{r['model']:<10}{runs_str:<8}"
            f"{r['avg_prompt_tokens']:<12}{r['avg_completion_tokens']:<16}"
            f"{r['avg_total_tokens']:<12}{minmax:<14}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vllm-url", required=True, help="Heavy vLLM endpoint (cloudflared URL)")
    parser.add_argument("--vllm-light-url", required=True, help="Light vLLM endpoint (cloudflared URL)")
    parser.add_argument("--heavy-model", default="heavy", help="Served-model-name on the heavy endpoint")
    parser.add_argument("--light-model", default="light", help="Served-model-name on the light endpoint")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per agent role")
    parser.add_argument("--out", type=Path, default=None, help="Optional path to dump the JSON summary")
    args = parser.parse_args()

    results = asyncio.run(
        run_benchmark(args.vllm_url, args.vllm_light_url, args.heavy_model, args.light_model, args.runs)
    )
    _print_table(results)

    if args.out:
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Summary written to {args.out}")


if __name__ == "__main__":
    main()
