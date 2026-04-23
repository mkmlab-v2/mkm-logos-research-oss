#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build consistency check for last N canon chain runs.")
    ap.add_argument(
        "--gate-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    ap.add_argument(
        "--insight-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    ap.add_argument(
        "--health-policy-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1.json",
    )
    ap.add_argument(
        "--insight-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_quality_gate_v1.json",
    )
    ap.add_argument(
        "--insight-delta-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_delta_summary_v1.json",
    )
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_operational_consistency_check_v1.json",
    )
    args = ap.parse_args()

    gate_hist = _read_jsonl(Path(args.gate_history_jsonl))
    insight_hist = _read_jsonl(Path(args.insight_history_jsonl))
    health_policy = _read_json(Path(args.health_policy_json))
    insight_gate = _read_json(Path(args.insight_gate_json))
    insight_delta = _read_json(Path(args.insight_delta_json))

    w = int(args.window)
    gate_recent = gate_hist[-w:]
    insight_recent = insight_hist[-w:]

    gate_all_pass = len(gate_recent) == w and all(x.get("result") == "pass" for x in gate_recent)
    insight_rows_stable = False
    if len(insight_recent) == w:
        counts = {int((x.get("counts") or {}).get("insight_rows", -1)) for x in insight_recent}
        insight_rows_stable = len(counts) == 1 and next(iter(counts), -1) > 0

    policy_pass = health_policy.get("status") == "pass"
    insight_gate_pass = insight_gate.get("status") == "pass"
    delta_counts = insight_delta.get("counts") or {}
    delta_zero = (
        int(delta_counts.get("added_count", -1)) == 0
        and int(delta_counts.get("removed_count", -1)) == 0
        and int(delta_counts.get("changed_count", -1)) == 0
    )

    checks = {
        "gate_recent_pass": gate_all_pass,
        "insight_rows_stable": insight_rows_stable,
        "health_policy_pass": policy_pass,
        "insight_quality_gate_pass": insight_gate_pass,
        "delta_zero_change": delta_zero,
    }
    status = "pass" if all(checks.values()) else "fail"

    out = {
        "schema": "original_corpus_regime_singularity_canon_operational_consistency_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "window": w,
            "gate_history_jsonl": str(args.gate_history_jsonl),
            "insight_history_jsonl": str(args.insight_history_jsonl),
            "health_policy_json": str(args.health_policy_json),
            "insight_gate_json": str(args.insight_gate_json),
            "insight_delta_json": str(args.insight_delta_json),
        },
        "status": status,
        "checks": checks,
        "metrics": {
            "gate_recent_count": len(gate_recent),
            "insight_recent_count": len(insight_recent),
            "latest_gate_generated_at_utc": (gate_recent[-1] if gate_recent else {}).get("generated_at_utc"),
            "latest_insight_generated_at_utc": (insight_recent[-1] if insight_recent else {}).get("generated_at_utc"),
            "delta_counts": delta_counts,
        },
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

