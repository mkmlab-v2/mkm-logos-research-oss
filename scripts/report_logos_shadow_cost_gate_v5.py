#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build v5 cost-aware gate from latest logos shadow tuning outputs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TUNING_V3 = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_tuning_v3_top3_latest.json"
DEFAULT_OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_cost_gate_v5_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute v5 precision-load-cost gate.")
    ap.add_argument("--tuning-v3", type=Path, default=DEFAULT_TUNING_V3)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--warning-review-minutes", type=float, default=6.0)
    ap.add_argument("--review-cost-per-minute", type=float, default=0.8)
    ap.add_argument("--false-alert-penalty-units", type=float, default=1.5)
    ap.add_argument("--min_cost_efficiency_score", type=float, default=0.35)
    args = ap.parse_args()

    doc = _read_json(args.tuning_v3)
    winner = doc.get("winner") if isinstance(doc.get("winner"), dict) else {}
    if not winner:
        raise SystemExit(f"missing winner in {args.tuning_v3}")

    avg_precision = float(winner.get("avg_precision", 0.0))
    avg_load = float(winner.get("avg_load_ratio", 0.0))
    avg_false = float(winner.get("avg_false_alert_density", 0.0))

    review_cost_units = float(args.warning_review_minutes) * float(args.review_cost_per_minute)
    denominator = (1.0 + avg_load * review_cost_units + avg_false * float(args.false_alert_penalty_units))
    cost_eff = (avg_precision / denominator) if denominator > 0 else 0.0
    pass_gate = cost_eff >= float(args.min_cost_efficiency_score)

    payload: dict[str, Any] = {
        "schema": "logos_kospi_shadow_cost_gate_v5",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "tuning_v3_path": str(args.tuning_v3.resolve()),
            "winner_config": winner.get("config"),
            "avg_precision": avg_precision,
            "avg_load_ratio": avg_load,
            "avg_false_alert_density": avg_false,
        },
        "cost_model": {
            "warning_review_minutes": float(args.warning_review_minutes),
            "review_cost_per_minute": float(args.review_cost_per_minute),
            "false_alert_penalty_units": float(args.false_alert_penalty_units),
            "review_cost_units": review_cost_units,
        },
        "gate": {
            "cost_efficiency_score": round(cost_eff, 6),
            "min_cost_efficiency_score": float(args.min_cost_efficiency_score),
            "pass": pass_gate,
            "decision": "OBSERVATION_ONLY_COST_OK" if pass_gate else "OBSERVATION_ONLY_COST_BLOCKED",
        },
        "note": "Cost gate is research-only and must not be used as direct production trigger. avg_precision historically came from tuning JSON; after v21, prefer precrash_zone_precision from run_logos_kospi_shadow_test metrics for new evaluations (see report_logos_shadow_cost_gate_temporal_v22.py).",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "pass": pass_gate, "score": payload["gate"]["cost_efficiency_score"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

