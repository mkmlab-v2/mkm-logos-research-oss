#!/usr/bin/env python3
"""Build S1 manual signoff worksheet for commander review."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "lens_penalty_s1_shadow_gate_latest.json"
DEFAULT_STREAK = ART / "lens_penalty_s1_shadow_streak_gate_latest.json"
DEFAULT_PACKET = ART / "lens_penalty_s1_promotion_review_packet_latest.json"
DEFAULT_CHECKLIST = ART / "lens_penalty_apply_mode_checklist_latest.json"
DEFAULT_OUT = ART / "lens_penalty_s1_manual_signoff_worksheet_latest.json"


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
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--streak-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--packet-json", type=Path, default=DEFAULT_PACKET)
    ap.add_argument("--apply-checklist-json", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _read_json(args.gate_json)
    streak = _read_json(args.streak_json)
    packet = _read_json(args.packet_json)
    apply_ck = _read_json(args.apply_checklist_json)

    gate_go = str(gate.get("decision") or "") == "GO_REVIEW"
    streak_ready = str(streak.get("decision") or "") == "READY_FOR_COMMANDER_REVIEW"
    decision_hint_ready = str(packet.get("decision_hint") or "") == "READY_FOR_COMMANDER_REVIEW"
    human_review_required = bool((gate.get("constraints") or {}).get("human_review_required", True))
    auto_apply_disabled = bool((gate.get("constraints") or {}).get("auto_apply_enabled", False) is False)

    checklist = {
        "s1_gate_go_review": gate_go,
        "streak_ready_for_review": streak_ready,
        "review_packet_ready": decision_hint_ready,
        "human_review_required": human_review_required,
        "auto_apply_disabled": auto_apply_disabled,
    }
    failed = [k for k, v in checklist.items() if not v]
    all_green = len(failed) == 0
    decision = "READY_FOR_COMMANDER_SIGNOFF" if all_green else "HOLD_NEEDS_REVIEW"

    out = {
        "schema": "lens_penalty_s1_manual_signoff_worksheet_v1",
        "generated_at_utc": _now(),
        "decision": decision,
        "all_green": all_green,
        "checklist": checklist,
        "failed_checks": failed,
        "summary": {
            "s1_gate_decision": gate.get("decision"),
            "streak_decision": streak.get("decision"),
            "review_packet_decision_hint": packet.get("decision_hint"),
            "streak_go_days": (streak.get("snapshot") or {}).get("current_go_streak"),
            "weekly_strict_gap": (packet.get("summary") or {}).get("weekly_strict_gap"),
            "simulated_strict_gap": (packet.get("summary") or {}).get("simulated_strict_gap"),
            "flip_candidates": (packet.get("summary") or {}).get("flip_candidates"),
            "apply_check_decision": apply_ck.get("decision"),
        },
        "constraints": {
            "human_review_required": True,
            "auto_apply_enabled": False,
        },
        "evidence_paths": {
            "gate_json": str(args.gate_json.resolve()).replace("\\", "/"),
            "streak_json": str(args.streak_json.resolve()).replace("\\", "/"),
            "packet_json": str(args.packet_json.resolve()).replace("\\", "/"),
            "apply_checklist_json": str(args.apply_checklist_json.resolve()).replace("\\", "/"),
        },
        "operator_action": {
            "approve_if_all_green": all_green,
            "review_items_if_hold": failed,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
