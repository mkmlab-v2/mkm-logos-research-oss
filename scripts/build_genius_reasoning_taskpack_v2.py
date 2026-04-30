#!/usr/bin/env python3
"""Build an expanded genius reasoning taskpack (v2, 20 tasks)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "genius_reasoning_benchmark_tasks_v1.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    specs = [
        ("GR-01", "multi_step_planning", 0.80),
        ("GR-02", "counterfactual_reasoning", 0.75),
        ("GR-03", "constraint_repair", 0.70),
        ("GR-04", "risk_forecast_response", 0.72),
        ("GR-05", "novel_pattern_transfer", 0.85),
        ("GR-06", "long_horizon_dependency", 0.86),
        ("GR-07", "self_consistency_check", 0.78),
        ("GR-08", "adversarial_prompt_resistance", 0.90),
        ("GR-09", "objective_conflict_resolution", 0.84),
        ("GR-10", "resource_budget_optimization", 0.76),
        ("GR-11", "policy_exception_handling", 0.82),
        ("GR-12", "temporal_reasoning_reorder", 0.79),
        ("GR-13", "causal_chain_diagnosis", 0.83),
        ("GR-14", "uncertainty_aware_decision", 0.74),
        ("GR-15", "partial_information_recovery", 0.88),
        ("GR-16", "multi_objective_tradeoff", 0.81),
        ("GR-17", "counterexample_generation", 0.87),
        ("GR-18", "failure_mode_triage", 0.77),
        ("GR-19", "deceptive_pattern_detection", 0.91),
        ("GR-20", "compositional_transfer", 0.89),
    ]

    weight = round(1.0 / len(specs), 6)
    tasks = [
        {"task_id": tid, "type": ttype, "difficulty": diff, "weight": weight}
        for tid, ttype, diff in specs
    ]
    # normalize rounding drift
    drift = round(1.0 - sum(t["weight"] for t in tasks), 6)
    tasks[-1]["weight"] = round(tasks[-1]["weight"] + drift, 6)

    out = {
        "schema": "genius_reasoning_benchmark_tasks_v2",
        "generated_at_utc": _iso_now(),
        "task_count": len(tasks),
        "tasks": tasks,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "task_count": len(tasks)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
