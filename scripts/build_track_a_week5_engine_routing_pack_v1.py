# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-5 engine-level routing redesign experiment pack.
# Keywords: track_a, week5, routing, penalty, experiment_pack
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W4_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week5_engine_routing_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week4-replay", type=Path, default=W4_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week4_replay if args.week4_replay.is_absolute() else ROOT / args.week4_replay)
    policy_floor = float((replay.get("replay_checks") or {}).get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week5_engine_routing_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week4_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": (replay.get("replay_checks") or {}).get("quality_tradeoff_flag"),
        },
        "pack": {
            "name": "track_a_week5_engine_routing_redesign",
            "objective": "Recover policy-floor-compatible saving without catastrophic jaccard drop via router scoring redesign.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "No global router_off default allowed",
            ],
            "experiments": [
                {
                    "id": "W5-E1",
                    "title": "Penalty-based router scoring (domain risk penalty)",
                    "script_hint": "run_track_a_week5_penalty_router_sweep_v1.py",
                    "config": {
                        "risk_domains": ["ssot", "timing"],
                        "penalty_grid": [0.05, 0.1, 0.15, 0.2],
                        "router_default": "on",
                    },
                    "success_gate": "saving >= 0.475 and jaccard >= 0.82 and integrity == 1.0",
                },
                {
                    "id": "W5-E2",
                    "title": "Adaptive threshold router by domain confidence",
                    "script_hint": "run_track_a_week5_confidence_router_sweep_v1.py",
                    "config": {
                        "confidence_threshold_grid": [0.55, 0.6, 0.65, 0.7],
                        "domain_overrides": {"ssot": 0.7, "timing": 0.68},
                    },
                    "success_gate": "saving >= 0.48 and jaccard >= 0.83 and integrity == 1.0",
                },
                {
                    "id": "W5-E3",
                    "title": "Hybrid fallback route (router_on hard domains, penalty mix others)",
                    "script_hint": "run_track_a_week5_hybrid_router_mix_v1.py",
                    "config": {
                        "hard_router_on_domains": ["ssot", "timing"],
                        "soft_penalty_domains": ["general"],
                        "penalty_alpha_grid": [0.2, 0.3, 0.4],
                    },
                    "success_gate": "saving >= 0.485 and jaccard >= 0.84 and integrity == 1.0",
                },
                {
                    "id": "W5-E4",
                    "title": "Policy floor replay with redesigned routing candidate",
                    "script_hint": "report_track_a_week5_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W5-E1 and keep commercialization line at HOLD until W5-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
