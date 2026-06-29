#!/usr/bin/env python3
"""Record commander human gate attestation for 창업패키지 340 (G0/G3/G5)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/startup_package_ai_2026_submission_checklist_v1_latest.json"
ATTESTATION = ROOT / "reports/kstartup_startup_package_ai_human_gate_attestation_v1.json"

VALID_GATES = (
    "G0_eligibility",
    "G1_form_mapping",
    "G3_host_institution",
    "G4_ai_talent_2p",
    "G5_dry_run",
    "G6_submitted_complete",
)
VALID_STATUS = frozenset({"pass", "ready", "done", "confirmed", "todo", "fail"})
G6_NOTE_TEMPLATE = "K-Startup 제출완료 확인 · PMS={pms_task_id}"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": "kstartup_startup_package_ai_human_gate_attestation_v1", "gates": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Attest human grant gates for 340.")
    ap.add_argument("--gate", required=True, choices=VALID_GATES)
    ap.add_argument("--status", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument(
        "--note-file",
        type=Path,
        default=None,
        help="UTF-8 note file (Windows PowerShell 한글 인자 깨짐 회피).",
    )
    ap.add_argument(
        "--pms-task-id",
        default="",
        help="G6_submitted_complete 전용: note 비었을 때 내장 한글 템플릿에 삽입.",
    )
    ap.add_argument(
        "--set-upload-ready",
        action="store_true",
        help="Set ready_for_kstartup_upload true only if all blocker gates attested pass/ready/done.",
    )
    args = ap.parse_args()

    status = args.status.strip().lower()
    if status not in VALID_STATUS:
        raise SystemExit(f"invalid status: {args.status}")

    note = args.note.strip()
    if args.note_file is not None:
        note = args.note_file.read_text(encoding="utf-8-sig").strip()
    if not note and args.gate == "G6_submitted_complete" and str(args.pms_task_id or "").strip():
        note = G6_NOTE_TEMPLATE.format(pms_task_id=str(args.pms_task_id).strip())

    doc = _load(ATTESTATION)
    doc["schema"] = "kstartup_startup_package_ai_human_gate_attestation_v1"
    doc["program"] = "startup_package_ai_2026_340"
    doc["updated_at_utc"] = _utc()
    gates = doc.setdefault("gates", {})
    if not isinstance(gates, dict):
        gates = {}
        doc["gates"] = gates
    gates[args.gate] = {
        "status": status,
        "note": note,
        "attested_at_utc": _utc(),
        "attested_by": "commander",
    }

    checklist = _load(CHECKLIST)
    cl_gates = checklist.get("gates") if isinstance(checklist.get("gates"), dict) else {}
    blocker_ids = [gid for gid, row in cl_gates.items() if isinstance(row, dict) and row.get("blocker")]
    pass_set = frozenset({"pass", "ready", "done", "confirmed"})

    def _effective(gid: str) -> str:
        att = gates.get(gid) if isinstance(gates.get(gid), dict) else {}
        if str(att.get("status") or "").lower() in pass_set:
            return str(att["status"]).lower()
        row = cl_gates.get(gid) if isinstance(cl_gates.get(gid), dict) else {}
        return str(row.get("status") or "todo").lower()

    all_blockers_ok = all(_effective(gid) in pass_set for gid in blocker_ids)
    if args.set_upload_ready:
        if not all_blockers_ok:
            missing = [gid for gid in blocker_ids if _effective(gid) not in pass_set]
            raise SystemExit(f"cannot set upload ready; blockers incomplete: {missing}")
        doc["ready_for_kstartup_upload"] = True
        doc["ready_set_at_utc"] = _utc()
    else:
        doc["ready_for_kstartup_upload"] = bool(doc.get("ready_for_kstartup_upload")) and all_blockers_ok

    ATTESTATION.parent.mkdir(parents=True, exist_ok=True)
    ATTESTATION.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"attested {args.gate}={status} -> {ATTESTATION}")
    if doc.get("ready_for_kstartup_upload"):
        print("ready_for_kstartup_upload=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
