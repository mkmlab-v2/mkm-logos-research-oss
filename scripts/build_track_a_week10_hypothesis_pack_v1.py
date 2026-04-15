# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-10 hypothesis experiment pack.
# Keywords: track_a, week10, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W9_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week9_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week10_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week9-replay", type=Path, default=W9_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week9_replay if args.week9_replay.is_absolute() else ROOT / args.week9_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week10_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week9_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week10_hypothesis_pack",
            "objective": "Break the quality_tradeoff_flag deadlock with constrained hybrid routing while preserving policy-floor viability.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W10-E1",
                    "title": "Domain-tiered hybrid routing with strict jaccard guard",
                    "script_hint": "run_track_a_week10_domain_tiered_hybrid_sweep_v1.py",
                    "config": {
                        "tier_guard_domains": ["ssot", "timing"],
                        "off_ratio_grid": [0.12, 0.16, 0.2],
                        "jaccard_guard_margin_grid": [0.004, 0.006, 0.008],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W10-E2",
                    "title": "Saving-floor constrained candidate replay blend",
                    "script_hint": "run_track_a_week10_saving_floor_candidate_blend_sweep_v1.py",
                    "config": {
                        "blend_weight_grid": [0.2, 0.3, 0.4],
                        "saving_floor_buffer_grid": [0.0, 0.005, 0.01],
                        "candidate_pool_grid": [2, 3, 4],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W10-E3",
                    "title": "Confidence-band fallback with dynamic cap rollback",
                    "script_hint": "run_track_a_week10_dynamic_cap_fallback_sweep_v1.py",
                    "config": {
                        "confidence_band_grid": [0.6, 0.64, 0.68],
                        "dynamic_cap_grid": [0.5, 0.52, 0.54],
                        "rollback_penalty_grid": [0.03, 0.05, 0.07],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W10-E4",
                    "title": "Policy floor replay with Week-10 best candidate",
                    "script_hint": "report_track_a_week10_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W10-E1 and keep commercialization line at HOLD until W10-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
