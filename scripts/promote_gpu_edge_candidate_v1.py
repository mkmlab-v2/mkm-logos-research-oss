#!/usr/bin/env python3
"""Promote GPU->Edge optimization to approved Track A candidate (manual lock)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "gpu_edge_promotion_gate_v1_latest.json"
DEFAULT_LOCK = ART / "gpu_edge_manual_promotion_decision_lock_latest.json"
DEFAULT_CANDIDATE = ART / "gpu_edge_track_a_candidate_latest.json"
DEFAULT_PROMOTED = ART / "gpu_edge_track_a_promoted_latest.json"


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
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision-note", default="manual promotion approval for LG HS pack")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--lock-out", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--candidate-out", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--promoted-out", type=Path, default=DEFAULT_PROMOTED)
    args = ap.parse_args()

    gate = _read_json(args.gate_json)
    gate_ok = str(gate.get("decision") or "") == "GO_CANDIDATE_GPU_EDGE_V1" and bool(gate.get("promotion_ready"))
    approved = bool(args.approve and gate_ok)

    lock_doc = {
        "schema": "gpu_edge_manual_promotion_decision_lock_v1",
        "locked_at_utc": _now(),
        "inputs": {"gate_json": str(args.gate_json.resolve())},
        "review_snapshot": {
            "gate_decision": gate.get("decision"),
            "gate_checks": gate.get("checks"),
            "gate_metrics": gate.get("metrics"),
            "manual_approve_flag": bool(args.approve),
        },
        "final_decision": "approved" if approved else "rejected",
        "reviewer": args.reviewer,
        "decision_note": args.decision_note,
        "constraints": {
            "research_only": True,
            "target_board_measurement_required_for_final_promotion": True,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
        },
    }
    args.lock_out.parent.mkdir(parents=True, exist_ok=True)
    args.lock_out.write_text(json.dumps(lock_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if approved:
        candidate_doc = {
            "schema": "gpu_edge_track_a_candidate_v1",
            "generated_at_utc": _now(),
            "status": "APPROVED_CANDIDATE",
            "source_track": "B",
            "promotion_mode": "human_approved_candidate_only",
            "candidate_gate": {
                "decision": gate.get("decision"),
                "promotion_ready": bool(gate.get("promotion_ready")),
            },
            "top_candidate": (gate.get("metrics") or {}).get("top_candidate"),
            "runtime_constraints": {
                "research_only": True,
                "target_board_measurement_required_for_final_promotion": True,
                "auto_release_enabled": False,
                "live_trigger_auto_enabled": False,
            },
            "evidence": {
                "manual_lock": str(args.lock_out.resolve()),
                "gate_json": str(args.gate_json.resolve()),
            },
        }
        args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
        args.candidate_out.write_text(json.dumps(candidate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        promoted_doc = {
            "schema": "gpu_edge_track_a_promoted_v1",
            "promoted_at_utc": _now(),
            "status": "PROMOTED_TRACK_A_CANDIDATE",
            "checks": {
                "gate_go_candidate": gate_ok,
                "manual_lock_approved": True,
                "target_board_final_promotion_pending": True,
            },
            "inputs": {
                "candidate": str(args.candidate_out.resolve()),
                "manual_lock": str(args.lock_out.resolve()),
                "gate_json": str(args.gate_json.resolve()),
            },
            "constraints": {
                "research_only": True,
                "target_board_measurement_required_for_final_promotion": True,
                "auto_live_binding": False,
            },
        }
        args.promoted_out.parent.mkdir(parents=True, exist_ok=True)
        args.promoted_out.write_text(json.dumps(promoted_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "approved": approved,
                "lock_out": str(args.lock_out),
                "candidate_out": str(args.candidate_out if approved else ""),
                "promoted_out": str(args.promoted_out if approved else ""),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
