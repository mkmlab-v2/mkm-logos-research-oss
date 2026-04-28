#!/usr/bin/env python3
"""Summarize recent GitHub Actions runtime usage from gh run list JSON."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class WorkflowStats:
    runs: int = 0
    runtime_minutes: float = 0.0
    success: int = 0
    failed: int = 0
    other: int = 0
    event_counts: Counter = field(default_factory=Counter)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, TS_FMT)
    except ValueError:
        return None


def _classify_conclusion(conclusion: str | None) -> str:
    value = (conclusion or "").lower()
    if value == "success":
        return "success"
    if value in {"failure", "timed_out", "startup_failure", "action_required"}:
        return "failed"
    return "other"


def build_summary(runs: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    per_workflow: dict[str, WorkflowStats] = defaultdict(WorkflowStats)
    for run in runs:
        created = _parse_ts(run.get("createdAt"))
        updated = _parse_ts(run.get("updatedAt"))
        if created is None or updated is None:
            continue

        runtime_minutes = max((updated - created).total_seconds() / 60.0, 0.0)
        name = run.get("workflowName") or "unknown"
        event = run.get("event") or "unknown"
        outcome = _classify_conclusion(run.get("conclusion"))

        stats = per_workflow[name]
        stats.runs += 1
        stats.runtime_minutes += runtime_minutes
        stats.event_counts[event] += 1
        if outcome == "success":
            stats.success += 1
        elif outcome == "failed":
            stats.failed += 1
        else:
            stats.other += 1

    sorted_items = sorted(
        per_workflow.items(),
        key=lambda item: item[1].runtime_minutes,
        reverse=True,
    )
    top = []
    for name, stats in sorted_items[:top_n]:
        top.append(
            {
                "workflow_name": name,
                "runs": stats.runs,
                "runtime_minutes_total": round(stats.runtime_minutes, 2),
                "runtime_minutes_avg": round(stats.runtime_minutes / max(stats.runs, 1), 2),
                "success": stats.success,
                "failed": stats.failed,
                "other": stats.other,
                "events": dict(stats.event_counts.most_common()),
            }
        )

    return {
        "schema": "github_actions_usage_baseline_v1",
        "generated_at_utc": datetime.utcnow().strftime(TS_FMT),
        "input_run_count": len(runs),
        "workflow_count": len(per_workflow),
        "top_by_runtime_minutes": top,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", required=True, help="Path to gh run list JSON export")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--output-json", required=False)
    args = parser.parse_args()

    input_path = Path(args.input_json)
    runs = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if not isinstance(runs, list):
        raise ValueError("Expected a JSON array from gh run list --json")

    summary = build_summary(runs, max(args.top_n, 1))
    text = json.dumps(summary, ensure_ascii=False, indent=2)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(f"WROTE: {output_path}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
