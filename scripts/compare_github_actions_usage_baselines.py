#!/usr/bin/env python3
"""Compare two GitHub Actions baseline snapshots and emit deltas."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _to_map(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = baseline.get("top_by_runtime_minutes") or []
    out: dict[str, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        name = row.get("workflow_name")
        if isinstance(name, str) and name:
            out[name] = row
    return out


def _num(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def compare(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_map = _to_map(previous)
    curr_map = _to_map(current)
    names = sorted(set(prev_map) | set(curr_map))

    deltas: list[dict[str, Any]] = []
    for name in names:
        prev = prev_map.get(name, {})
        curr = curr_map.get(name, {})
        runtime_prev = _num(prev, "runtime_minutes_total")
        runtime_curr = _num(curr, "runtime_minutes_total")
        runs_prev = _num(prev, "runs")
        runs_curr = _num(curr, "runs")
        failed_prev = _num(prev, "failed")
        failed_curr = _num(curr, "failed")
        deltas.append(
            {
                "workflow_name": name,
                "runtime_minutes_total_prev": round(runtime_prev, 2),
                "runtime_minutes_total_curr": round(runtime_curr, 2),
                "runtime_minutes_delta": round(runtime_curr - runtime_prev, 2),
                "runs_prev": int(runs_prev),
                "runs_curr": int(runs_curr),
                "runs_delta": int(runs_curr - runs_prev),
                "failed_prev": int(failed_prev),
                "failed_curr": int(failed_curr),
                "failed_delta": int(failed_curr - failed_prev),
            }
        )

    deltas.sort(key=lambda x: abs(x["runtime_minutes_delta"]), reverse=True)
    return {
        "schema": "github_actions_usage_delta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "previous_generated_at_utc": previous.get("generated_at_utc"),
        "current_generated_at_utc": current.get("generated_at_utc"),
        "window_prev_runs": previous.get("input_run_count"),
        "window_curr_runs": current.get("input_run_count"),
        "workflow_deltas": deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-json", required=True)
    parser.add_argument("--current-json", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    prev_path = Path(args.previous_json)
    curr_path = Path(args.current_json)
    out_path = Path(args.output_json)

    previous = _load(prev_path)
    current = _load(curr_path)
    payload = compare(previous, current)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
