#!/usr/bin/env python3
"""Lock manual promotion decision for prophecy Track A candidate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SIGNOFF = ART / "btrack_promotion_signoff_packet_separated_v1_latest.json"
DEFAULT_GATE = ART / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
DEFAULT_LIVE_AB = ART / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_PRE_REVIEW = ART / "prophecy_track_a_candidate_pre_review_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_manual_promotion_decision_lock_v1_latest.json"
DEFAULT_TRACKA = ART / "prophecy_track_a_candidate_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--live-ab-summary", type=Path, default=DEFAULT_LIVE_AB)
    ap.add_argument("--pre-review-candidate", type=Path, default=DEFAULT_PRE_REVIEW)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision-note", default="user approved promotion in-chat")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tracka-candidate-out", type=Path, default=DEFAULT_TRACKA)
    args = ap.parse_args()

    signoff = _read_json(args.signoff_json)
    gate = _read_json(args.promotion_gate)
    live_ab = _read_json(args.live_ab_summary)
    pre_review = _read_json(args.pre_review_candidate)

    prophecy_status = ((signoff.get("track_status") or {}).get("prophecy") or {})
    blockers = prophecy_status.get("blockers") if isinstance(prophecy_status.get("blockers"), list) else []
    checklist = {
        "signoff_ready_for_human_signoff": str(prophecy_status.get("decision") or "") == "READY_FOR_HUMAN_SIGNOFF",
        "signoff_has_no_blockers": len(blockers) == 0,
        "promotion_gate_auto_promote_ready": bool(gate.get("auto_promote_ready") is True),
        "promotion_gate_shared_gate_pass": bool(gate.get("shared_all_gates_passed") is True),
        "live_ab_ready": str(live_ab.get("status") or "") == "READY",
        "pre_review_candidate_present": str(pre_review.get("status") or "") == "PRE_REVIEW_CANDIDATE",
    }
    approved = all(checklist.values())

    lock_doc = {
        "schema": "prophecy_manual_promotion_decision_lock_v1",
        "locked_at_utc": _now(),
        "inputs": {
            "signoff_json": str(args.signoff_json.resolve()),
            "promotion_gate": str(args.promotion_gate.resolve()),
            "live_ab_summary": str(args.live_ab_summary.resolve()),
            "pre_review_candidate": str(args.pre_review_candidate.resolve()),
        },
        "review_snapshot": {
            "signoff_decision": prophecy_status.get("decision"),
            "auto_promote_ready": gate.get("auto_promote_ready"),
            "strict_pass_streak": gate.get("strict_pass_streak"),
            "live_ab_status": live_ab.get("status"),
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
    args.out.write_text(json.dumps(lock_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if approved:
        candidate = {
            "schema": "prophecy_track_a_candidate_v1",
            "generated_at_utc": _now(),
            "status": "APPROVED_CANDIDATE",
            "source_track": "B",
            "promotion_mode": "human_approved_candidate_only",
            "candidate_gate": {
                "promotion_track_mode": ((gate.get("inputs") or {}).get("promotion_track_mode")),
                "strict_pass_streak": gate.get("strict_pass_streak"),
            },
            "candidate_metrics": {
                "mean_test_accuracy": (((gate.get("tracks") or {}).get("per_date_lens") or {}).get("gates") or []),
                "live_ab_status": live_ab.get("status"),
            },
            "runtime_constraints": {
                "track_b_to_a_auto_bridge": False,
                "live_trigger_auto_enabled": False,
                "requires_human_review_each_release": True,
            },
            "evidence": {
                "manual_lock": str(args.out.resolve()),
                "signoff_json": str(args.signoff_json.resolve()),
                "promotion_gate": str(args.promotion_gate.resolve()),
                "live_ab_summary": str(args.live_ab_summary.resolve()),
            },
        }
        args.tracka_candidate_out.parent.mkdir(parents=True, exist_ok=True)
        args.tracka_candidate_out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.tracka_candidate_out}")

    print(f"WROTE: {args.out}")
    print(f"final_decision={lock_doc['final_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
