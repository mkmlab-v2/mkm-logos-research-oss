# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-15 hypothesis experiment pack.
# Keywords: track_a, week15, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W14_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week14_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week14-replay", type=Path, default=W14_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week14_replay if args.week14_replay.is_absolute() else ROOT / args.week14_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week15_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week14_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week15_hypothesis_pack",
            "objective": "Break quality-tradeoff deadlock via selective floor unlock and confidence replay crossover under fixed policy floor.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W15-E1",
                    "title": "Selective floor-unlock lane sweep with strict jaccard guard",
                    "script_hint": "run_track_a_week15_selective_floor_unlock_sweep_v1.py",
                    "config": {
                        "floor_unlock_ratio_grid": [0.08, 0.1, 0.12],
                        "jaccard_guard_grid": [0.846, 0.848, 0.85],
                        "protected_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W15-E2",
                    "title": "Confidence replay crossover with floor shadow",
                    "script_hint": "run_track_a_week15_confidence_replay_crossover_sweep_v1.py",
                    "config": {
                        "crossover_weight_grid": [0.6, 0.65, 0.7],
                        "floor_shadow_margin_grid": [0.0, 0.002, 0.004],
                        "candidate_pool_grid": [3, 4, 5],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W15-E3",
                    "title": "Adaptive throttle rollback with confidence veto",
                    "script_hint": "run_track_a_week15_adaptive_throttle_veto_sweep_v1.py",
                    "config": {
                        "confidence_gate_grid": [0.56, 0.6, 0.64],
                        "throttle_quota_grid": [0.08, 0.1, 0.12],
                        "rollback_penalty_grid": [0.02, 0.035, 0.05],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W15-E4",
                    "title": "Policy floor replay with Week-15 best candidate",
                    "script_hint": "report_track_a_week15_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W15-E1 and keep commercialization line at HOLD until W15-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
