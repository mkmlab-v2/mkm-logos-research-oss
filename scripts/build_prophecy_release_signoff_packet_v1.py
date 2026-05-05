#!/usr/bin/env python3
"""Build final release sign-off packet for prophecy approved candidate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "prophecy_track_a_candidate_v1_latest.json"
DEFAULT_LOCK = ART / "prophecy_manual_promotion_decision_lock_v1_latest.json"
DEFAULT_CHECKLIST = ART / "prophecy_approved_candidate_release_checklist_v1_latest.json"
DEFAULT_SIGNOFF = ART / "prophecy_release_human_signoff_v1_latest.json"
DEFAULT_GATE = ART / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
DEFAULT_LIVE_AB = ART / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_release_signoff_packet_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--manual-lock", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--human-signoff", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--live-ab-summary", type=Path, default=DEFAULT_LIVE_AB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    candidate = _load(args.candidate)
    lock = _load(args.manual_lock)
    checklist = _load(args.checklist)
    signoff = _load(args.human_signoff)
    gate = _load(args.promotion_gate)
    live_ab = _load(args.live_ab_summary)

    release_ready = bool((checklist.get("summary") or {}).get("ready_for_release_signoff"))
    signoff_ok = str(signoff.get("decision") or "").upper() == "APPROVED"
    candidate_ok = str(candidate.get("status") or "") == "APPROVED_CANDIDATE"
    lock_ok = str(lock.get("final_decision") or "") == "approved"

    packet = {
        "schema": "prophecy_release_signoff_packet_v1",
        "generated_at_utc": _now(),
        "track": "prophecy",
        "research_only": True,
        "status": "READY_FOR_RELEASE_SIGNOFF" if (release_ready and signoff_ok and candidate_ok and lock_ok) else "HOLD",
        "inputs": {
            "candidate": str(args.candidate).replace("\\", "/"),
            "manual_lock": str(args.manual_lock).replace("\\", "/"),
            "checklist": str(args.checklist).replace("\\", "/"),
            "human_signoff": str(args.human_signoff).replace("\\", "/"),
            "promotion_gate": str(args.promotion_gate).replace("\\", "/"),
            "live_ab_summary": str(args.live_ab_summary).replace("\\", "/"),
        },
        "checks": {
            "candidate_approved": candidate_ok,
            "manual_lock_approved": lock_ok,
            "checklist_ready_for_release_signoff": release_ready,
            "human_signoff_approved": signoff_ok,
            "promotion_gate_auto_promote_ready": bool(gate.get("auto_promote_ready") is True),
            "live_ab_ready": str(live_ab.get("status") or "") == "READY",
        },
        "constraints": {
            "auto_release_enabled": False,
            "human_review_required_each_release": True,
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
        },
        "next_actions_ko": []
        if (release_ready and signoff_ok and candidate_ok and lock_ok)
        else ["누락된 체크를 보완한 뒤 human sign-off를 재기록"],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={packet['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
