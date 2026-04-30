#!/usr/bin/env python3
"""Lock final manual promotion decision for emotion-state control."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "emotion_state_promotion_gate_latest.json"
DEFAULT_MAPPING = ART / "emotion_state_mapping_latest.json"
DEFAULT_OUT = ART / "emotion_state_manual_promotion_decision_lock_latest.json"
DEFAULT_CANDIDATE = ART / "emotion_state_track_a_candidate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision-note", default="manual approval in chat")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--candidate-out", type=Path, default=DEFAULT_CANDIDATE)
    args = ap.parse_args()

    gate = _read_json(args.promotion_gate)
    mapping = _read_json(args.mapping_json)

    gate_candidate = str(gate.get("decision") or "") == "PROMOTION_CANDIDATE"
    mapping_loaded = bool(mapping.get("states"))
    approved = bool(args.approve and gate_candidate and mapping_loaded)

    checklist = {
        "gate_is_promotion_candidate": gate_candidate,
        "mapping_loaded": mapping_loaded,
        "manual_approve_flag": bool(args.approve),
    }

    lock = {
        "schema": "emotion_state_manual_promotion_decision_lock_v1",
        "locked_at_utc": _now(),
        "inputs": {
            "promotion_gate": str(args.promotion_gate.resolve()),
            "mapping_json": str(args.mapping_json.resolve()),
        },
        "review_snapshot": {
            "promotion_gate_decision": gate.get("decision"),
            "promotion_gate_checks": gate.get("checks"),
            "checklist": checklist,
        },
        "final_decision": "approved" if approved else "rejected",
        "reviewer": args.reviewer,
        "decision_note": args.decision_note,
        "constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
            "a_track_candidate_only": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if approved:
        candidate = {
            "schema": "emotion_state_track_a_candidate_v1",
            "generated_at_utc": _now(),
            "status": "APPROVED_CANDIDATE",
            "source_track": "B",
            "promotion_mode": "human_approved_candidate_only",
            "candidate_gate": {
                "decision": gate.get("decision"),
                "thresholds": gate.get("thresholds"),
            },
            "runtime_constraints": {
                "track_b_to_a_auto_bridge": False,
                "live_trigger_auto_enabled": False,
                "requires_human_review_each_release": True,
            },
            "evidence": {
                "manual_lock": str(args.out.resolve()),
                "promotion_gate": str(args.promotion_gate.resolve()),
                "mapping_json": str(args.mapping_json.resolve()),
            },
        }
        args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
        args.candidate_out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.candidate_out}")

    print(f"WROTE: {args.out}")
    print(f"final_decision={lock['final_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
