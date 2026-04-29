#!/usr/bin/env python3
"""Lock final manual promotion decision for myeongni rail."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_GATE = ART / "myeongni_promotion_gate_latest.json"
DEFAULT_REVIEW_PACKET = ART / "myeongni_promotion_review_packet_latest.json"
DEFAULT_R1 = REPORTS / "myeongni_a_track_promotion_decision_latest.json"
DEFAULT_R2 = REPORTS / "myeongni_a_track_promotion_decision_s3_latest.json"
DEFAULT_R3 = REPORTS / "myeongni_a_track_promotion_decision_s4_latest.json"
DEFAULT_OUT = ART / "myeongni_manual_promotion_decision_lock_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ok_receipt(doc: dict[str, Any], stage: str) -> bool:
    return (
        str(doc.get("schema") or "") == "a_track_promotion_decision_v1"
        and str(doc.get("requested_stage") or "") == stage
        and str(doc.get("status") or "") == "accepted"
        and str(doc.get("action") or "") == "approve"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--review-packet", type=Path, default=DEFAULT_REVIEW_PACKET)
    ap.add_argument("--receipt-s2", type=Path, default=DEFAULT_R1)
    ap.add_argument("--receipt-s3", type=Path, default=DEFAULT_R2)
    ap.add_argument("--receipt-s4", type=Path, default=DEFAULT_R3)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", default="PRO")
    args = ap.parse_args()

    gate = _read_json(args.gate)
    review_packet = _read_json(args.review_packet)
    r2 = _read_json(args.receipt_s2)
    r3 = _read_json(args.receipt_s3)
    r4 = _read_json(args.receipt_s4)

    gate_pass = str(gate.get("status") or "") == "PASS"
    manual_go = bool(gate.get("go_for_manual_signoff"))
    track_wall_ok = not bool((gate.get("policy") or {}).get("track_b_to_a_auto_bridge"))
    live_auto_ok = not bool((gate.get("policy") or {}).get("live_trigger_auto_enabled"))
    s2_ok = _ok_receipt(r2, "S2_PAPER_STRICT")
    s3_ok = _ok_receipt(r3, "S3_PAPER_SCALED")
    s4_ok = _ok_receipt(r4, "S4_LIMITED_LIVE")

    checklist = {
        "gate_status_pass": gate_pass,
        "manual_signoff_go": manual_go,
        "receipt_s2_accepted": s2_ok,
        "receipt_s3_accepted": s3_ok,
        "receipt_s4_accepted": s4_ok,
        "track_bridge_auto_disabled": track_wall_ok,
        "live_trigger_auto_disabled": live_auto_ok,
    }
    approved = all(checklist.values())

    payload = {
        "schema": "myeongni_manual_promotion_decision_lock_v1",
        "locked_at_utc": _now(),
        "inputs": {
            "promotion_gate": str(args.gate.resolve()),
            "review_packet": str(args.review_packet.resolve()),
            "receipt_s2": str(args.receipt_s2.resolve()),
            "receipt_s3": str(args.receipt_s3.resolve()),
            "receipt_s4": str(args.receipt_s4.resolve()),
        },
        "review_snapshot": {
            "promotion_gate_status": gate.get("status"),
            "promotion_decision": gate.get("decision"),
            "review_packet_schema": review_packet.get("schema"),
            "checklist": checklist,
        },
        "final_decision": "approved" if approved else "rejected",
        "reviewer": args.reviewer,
        "decision_note": (
            "Manual promotion lock approved with S2/S3/S4 accepted receipts; "
            "auto-bridge and auto-live remain disabled."
            if approved
            else "One or more checklist items failed; keep observation-only promotion hold."
        ),
        "constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"final_decision={payload['final_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
