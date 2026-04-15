# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-11 hypothesis experiment pack.
# Keywords: track_a, week11, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W10_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week10_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week11_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week10-replay", type=Path, default=W10_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week10_replay if args.week10_replay.is_absolute() else ROOT / args.week10_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week11_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week10_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week11_hypothesis_pack",
            "objective": "Recover saving floor without jaccard regression by introducing strict dual-threshold candidate governance.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W11-E1",
                    "title": "Dual-threshold router governance sweep",
                    "script_hint": "run_track_a_week11_dual_threshold_router_sweep_v1.py",
                    "config": {
                        "saving_trigger_grid": [0.486, 0.488, 0.49],
                        "jaccard_guard_grid": [0.846, 0.848, 0.85],
                        "protected_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W11-E2",
                    "title": "Selective off-path quota with quality backpressure",
                    "script_hint": "run_track_a_week11_offpath_quota_backpressure_sweep_v1.py",
                    "config": {
                        "offpath_quota_grid": [0.08, 0.1, 0.12],
                        "backpressure_alpha_grid": [0.25, 0.3, 0.35],
                        "candidate_pool_grid": [2, 3, 4],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W11-E3",
                    "title": "Rollback-aware dynamic cap plus confidence veto",
                    "script_hint": "run_track_a_week11_dynamic_cap_confidence_veto_sweep_v1.py",
                    "config": {
                        "dynamic_cap_grid": [0.5, 0.52, 0.54],
                        "confidence_veto_grid": [0.62, 0.66, 0.7],
                        "rollback_penalty_grid": [0.03, 0.05, 0.07],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W11-E4",
                    "title": "Policy floor replay with Week-11 best candidate",
                    "script_hint": "report_track_a_week11_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W11-E1 and keep commercialization line at HOLD until W11-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
