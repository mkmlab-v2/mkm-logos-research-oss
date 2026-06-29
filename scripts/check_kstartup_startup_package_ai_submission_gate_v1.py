#!/usr/bin/env python3
"""Hard gate for 창업패키지 340 — blocker gates must pass before upload/autofill.

Prevents majung-style submit: paste/forbidden pass while G0/G3/G5 still todo.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/startup_package_ai_2026_submission_checklist_v1_latest.json"
ATTESTATION = ROOT / "reports/kstartup_startup_package_ai_human_gate_attestation_v1.json"
FORBIDDEN_REPORT = ROOT / "reports/kstartup_startup_package_ai_forbidden_scan_latest.json"
DEFAULT_OUT = ROOT / "reports/kstartup_startup_package_ai_submission_gate_latest.json"

PASS_STATUSES = frozenset({"done", "pass", "ready", "confirmed"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate_status(checklist: dict[str, Any], attestation: dict[str, Any], gate_id: str) -> str:
    gates = checklist.get("gates") if isinstance(checklist.get("gates"), dict) else {}
    row = gates.get(gate_id) if isinstance(gates.get(gate_id), dict) else {}
    base = str(row.get("status") or "todo").lower()
    att_gates = attestation.get("gates") if isinstance(attestation.get("gates"), dict) else {}
    att_row = att_gates.get(gate_id) if isinstance(att_gates.get(gate_id), dict) else {}
    att = str(att_row.get("status") or "").lower()
    if att in PASS_STATUSES:
        return att
    return base


def evaluate(*, draft_ok: bool) -> dict[str, Any]:
    checklist = _load(CHECKLIST)
    attestation = _load(ATTESTATION)
    forbidden = _load(FORBIDDEN_REPORT)

    gates = checklist.get("gates") if isinstance(checklist.get("gates"), dict) else {}
    blockers_failed: list[dict[str, Any]] = []
    for gate_id, row in gates.items():
        if not isinstance(row, dict) or not row.get("blocker"):
            continue
        status = _gate_status(checklist, attestation, gate_id)
        if status not in PASS_STATUSES:
            blockers_failed.append(
                {
                    "gate_id": gate_id,
                    "label": row.get("label"),
                    "status": status,
                    "owner": row.get("owner"),
                }
            )

    forbidden_ok = bool(forbidden.get("ok") or forbidden.get("pass"))
    ready_flag = bool(checklist.get("ready_for_kstartup_upload"))
    att_ready = bool(attestation.get("ready_for_kstartup_upload"))

    reasons: list[str] = []
    if blockers_failed:
        reasons.append("blocker_gates_incomplete")
    if not forbidden_ok:
        reasons.append("forbidden_scan_not_pass")
    if not draft_ok:
        if not ready_flag and not att_ready:
            reasons.append("ready_for_kstartup_upload_false")

    upload_ok = not reasons
    return {
        "schema": "kstartup_startup_package_ai_submission_gate_v1",
        "generated_at_utc": _utc(),
        "program": "startup_package_ai_2026_340",
        "checklist_path": str(CHECKLIST.relative_to(ROOT)).replace("\\", "/"),
        "attestation_path": str(ATTESTATION.relative_to(ROOT)).replace("\\", "/"),
        "draft_mode": draft_ok,
        "upload_ok": upload_ok,
        "ready_for_kstartup_upload": ready_flag or att_ready,
        "forbidden_scan_ok": forbidden_ok,
        "blockers_failed": blockers_failed,
        "reasons": reasons,
        "remediation": [
            "Human: complete G0/G3/G5 then run attest script.",
            "py scripts/attest_kstartup_startup_package_ai_human_gates_v1.py --gate G0_eligibility --status pass --note \"...\"",
            "py scripts/check_kstartup_startup_package_ai_forbidden_phrases_v1.py",
            "Only when upload_ok: K-Startup 임시저장/제출완료",
        ],
        "boundary_ack": "upload_ok does not imply selection.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="340 submission hard gate (exit 1 if not upload-ready).")
    ap.add_argument("--draft-ok", action="store_true", help="Allow paste build; still report blockers.")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out = evaluate(draft_ok=bool(args.draft_ok))
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if out["upload_ok"]:
        print(f"SUBMISSION_GATE OK -> {out_path}")
        return 0

    print(f"SUBMISSION_GATE FAIL ({', '.join(out['reasons'])}) -> {out_path}")
    for row in out["blockers_failed"]:
        print(f"  - {row['gate_id']}: {row['status']} ({row.get('label')})")
    return 1 if not args.draft_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
