#!/usr/bin/env python3
"""Run monthly promotion drill for emotion-state control (approve + reject)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "emotion_state_promotion_gate_latest.json"
DEFAULT_MAPPING = ART / "emotion_state_mapping_latest.json"
DEFAULT_SUMMARY = ART / "emotion_state_monthly_promotion_drill_summary_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _run_lock(
    promotion_gate: Path,
    mapping_json: Path,
    out_lock: Path,
    out_candidate: Path,
    reviewer: str,
    note: str,
    approve: bool,
) -> dict[str, Any]:
    cmd = [
        "py",
        str(ROOT / "scripts" / "lock_emotion_state_manual_promotion_decision_v1.py"),
        "--promotion-gate",
        str(promotion_gate),
        "--mapping-json",
        str(mapping_json),
        "--reviewer",
        reviewer,
        "--decision-note",
        note,
        "--out",
        str(out_lock),
        "--candidate-out",
        str(out_candidate),
    ]
    if approve:
        cmd.append("--approve")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    approve_lock = ART / "emotion_state_manual_promotion_decision_lock_drill_approve_latest.json"
    approve_candidate = ART / "emotion_state_track_a_candidate_drill_approve_latest.json"
    reject_lock = ART / "emotion_state_manual_promotion_decision_lock_drill_reject_latest.json"
    reject_candidate = ART / "emotion_state_track_a_candidate_drill_reject_latest.json"

    approved_run = _run_lock(
        args.promotion_gate,
        args.mapping_json,
        approve_lock,
        approve_candidate,
        args.reviewer,
        "monthly drill approve path",
        approve=True,
    )
    rejected_run = _run_lock(
        args.promotion_gate,
        args.mapping_json,
        reject_lock,
        reject_candidate,
        args.reviewer,
        "monthly drill reject path",
        approve=False,
    )

    approve_doc = _load_json(approve_lock)
    reject_doc = _load_json(reject_lock)
    approve_candidate_doc = _load_json(approve_candidate)
    reject_candidate_doc = _load_json(reject_candidate)

    approve_ok = (
        approved_run["returncode"] == 0
        and str(approve_doc.get("final_decision")) == "approved"
        and str(approve_candidate_doc.get("status")) == "APPROVED_CANDIDATE"
    )
    reject_ok = (
        rejected_run["returncode"] == 0
        and str(reject_doc.get("final_decision")) == "rejected"
        and (not reject_candidate_doc)
    )

    summary = {
        "schema": "emotion_state_monthly_promotion_drill_summary_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "promotion_gate": str(args.promotion_gate).replace("\\", "/"),
            "mapping_json": str(args.mapping_json).replace("\\", "/"),
        },
        "approve_case": {
            "lock_json": str(approve_lock).replace("\\", "/"),
            "candidate_json": str(approve_candidate).replace("\\", "/"),
            "returncode": approved_run["returncode"],
            "final_decision": approve_doc.get("final_decision"),
            "candidate_status": approve_candidate_doc.get("status"),
            "passed": approve_ok,
        },
        "reject_case": {
            "lock_json": str(reject_lock).replace("\\", "/"),
            "candidate_json": str(reject_candidate).replace("\\", "/"),
            "returncode": rejected_run["returncode"],
            "final_decision": reject_doc.get("final_decision"),
            "candidate_generated": bool(reject_candidate_doc),
            "passed": reject_ok,
        },
        "drill_passed": bool(approve_ok and reject_ok),
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "drill_passed": summary["drill_passed"], "summary_json": str(args.summary_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
