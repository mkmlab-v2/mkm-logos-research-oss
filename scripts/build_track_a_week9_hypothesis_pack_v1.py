# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-9 hypothesis experiment pack.
# Keywords: track_a, week9, hypothesis, experiment_pack, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W8_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week8_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week9_hypothesis_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week8-replay", type=Path, default=W8_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week8_replay if args.week8_replay.is_absolute() else ROOT / args.week8_replay)
    checks = replay.get("replay_checks") or {}
    policy_floor = float(checks.get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week9_hypothesis_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week8_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": checks.get("quality_tradeoff_flag"),
            "best_saving_seen": checks.get("best_saving_seen"),
            "best_jaccard_seen": checks.get("best_jaccard_seen"),
        },
        "pack": {
            "name": "track_a_week9_hypothesis_pack",
            "objective": "Target the quality tradeoff flag directly while preserving policy-floor-level saving potential.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Quality tradeoff flag must become false for promotion",
                "All experiments stay in isolated research lane",
            ],
            "experiments": [
                {
                    "id": "W9-E1",
                    "title": "Domain-frozen router mix with bounded off-ratio",
                    "script_hint": "run_track_a_week9_domain_frozen_router_mix_sweep_v1.py",
                    "config": {
                        "off_ratio_grid": [0.18, 0.22, 0.26],
                        "frozen_domains": ["ssot", "timing"],
                        "max_nonrisk_off_ratio": 0.3,
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W9-E2",
                    "title": "Jaccard-prior rerank with savings hard cap",
                    "script_hint": "run_track_a_week9_jaccard_prior_rerank_sweep_v1.py",
                    "config": {
                        "jaccard_prior_grid": [0.65, 0.7, 0.75],
                        "saving_cap_grid": [0.5, 0.52, 0.54],
                        "candidate_pool_grid": [2, 3],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W9-E3",
                    "title": "Selective recovery fallback by confidence bands",
                    "script_hint": "run_track_a_week9_confidence_band_fallback_sweep_v1.py",
                    "config": {
                        "confidence_band_grid": [0.58, 0.62, 0.66],
                        "fallback_penalty_grid": [0.04, 0.06, 0.08],
                        "critical_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.49 and jaccard >= 0.85 and integrity == 1.0",
                },
                {
                    "id": "W9-E4",
                    "title": "Policy floor replay with Week-9 best candidate",
                    "script_hint": "report_track_a_week9_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W9-E1 and keep commercialization line at HOLD until W9-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
