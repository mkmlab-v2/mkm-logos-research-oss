#!/usr/bin/env python3
"""Patient intake SEND_GATE — internal PoC lane only; external stays HOLD until legal."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/patient_intake_send_gate_v1_latest.json"
SOLAPI_DRY = ROOT / "docs/final/artifacts/patient_intake_solapi_dry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _all_checklist_true(checklist: dict[str, Any]) -> bool:
    return all(bool(v) for v in checklist.values())


def evaluate(doc: dict[str, Any]) -> dict[str, Any]:
    checklist = doc.get("checklist") or {}
    ready_internal = _all_checklist_true(checklist)
    send_gate = doc.get("send_gate", "HOLD")
    ok = True
    reasons: list[str] = []

    if ready_internal:
        if send_gate != "READY_INTERNAL_POC":
            ok = False
            reasons.append("send_gate must be READY_INTERNAL_POC when checklist complete")
        if doc.get("ready_for_external_send") is True:
            ok = False
            reasons.append("ready_for_external_send must stay false for internal PoC lane")
        if not doc.get("ready_internal_poc"):
            ok = False
            reasons.append("ready_internal_poc flag missing")
    elif send_gate != "HOLD":
        ok = False
        reasons.append(f"send_gate must be HOLD when checklist incomplete (got {send_gate})")

    if not SOLAPI_DRY.is_file():
        ok = False
        reasons.append(f"missing {SOLAPI_DRY.name} — run build_patient_intake_solapi_dry_v1.py")

    return {
        "ok": ok,
        "send_gate": send_gate,
        "ready_internal_poc": ready_internal,
        "ready_for_external_send": doc.get("ready_for_external_send"),
        "reasons": reasons,
    }


def confirm_internal_poc(doc: dict[str, Any]) -> dict[str, Any]:
    checklist = dict(doc.get("checklist") or {})
    checklist["public_facing_v17_reviewed"] = True
    checklist["commander_internal_poc_ack"] = True
    doc["checklist"] = checklist
    doc["send_gate"] = "READY_INTERNAL_POC"
    doc["ready_internal_poc"] = True
    doc["ready_for_external_send"] = False
    doc["confirmed_at_utc"] = _utc()
    doc["generated_at_utc"] = _utc()
    doc["operator_note"] = (
        "Internal PoC lane only — Solapi/SMS test webhook allowed; "
        "mass external alimtalk remains HOLD until legal sign-off."
    )
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm-internal-poc", action="store_true", help="Commander ack: internal PoC lane only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not GATE.is_file():
        print(json.dumps({"ok": False, "error": f"missing {GATE}"}))
        return 2

    doc = json.loads(GATE.read_text(encoding="utf-8"))
    if args.confirm_internal_poc:
        doc = confirm_internal_poc(doc)
        GATE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = evaluate(doc)
    payload = {**result, "artifact": str(GATE.relative_to(ROOT)).replace("\\", "/")}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
