"""
Load test for the Findable vLLM servers.

Tests:
  1. Health check  — both endpoints alive
  2. Cold start    — first-request latency (ROCm kernel compile)
  3. Warm single   — single request p50/p90/p99 latency
  4. Audit pattern — 4 concurrent requests (one full Findable audit cycle)
  5. Sustained     — N concurrent workers for T seconds (throughput/error rate)

Usage:
    python load_test.py                                 # local servers
    python load_test.py --heavy-url https://xxx.trycloudflare.com
    python load_test.py --light-url http://localhost:8000 --heavy-url http://localhost:8001
    python load_test.py --concurrency 8 --duration 60  # stress test
    python load_test.py --heavy-only                   # skip light model
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

import httpx

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_LIGHT_URL  = "http://localhost:8000"
DEFAULT_HEAVY_URL  = "http://localhost:8001"
LIGHT_MODEL_NAME   = "light"    # --served-model-name in start_service.sh
HEAVY_MODEL_NAME   = "heavy"

# Prompt typical of what each Findable agent sends
AGENT_PROMPTS = {
    "crawlability": (
        "You are an AI crawlability expert. Analyse the following site data and "
        "return a JSON assessment of how accessible this site is to AI crawlers.\n\n"
        "robots.txt: allow all bots. JS dependency ratio: 0.59. "
        "HTTP status: 200. Sitemap: present (87 URLs). "
        "Provide score (0-100) and top 3 findings."
    ),
    "content_signal": (
        "You are an E-E-A-T content analyst. Review this page data:\n"
        "word_count=640, byline_present=false, author_schema=false, "
        "outbound_citations=2. Score expertise, authority, trust (0-100 each) "
        "and list improvement actions as JSON."
    ),
    "structured_data": (
        "You are a structured data expert. Analyse: schema_types=['Organization','WebSite'], "
        "jsonld_valid=true, llms_txt_exists=false, og_title='Example Domain'. "
        "Return JSON with score and missing schema recommendations."
    ),
    "entity_topic": (
        "You are an entity and topic relevance analyst. "
        "entities=['Example Domain (ORG)', 'United States (GPE)', '2024 (DATE)']. "
        "internal_links=24, external_links=6. "
        "Return JSON with entity coverage score and topic coherence assessment."
    ),
}

MAX_TOKENS = 512

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    agent:       str
    success:     bool
    latency_s:   float
    ttft_s:      float | None = None   # time to first token (streaming)
    input_tokens:  int = 0
    output_tokens: int = 0
    error:       str = ""


@dataclass
class BenchResult:
    results:  list[RequestResult] = field(default_factory=list)

    @property
    def successes(self):
        return [r for r in self.results if r.success]

    @property
    def failures(self):
        return [r for r in self.results if not r.success]

    def latencies(self) -> list[float]:
        return sorted(r.latency_s for r in self.successes)

    def pct(self, p: float) -> float:
        lats = self.latencies()
        if not lats:
            return 0.0
        idx = max(0, int(len(lats) * p / 100) - 1)
        return lats[idx]

    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.successes)

    def tokens_per_second(self, elapsed: float) -> float:
        return self.total_output_tokens() / elapsed if elapsed > 0 else 0.0

# ---------------------------------------------------------------------------
# Core request
# ---------------------------------------------------------------------------

async def chat_completion(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    agent: str,
    stream: bool = False,
) -> RequestResult:
    prompt = AGENT_PROMPTS.get(agent, AGENT_PROMPTS["crawlability"])
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1,
        "stream": stream,
    }
    t0 = time.perf_counter()
    ttft = None
    output_tokens = 0
    input_tokens = 0

    try:
        if stream:
            async with client.stream(
                "POST", f"{base_url}/v1/chat/completions",
                json=payload, timeout=120.0,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            output_tokens += 1
                        usage = data.get("usage") or {}
                        input_tokens  = usage.get("prompt_tokens", input_tokens)
                        output_tokens = usage.get("completion_tokens", output_tokens)
                    except (json.JSONDecodeError, KeyError):
                        pass
        else:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload, timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            input_tokens  = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

        latency = time.perf_counter() - t0
        return RequestResult(
            agent=agent, success=True, latency_s=latency, ttft_s=ttft,
            input_tokens=input_tokens, output_tokens=output_tokens,
        )

    except Exception as exc:
        return RequestResult(
            agent=agent, success=False,
            latency_s=time.perf_counter() - t0,
            error=str(exc),
        )

# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"

def hdr(title: str):
    print(f"\n{BOLD}{CYAN}{title}{RESET}")
    print("-" * 55)

def ok(msg: str):  print(f"  {GREEN}OK{RESET}   {msg}")
def warn(msg: str): print(f"  {YELLOW}WARN{RESET} {msg}")
def err(msg: str): print(f"  {RED}FAIL{RESET} {msg}")

def print_latency_table(bench: BenchResult, elapsed: float):
    lats = bench.latencies()
    if not lats:
        err("No successful requests")
        return
    tps = bench.tokens_per_second(elapsed)
    print(f"  Requests : {len(bench.results)}  ({len(bench.successes)} ok, {len(bench.failures)} failed)")
    print(f"  Latency  : p50={bench.pct(50):.2f}s  p90={bench.pct(90):.2f}s  p99={bench.pct(99):.2f}s  min={min(lats):.2f}s  max={max(lats):.2f}s")
    print(f"  Tokens   : {bench.total_output_tokens()} output  ({tps:.1f} tok/s)")
    if bench.failures:
        for r in bench.failures[:3]:
            err(f"  {r.agent}: {r.error[:80]}")


async def test_health(light_url: str | None, heavy_url: str | None,
                      client: httpx.AsyncClient):
    hdr("1. Health check")
    for label, url in [("light", light_url), ("heavy", heavy_url)]:
        if url is None:
            continue
        try:
            resp = await client.get(f"{url}/health", timeout=10.0)
            resp.raise_for_status()
            ok(f"{label}  {url}/health  -> {resp.status_code}")
        except Exception as exc:
            err(f"{label}  {url}/health  -> {exc}")
            sys.exit(1)


async def test_models_endpoint(light_url: str | None, heavy_url: str | None,
                                client: httpx.AsyncClient):
    hdr("2. Models endpoint")
    for label, url, expected in [
        ("light", light_url, LIGHT_MODEL_NAME),
        ("heavy", heavy_url, HEAVY_MODEL_NAME),
    ]:
        if url is None:
            continue
        try:
            resp = await client.get(f"{url}/v1/models", timeout=10.0)
            resp.raise_for_status()
            ids = [m["id"] for m in resp.json()["data"]]
            ok(f"{label}  models={ids}")
            if expected not in ids:
                warn(f"  Expected served-model-name '{expected}' not found. "
                     f"Update LIGHT_MODEL_NAME / HEAVY_MODEL_NAME in this script.")
        except Exception as exc:
            err(f"{label}: {exc}")


async def test_single(url: str, model: str, label: str, n: int,
                      client: httpx.AsyncClient):
    hdr(f"3. Single-request latency  [{label}]  (n={n})")
    bench = BenchResult()
    agents = list(AGENT_PROMPTS.keys())
    t0 = time.perf_counter()
    for i in range(n):
        agent = agents[i % len(agents)]
        r = await chat_completion(client, url, model, agent, stream=False)
        bench.results.append(r)
        status = f"{GREEN}ok{RESET}" if r.success else f"{RED}FAIL{RESET}"
        print(f"  [{i+1}/{n}] {agent:<20} {status}  {r.latency_s:.2f}s  {r.output_tokens} tok")
    print_latency_table(bench, time.perf_counter() - t0)


async def test_audit_pattern(light_url: str | None, heavy_url: str | None,
                              client: httpx.AsyncClient, n_audits: int = 3):
    hdr(f"4. Full audit pattern  (4 agents × {n_audits} audit{'s' if n_audits>1 else ''})")
    print("  Fires all 4 agents simultaneously, as Findable does per audit.")

    async def one_audit(audit_num: int) -> list[RequestResult]:
        tasks = []
        for agent in AGENT_PROMPTS:
            # Route: crawlability -> light, others -> heavy (matches model router)
            if agent == "crawlability" and light_url:
                url, model = light_url, LIGHT_MODEL_NAME
            elif heavy_url:
                url, model = heavy_url, HEAVY_MODEL_NAME
            else:
                url, model = light_url, LIGHT_MODEL_NAME  # type: ignore
            tasks.append(chat_completion(client, url, model, agent, stream=False))
        results = await asyncio.gather(*tasks)
        wall = max(r.latency_s for r in results)
        statuses = " ".join(
            f"{r.agent[:4]}={'ok' if r.success else 'FAIL'}" for r in results
        )
        print(f"  audit {audit_num+1:>2}:  {statuses}  wall={wall:.2f}s")
        return list(results)

    all_results = BenchResult()
    t0 = time.perf_counter()
    for i in range(n_audits):
        results = await one_audit(i)
        all_results.results.extend(results)
    elapsed = time.perf_counter() - t0
    print()
    print_latency_table(all_results, elapsed)
    print(f"  Avg audit wall time: {elapsed/n_audits:.2f}s")


async def test_sustained(url: str, model: str, label: str,
                          concurrency: int, duration: int,
                          client: httpx.AsyncClient):
    hdr(f"5. Sustained load  [{label}]  concurrency={concurrency}  duration={duration}s")
    bench = BenchResult()
    stop_event = asyncio.Event()
    agents = list(AGENT_PROMPTS.keys())
    counter = [0]

    async def worker(worker_id: int):
        while not stop_event.is_set():
            agent = agents[counter[0] % len(agents)]
            counter[0] += 1
            r = await chat_completion(client, url, model, agent, stream=False)
            bench.results.append(r)

    tasks = [asyncio.create_task(worker(i)) for i in range(concurrency)]
    t0 = time.perf_counter()

    # Progress ticker
    async def ticker():
        while not stop_event.is_set():
            await asyncio.sleep(10)
            elapsed = time.perf_counter() - t0
            n_ok = len(bench.successes)
            n_fail = len(bench.failures)
            rps = n_ok / elapsed if elapsed > 0 else 0
            print(f"  t={elapsed:>4.0f}s  ok={n_ok:<4}  fail={n_fail:<3}  {rps:.2f} req/s")

    tick_task = asyncio.create_task(ticker())
    await asyncio.sleep(duration)
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    tick_task.cancel()

    elapsed = time.perf_counter() - t0
    print()
    print_latency_table(bench, elapsed)
    rps = len(bench.successes) / elapsed
    print(f"  Throughput: {rps:.2f} req/s  ({rps*60:.0f} req/min)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Findable vLLM load tester")
    parser.add_argument("--light-url",   default=DEFAULT_LIGHT_URL)
    parser.add_argument("--heavy-url",   default=DEFAULT_HEAVY_URL)
    parser.add_argument("--heavy-only",  action="store_true", help="Skip light model tests")
    parser.add_argument("--light-only",  action="store_true", help="Skip heavy model tests")
    parser.add_argument("--single-n",    type=int, default=5,
                        help="Requests for single-request test (default: 5)")
    parser.add_argument("--audit-n",     type=int, default=3,
                        help="Full audit cycles to run (default: 3)")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Workers for sustained test (default: 4)")
    parser.add_argument("--duration",    type=int, default=60,
                        help="Seconds for sustained test (default: 60)")
    parser.add_argument("--skip-sustained", action="store_true",
                        help="Skip the sustained load test")
    args = parser.parse_args()

    light_url = None if args.heavy_only else args.light_url
    heavy_url = None if args.light_only else args.heavy_url

    print(f"\n{BOLD}Findable vLLM Load Test{RESET}")
    if light_url: print(f"  Light: {light_url}  (model={LIGHT_MODEL_NAME})")
    if heavy_url: print(f"  Heavy: {heavy_url}  (model={HEAVY_MODEL_NAME})")

    async with httpx.AsyncClient() as client:
        await test_health(light_url, heavy_url, client)
        await test_models_endpoint(light_url, heavy_url, client)

        if light_url:
            await test_single(light_url, LIGHT_MODEL_NAME, "light",
                              args.single_n, client)
        if heavy_url:
            await test_single(heavy_url, HEAVY_MODEL_NAME, "heavy",
                              args.single_n, client)

        await test_audit_pattern(light_url, heavy_url, client, args.audit_n)

        if not args.skip_sustained:
            # Stress the heavy model — it's the bottleneck
            target_url   = heavy_url or light_url
            target_model = HEAVY_MODEL_NAME if heavy_url else LIGHT_MODEL_NAME
            target_label = "heavy" if heavy_url else "light"
            await test_sustained(target_url, target_model, target_label,  # type: ignore
                                  args.concurrency, args.duration, client)

    print(f"\n{BOLD}{GREEN}Load test complete.{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
