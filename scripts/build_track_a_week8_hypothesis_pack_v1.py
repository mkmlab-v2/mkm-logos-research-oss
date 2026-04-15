# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-8 hypothesis experiment pack.
# Keywords: track_a, week8, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W7_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week7_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week8_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week7-replay", type=Path, default=W7_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week7_replay if args.week7_replay.is_absolute() else ROOT / args.week7_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week8_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week7_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week8_hypothesis_pack",
            "objective": "Test low-impact structural hypotheses to recover saving without reopening large jaccard regressions.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W8-E1",
                    "title": "Domain-locked phrase budget micro-tuning",
                    "script_hint": "run_track_a_week8_phrase_budget_micro_sweep_v1.py",
                    "config": {
                        "phrase_budget_grid": [0.04, 0.06, 0.08],
                        "target_domains": ["ssot", "timing"],
                        "router_policy": "router_on_only",
                    },
                    "success_gate": "saving >= 0.48 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W8-E2",
                    "title": "Domain confidence restore gate",
                    "script_hint": "run_track_a_week8_confidence_restore_gate_sweep_v1.py",
                    "config": {
                        "restore_threshold_grid": [0.6, 0.65, 0.7],
                        "restore_penalty_grid": [0.05, 0.08, 0.1],
                        "risk_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.485 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W8-E3",
                    "title": "Low-cost rerank tie-breaker for jaccard floor",
                    "script_hint": "run_track_a_week8_low_cost_rerank_sweep_v1.py",
                    "config": {
                        "rerank_alpha_grid": [0.15, 0.2, 0.25],
                        "candidate_pool_grid": [2, 3, 4],
                        "latency_budget_ms_per_case": 2.0,
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W8-E4",
                    "title": "Policy floor replay with Week-8 best candidate",
                    "script_hint": "report_track_a_week8_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W8-E1 and keep commercialization line at HOLD until W8-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
