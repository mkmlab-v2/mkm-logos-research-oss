#!/usr/bin/env python3
"""[HYPO] Validate Han Vocology F12 adjudication record."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/han_vocology_overlay_manifest_v1.json"
OUT = ROOT / "reports/han_vocology_f12_adjudication_validation_v1_latest.json"

REQUIRED_IDS = {
    "base_license_verified",
    "overlay_geometry_plausible",
    "attribution_public_facing",
    "no_clinical_diagnosis_claim",
    "education_use_only_scope",
    "generative_anatomy_forbidden",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_record(record: dict[str, Any], *, manifest: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    entry_id = record.get("entry_id")
    entry = next((e for e in manifest.get("entries") or [] if e.get("entry_id") == entry_id), None)
    checks.append({"name": "manifest_entry_exists", "ok": entry is not None})

    ids = {c.get("item_id") for c in record.get("checklist") or []}
    checks.append({"name": "checklist_ids_complete", "ok": REQUIRED_IDS <= ids})

    decision = record.get("decision")
    if decision == "pending":
        checks.append({"name": "not_pending", "ok": False})
    else:
        checks.append({"name": "signed_at_present", "ok": bool(str(record.get("signed_at_utc") or "").strip())})
        checks.append({"name": "reviewer_present", "ok": bool(str(record.get("reviewer_display") or "").strip())})
        all_passed = all(bool(c.get("passed")) for c in record.get("checklist") or [])
        checks.append({"name": "checklist_all_passed", "ok": all_passed if decision != "rejected" else True})

    checks.append({"name": "clinical_ack", "ok": record.get("clinical_claim_forbidden_ack") is True})
    checks.append(
        {
            "name": "send_gate_stays_hold",
            "ok": record.get("send_gate_after_adjudication") in ("HOLD", "HOLD_LEGAL_REVIEW"),
        }
    )
    checks.append({"name": "schema", "ok": record.get("schema") == "han_vocology_f12_adjudication_record_v1"})

    ok = all(c["ok"] for c in checks)
    apply_allowed = ok and decision in ("approved_education_internal", "approved_with_reservations", "rejected")
    return {"ok": ok, "apply_allowed": apply_allowed, "checks": checks, "decision": decision}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record-json", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()

    record = json.loads(args.record_json.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = validate_record(record, manifest=manifest)
    result["generated_at_utc"] = _utc()
    result["record"] = str(args.record_json)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "apply_allowed": result["apply_allowed"]}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
