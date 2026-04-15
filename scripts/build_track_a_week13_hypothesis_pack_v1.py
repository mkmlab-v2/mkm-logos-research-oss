# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-13 hypothesis experiment pack.
# Keywords: track_a, week13, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W12_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week12_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week13_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week12-replay", type=Path, default=W12_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week12_replay if args.week12_replay.is_absolute() else ROOT / args.week12_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week13_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week12_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week13_hypothesis_pack",
            "objective": "Break quality-tradeoff deadlock by applying domain-priority recovery and bounded off-path unlock under fixed policy floor.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W13-E1",
                    "title": "Domain-priority selective unlock sweep",
                    "script_hint": "run_track_a_week13_domain_priority_unlock_sweep_v1.py",
                    "config": {
                        "priority_domain_weights": {
                            "ssot": 0.2,
                            "timing": 0.15,
                            "default": 0.65
                        },
                        "unlock_ratio_grid": [0.08, 0.1, 0.12],
                        "jaccard_guard_grid": [0.846, 0.848, 0.85],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W13-E2",
                    "title": "Recovery-first replay blend with floor shadow",
                    "script_hint": "run_track_a_week13_recovery_blend_floor_shadow_sweep_v1.py",
                    "config": {
                        "recovery_weight_grid": [0.6, 0.65, 0.7],
                        "floor_shadow_margin_grid": [0.0, 0.002, 0.004],
                        "candidate_pool_grid": [3, 4, 5],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W13-E3",
                    "title": "Confidence rollback with penalty annealing",
                    "script_hint": "run_track_a_week13_confidence_penalty_anneal_sweep_v1.py",
                    "config": {
                        "confidence_gate_grid": [0.58, 0.62, 0.66],
                        "quota_grid": [0.08, 0.1, 0.12],
                        "anneal_penalty_grid": [0.025, 0.04, 0.055],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W13-E4",
                    "title": "Policy floor replay with Week-13 best candidate",
                    "script_hint": "report_track_a_week13_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W13-E1 and keep commercialization line at HOLD until W13-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
