#!/usr/bin/env python3
"""[HYPO] Validate rib55 overlay human adjudication record against schema + prereqs."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/rib55_overlay_adjudication_record_v1.schema.json"
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT = ROOT / "reports/rib55_overlay_adjudication_validation_v1_latest.json"
ART = ROOT / "docs/final/artifacts/rib55_overlay_adjudication_validation_v1_latest.json"

REQUIRED_CHECKLIST_IDS = {
    "base_license_verified",
    "overlay_geometry_plausible",
    "angle_label_theory_not_measurement",
    "no_clinical_diagnosis_claim",
    "l0_l1_ablation_reviewed",
    "education_use_only_scope",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any], *, manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise RuntimeError("jsonschema required") from exc

    schema = _load(SCHEMA_PATH)
    jsonschema.Draft7Validator(schema).validate(record)

    checks: list[dict[str, Any]] = []
    entry_id = record.get("entry_id")
    entries = manifest.get("entries") or []
    entry = next((e for e in entries if e.get("entry_id") == entry_id), None)
    checks.append({"name": "manifest_entry_exists", "ok": entry is not None})

    ids = {c.get("item_id") for c in record.get("checklist") or []}
    checks.append({"name": "checklist_ids_complete", "ok": REQUIRED_CHECKLIST_IDS <= ids})

    decision = record.get("decision")
    signed = str(record.get("signed_at_utc") or "").strip()
    reviewer = str(record.get("reviewer_display") or "").strip()
    checklist = record.get("checklist") or []

    if decision == "pending":
        checks.append({"name": "not_pending_for_apply", "ok": False, "note": "decision still pending"})
    else:
        checks.append({"name": "signed_at_present", "ok": bool(signed)})
        checks.append({"name": "reviewer_display_present", "ok": bool(reviewer)})
        all_passed = all(bool(c.get("passed")) for c in checklist)
        checks.append({"name": "checklist_all_passed", "ok": all_passed if decision != "rejected" else True})
        if decision == "rejected":
            checks.append({"name": "rejection_notes", "ok": bool(str(record.get("notes_ko") or "").strip())})

    checks.append({"name": "clinical_ack", "ok": record.get("clinical_claim_forbidden_ack") is True})
    checks.append(
        {
            "name": "send_gate_stays_hold",
            "ok": record.get("send_gate_after_adjudication") in ("HOLD", "HOLD_LEGAL_REVIEW"),
        }
    )
    checks.append({"name": "manifest_send_gate_hold", "ok": manifest.get("send_gate") == "HOLD"})

    ok = all(c["ok"] for c in checks)
    apply_allowed = ok and decision in ("approved_education_internal", "approved_with_reservations", "rejected")

    return {
        "schema": "rib55_overlay_adjudication_validation_v1",
        "generated_at_utc": _utc(),
        "record_entry_id": entry_id,
        "decision": decision,
        "checks": checks,
        "ok": ok,
        "apply_allowed": apply_allowed,
        "send_gate_unlocked": False,
        "ready_for_external_send": False,
        "note_ko": "adjudication 통과해도 외부 송출 HOLD 유지 — legal 별도 해제",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record-json", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    if not SCHEMA_PATH.is_file():
        raise SystemExit(f"missing schema: {SCHEMA_PATH}")
    if not args.record_json.is_file():
        raise SystemExit(f"missing record: {args.record_json}")
    if not args.manifest.is_file():
        raise SystemExit(f"missing manifest: {args.manifest}")

    record = _load(args.record_json)
    manifest = _load(args.manifest)
    report = validate_record(record, manifest=manifest)

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    ART.parent.mkdir(parents=True, exist_ok=True)
    ART.write_text(text, encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "apply_allowed": report["apply_allowed"], "out": str(args.out_json)}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
