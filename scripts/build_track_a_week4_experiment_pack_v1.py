# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Week-4 Track A experiment pack after Week-3 replay hold.
# Keywords: track_a, week4, experiment_pack, phrase_policy, router_constraints
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPLAY = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_replay_v1.json"
RULES = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_priority_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_experiment_pack_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", type=Path, default=REPLAY)
    ap.add_argument("--rules", type=Path, default=RULES)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    replay = _load(args.replay if args.replay.is_absolute() else ROOT / args.replay)
    rules = _load(args.rules if args.rules.is_absolute() else ROOT / args.rules)
    candidates = [str((r or {}).get("token") or "").strip().lower() for r in rules.get("must_keep_candidates", [])]
    candidates = [c for c in candidates if c]

    ssot_seed = [t for t in candidates if t in {"constitution", "constraints", "operational", "stability", "quality"}]
    timing_seed = [t for t in candidates if t in {"timing", "bootstrap", "transition", "thresholds", "matrix"}]

    out_doc: dict[str, Any] = {
        "schema": "track_a_week4_experiment_pack_v1",
        "generated_at_utc": _now_utc(),
        "entry_condition": {
            "replay_decision": replay.get("decision"),
            "policy_floor_locked": (replay.get("policy_context") or {}).get("policy_floor"),
            "quality_tradeoff_flag": (replay.get("replay_checks") or {}).get("quality_tradeoff_flag"),
        },
        "pack": {
            "name": "track_a_week4_domain_phrase_router_pack",
            "objective": "Recover saving toward 0.49 while avoiding router-off quality collapse.",
            "constraints": [
                "Keep policy floor unchanged at 0.49",
                "Integrity floor fixed at 1.0",
                "Do not enable global router_off path as default candidate",
            ],
            "experiments": [
                {
                    "id": "W4-E1",
                    "title": "Domain-specific phrase policy (ssot only)",
                    "script_hint": "run_track_a_week4_domain_phrase_ab_v1.py",
                    "config": {
                        "target_domains": ["ssot"],
                        "phrase_seed_tokens": ssot_seed[:5],
                        "router_mode": "on",
                    },
                    "success_gate": "saving >= 0.475 and jaccard >= baseline-0.01 and integrity == 1.0",
                },
                {
                    "id": "W4-E2",
                    "title": "Domain-specific phrase policy (timing only)",
                    "script_hint": "run_track_a_week4_domain_phrase_ab_v1.py",
                    "config": {
                        "target_domains": ["timing"],
                        "phrase_seed_tokens": timing_seed[:5],
                        "router_mode": "on",
                    },
                    "success_gate": "saving >= 0.475 and timing-domain jaccard non-regression and integrity == 1.0",
                },
                {
                    "id": "W4-E3",
                    "title": "Selective router constraints (deny router_off on ssot/timing)",
                    "script_hint": "run_track_a_week4_selective_router_ab_v1.py",
                    "config": {
                        "router_default": "on",
                        "router_off_allowed_domains": ["general_only"],
                        "router_off_denied_domains": ["ssot", "timing"],
                    },
                    "success_gate": "saving >= 0.48 and jaccard >= 0.82 and integrity == 1.0",
                },
                {
                    "id": "W4-E4",
                    "title": "Policy floor replay with best constrained candidate",
                    "script_hint": "report_track_a_week4_policy_replay_v1.py",
                    "config": {
                        "policy_floor": 0.49,
                        "require_quality_tradeoff_flag": False,
                    },
                    "success_gate": "saving >= 0.49 and integrity == 1.0 and quality_tradeoff_flag == false",
                },
            ],
        },
        "next_action": "Start W4-E1 and keep commercialization line at HOLD until W4-E4 passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pack": out_doc["pack"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
