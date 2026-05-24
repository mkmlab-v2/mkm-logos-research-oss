#!/usr/bin/env python3
"""Record commander in-chat approval and finalize prophecy release governance chain."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"
OUT = REP / "btrack_commander_approval_finalize_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _write_commander_lock(*, reviewer: str, note: str) -> Path:
    gate_path = ART / "prophecy_promotion_gates_v1_latest.json"
    if not gate_path.is_file():
        gate_path = REP / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else {}
    lock_path = ART / "prophecy_manual_promotion_decision_lock_v1_latest.json"
    lock_doc = {
        "schema": "prophecy_manual_promotion_decision_lock_v1",
        "locked_at_utc": _utc(),
        "final_decision": "approved",
        "reviewer": reviewer,
        "decision_note": note,
        "commander_in_chat_approval": True,
        "review_snapshot": {
            "promotion_recommendation": gate.get("promotion_recommendation"),
            "soft_passed": gate.get("soft_passed"),
            "combined_all_passed": gate.get("combined_all_passed"),
            "strict_pass_streak": gate.get("strict_pass_streak"),
        },
        "constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
            "a_track_candidate_only": True,
        },
    }
    lock_path.write_text(json.dumps(lock_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default="지휘관 in-chat 승인(2026-05-18): 180d v1 soft_band + Track A candidate bridge. live 별도.",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    lock_path = _write_commander_lock(reviewer=args.reviewer, note=args.note)
    steps.append({"step": "commander_lock", "path": str(lock_path), "exit_code": 0})

    rc = _run(
        [
            py,
            "scripts/apply_prophecy_human_approval_v1.py",
            "--reviewer",
            args.reviewer,
            "--note",
            args.note,
        ]
    )
    steps.append({"step": "apply_prophecy_human_approval", "exit_code": rc})

    rc = _run(
        [
            py,
            "scripts/apply_btrack_track_a_candidate_human_approval_v1.py",
            "--reviewer",
            args.reviewer,
            "--note",
            args.note,
        ]
    )
    steps.append({"step": "apply_btrack_track_a_candidate_human_approval", "exit_code": rc})

    rc = _run(
        [
            py,
            "scripts/build_prophecy_approved_candidate_release_checklist_v1.py",
            "--promotion-gate",
            "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
        ]
    )
    steps.append({"step": "release_checklist", "exit_code": rc})

    rc = _run([py, "scripts/build_prophecy_release_signoff_packet_v1.py"])
    steps.append({"step": "release_signoff_packet", "exit_code": rc})

    rc = _run([py, "scripts/refresh_gut_brain_btrack_promotion_status_v1.py"])
    steps.append({"step": "refresh_gut_brain", "exit_code": rc})

    # apply_* scripts call lock_prophecy_manual_promotion_decision_v1 (auto checklist);
    # commander in-chat approval wins — re-write lock after the chain.
    lock_path = _write_commander_lock(reviewer=args.reviewer, note=args.note)
    steps.append({"step": "commander_lock_final", "path": str(lock_path), "exit_code": 0})

    rc = _run(
        [
            py,
            "scripts/build_prophecy_approved_candidate_release_checklist_v1.py",
            "--promotion-gate",
            "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
        ]
    )
    steps.append({"step": "release_checklist_post_lock", "exit_code": rc})

    rc = _run([py, "scripts/build_prophecy_release_signoff_packet_v1.py"])
    steps.append({"step": "release_signoff_packet_post_lock", "exit_code": rc})

    checklist = json.loads(
        (ART / "prophecy_approved_candidate_release_checklist_v1_latest.json").read_text(encoding="utf-8")
    )
    packet = json.loads((ART / "prophecy_release_signoff_packet_v1_latest.json").read_text(encoding="utf-8"))

    ready = (checklist.get("summary") or {}).get("ready_for_release_signoff")
    pkt_status = packet.get("status")
    pack = {
        "schema": "btrack_commander_approval_finalize_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "reviewer": args.reviewer,
        "note": args.note,
        "steps": steps,
        "ready_for_release_signoff": ready,
        "release_packet_status": pkt_status,
        "live_trading_enabled": False,
        "operator_lines": [
            "- [MKM-APPROVE] Commander in-chat approval recorded.",
            f"- [MKM-APPROVE] release_checklist ready={ready}",
            f"- [MKM-APPROVE] release_packet status={pkt_status}",
        ],
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"ready_for_release_signoff={pack['ready_for_release_signoff']} packet={packet.get('status')}")
    return 0 if all(s.get("exit_code") == 0 for s in steps) else 2


if __name__ == "__main__":
    raise SystemExit(main())
