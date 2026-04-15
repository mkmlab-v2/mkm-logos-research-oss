# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-7 architecture-level redesign experiment pack.
# Keywords: track_a, week7, architecture, redesign, experiment_pack
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W6_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week6_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week7_architecture_redesign_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week6-replay", type=Path, default=W6_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week6_replay if args.week6_replay.is_absolute() else ROOT / args.week6_replay)
    policy_floor = float((replay.get("replay_checks") or {}).get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week7_architecture_redesign_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week6_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": (replay.get("replay_checks") or {}).get("quality_tradeoff_flag"),
        },
        "pack": {
            "name": "track_a_week7_architecture_redesign",
            "objective": "Move from rule tuning to modular architecture redesign for better saving-quality frontier.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "All redesign experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W7-E1",
                    "title": "Two-stage compressor architecture (planner + executor)",
                    "script_hint": "run_track_a_week7_two_stage_arch_sweep_v1.py",
                    "config": {
                        "planner_budget_grid": [0.1, 0.12, 0.14],
                        "executor_budget_grid": [0.32, 0.34, 0.36],
                        "risk_domain_lock": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.475 and jaccard >= 0.84 and integrity == 1.0",
                },
                {
                    "id": "W7-E2",
                    "title": "Semantic chunker + sentence policy module",
                    "script_hint": "run_track_a_week7_semantic_chunk_sweep_v1.py",
                    "config": {
                        "chunk_size_grid": [48, 64, 80],
                        "sentence_policy_strength": [0.2, 0.25, 0.3],
                        "domain_priority": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.48 and jaccard >= 0.845 and integrity == 1.0",
                },
                {
                    "id": "W7-E3",
                    "title": "Dual-objective scorer (saving-jaccard pareto optimizer)",
                    "script_hint": "run_track_a_week7_pareto_scorer_sweep_v1.py",
                    "config": {
                        "saving_weight_grid": [0.45, 0.5, 0.55],
                        "jaccard_weight_grid": [0.55, 0.5, 0.45],
                        "integrity_hard_gate": 1.0,
                    },
                    "success_gate": "saving >= 0.485 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W7-E4",
                    "title": "Policy floor replay with architecture-level best candidate",
                    "script_hint": "report_track_a_week7_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W7-E1 and keep commercialization line at HOLD until W7-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
