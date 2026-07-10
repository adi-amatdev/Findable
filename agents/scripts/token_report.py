"""
Token usage report — reads back agents/logs/token_usage.jsonl (written by
app.token_logger during real audits and by scripts/token_benchmark.py) and
prints average / min / max tokens grouped by agent and by model.

Usage:
    python scripts/token_report.py
    python scripts/token_report.py --log-path /custom/path/token_usage.jsonl
    python scripts/token_report.py --audit-id benchmark   # filter to one audit_id
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.token_logger import TOKEN_LOG_PATH  # noqa: E402


def _load_records(log_path: Path, audit_id: str | None) -> list[dict]:
    if not log_path.exists():
        return []
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if audit_id is not None and record.get("audit_id") != audit_id:
            continue
        records.append(record)
    return records


def _summarize(records: list[dict], key: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        grouped[r.get(key, "unknown")].append(r)

    summary = []
    for name, group in sorted(grouped.items()):
        totals = [g["total_tokens"] for g in group]
        prompts = [g["prompt_tokens"] for g in group]
        completions = [g["completion_tokens"] for g in group]
        summary.append({
            key: name,
            "calls": len(group),
            "avg_prompt_tokens": round(statistics.mean(prompts), 1),
            "avg_completion_tokens": round(statistics.mean(completions), 1),
            "avg_total_tokens": round(statistics.mean(totals), 1),
            "min_total_tokens": min(totals),
            "max_total_tokens": max(totals),
        })
    return summary


def _print_table(title: str, rows: list[dict], key: str) -> None:
    print(f"\n=== {title} ===")
    header = f"{key:<20}{'calls':<8}{'avg prompt':<12}{'avg completion':<16}{'avg total':<12}{'min/max total':<14}"
    print(header)
    print("-" * len(header))
    for r in rows:
        minmax = f"{r['min_total_tokens']}/{r['max_total_tokens']}"
        print(
            f"{r[key]:<20}{r['calls']:<8}{r['avg_prompt_tokens']:<12}"
            f"{r['avg_completion_tokens']:<16}{r['avg_total_tokens']:<12}{minmax:<14}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-path", type=Path, default=TOKEN_LOG_PATH)
    parser.add_argument("--audit-id", type=str, default=None, help="Filter to a single audit_id")
    args = parser.parse_args()

    records = _load_records(args.log_path, args.audit_id)
    if not records:
        print(f"No token usage records found at {args.log_path}")
        return

    print(f"Loaded {len(records)} record(s) from {args.log_path}")
    _print_table("By agent", _summarize(records, "agent"), "agent")
    _print_table("By model", _summarize(records, "model"), "model")
    print()


if __name__ == "__main__":
    main()
