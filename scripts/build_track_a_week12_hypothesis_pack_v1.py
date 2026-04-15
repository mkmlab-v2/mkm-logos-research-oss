# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-12 hypothesis experiment pack.
# Keywords: track_a, week12, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W11_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week11_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week12_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week11-replay", type=Path, default=W11_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week11_replay if args.week11_replay.is_absolute() else ROOT / args.week11_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week12_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week11_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week12_hypothesis_pack",
            "objective": "Break quality_tradeoff deadlock via lane-weighted replay while preserving jaccard guard and fixed policy floor.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W12-E1",
                    "title": "Lane-weighted router allocation sweep",
                    "script_hint": "run_track_a_week12_lane_weighted_router_sweep_v1.py",
                    "config": {
                        "lane_weight_grid": [0.52, 0.56, 0.6],
                        "jaccard_guard_grid": [0.846, 0.848, 0.85],
                        "protected_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W12-E2",
                    "title": "Candidate replay with quality-first tie-break",
                    "script_hint": "run_track_a_week12_quality_tiebreak_replay_sweep_v1.py",
                    "config": {
                        "candidate_pool_grid": [3, 4, 5],
                        "quality_tiebreak_margin_grid": [0.001, 0.002, 0.003],
                        "saving_floor_buffer_grid": [0.0, 0.003, 0.006],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W12-E3",
                    "title": "Confidence-gated rollback with adaptive quota",
                    "script_hint": "run_track_a_week12_confidence_quota_rollback_sweep_v1.py",
                    "config": {
                        "confidence_gate_grid": [0.6, 0.64, 0.68],
                        "adaptive_quota_grid": [0.08, 0.1, 0.12],
                        "rollback_penalty_grid": [0.03, 0.05, 0.07],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W12-E4",
                    "title": "Policy floor replay with Week-12 best candidate",
                    "script_hint": "report_track_a_week12_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W12-E1 and keep commercialization line at HOLD until W12-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
