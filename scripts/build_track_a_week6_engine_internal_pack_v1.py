# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-6 engine-internal compression-rule redesign pack.
# Keywords: track_a, week6, engine_internal, compression_rule, experiment_pack
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
W5_REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_week5_policy_replay_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week6_engine_internal_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week5-replay", type=Path, default=W5_REPLAY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.week5_replay if args.week5_replay.is_absolute() else ROOT / args.week5_replay)
    policy_floor = float((replay.get("replay_checks") or {}).get("policy_floor", 0.49))

    out_doc: dict[str, Any] = {
        "schema": "track_a_week6_engine_internal_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "week5_decision": replay.get("decision"),
            "policy_floor_locked": policy_floor,
            "quality_tradeoff_flag": (replay.get("replay_checks") or {}).get("quality_tradeoff_flag"),
        },
        "pack": {
            "name": "track_a_week6_engine_internal_rule_redesign",
            "objective": "Improve saving-quality frontier by changing internal compression rules instead of router blending.",
            "constraints": [
                "Policy floor remains fixed at 0.49",
                "Integrity floor remains fixed at 1.0",
                "Router default behavior unchanged during rule-level experiments",
            ],
            "experiments": [
                {
                    "id": "W6-E1",
                    "title": "Entropy-aware token drop budget",
                    "script_hint": "run_track_a_week6_entropy_budget_sweep_v1.py",
                    "config": {
                        "drop_budget_grid": [0.08, 0.1, 0.12, 0.14],
                        "risk_domain_budget_multiplier": {"ssot": 0.6, "timing": 0.65},
                    },
                    "success_gate": "saving >= 0.475 and jaccard >= 0.83 and integrity == 1.0",
                },
                {
                    "id": "W6-E2",
                    "title": "N-gram preservation rule injection",
                    "script_hint": "run_track_a_week6_ngram_preserve_sweep_v1.py",
                    "config": {
                        "ngram_n_grid": [2, 3],
                        "preserve_ratio_grid": [0.15, 0.2, 0.25],
                        "domain_focus": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.48 and jaccard >= 0.84 and integrity == 1.0",
                },
                {
                    "id": "W6-E3",
                    "title": "Clause boundary-aware compression rule",
                    "script_hint": "run_track_a_week6_clause_boundary_sweep_v1.py",
                    "config": {
                        "boundary_penalty_grid": [0.1, 0.15, 0.2],
                        "sentence_keep_min_tokens": [4, 5, 6],
                    },
                    "success_gate": "saving >= 0.485 and jaccard >= 0.845 and integrity == 1.0",
                },
                {
                    "id": "W6-E4",
                    "title": "Policy floor replay with engine-internal best candidate",
                    "script_hint": "report_track_a_week6_policy_replay_v1.py",
                    "config": {
                        "policy_floor": policy_floor,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W6-E1 and keep commercialization line at HOLD until W6-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
