#!/usr/bin/env python3
"""[HYPO] Apply validated rib55 adjudication record to manifest (no external send unlock)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT_REPORT = ROOT / "reports/rib55_overlay_adjudication_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record-json", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from scripts.validate_rib55_overlay_adjudication_v1 import validate_record

    if not args.record_json.is_file():
        raise SystemExit(f"missing record: {args.record_json}")
    if not args.manifest.is_file():
        raise SystemExit(f"missing manifest: {args.manifest}")

    record = _load(args.record_json)
    manifest = _load(args.manifest)
    validation = validate_record(record, manifest=manifest)
    if not validation.get("apply_allowed"):
        print(json.dumps({"ok": False, "reason": "validation_failed", "validation": validation}, ensure_ascii=False))
        return 1

    entry_id = record["entry_id"]
    decision = record["decision"]
    status_map = {
        "approved_education_internal": "adjudicated_education_internal",
        "approved_with_reservations": "adjudicated_with_reservations",
        "rejected": "rejected",
    }
    new_status = status_map.get(decision)
    if not new_status:
        print(json.dumps({"ok": False, "reason": "bad_decision"}, ensure_ascii=False))
        return 1

    try:
        record_rel = args.record_json.relative_to(ROOT).as_posix()
    except ValueError:
        record_rel = args.record_json.as_posix()

    updated = False
    for entry in manifest.get("entries") or []:
        if entry.get("entry_id") != entry_id:
            continue
        entry["status"] = new_status
        entry["adjudication"] = {
            "required": decision != "rejected",
            "signed_by": record.get("reviewer_display"),
            "reviewer_role": record.get("reviewer_role"),
            "signed_at": record.get("signed_at_utc"),
            "decision": decision,
            "notes": record.get("notes_ko"),
            "reservations": record.get("reservations_ko"),
            "checklist": record.get("checklist"),
            "record_path": record_rel,
        }
        updated = True
        break

    if not updated:
        print(json.dumps({"ok": False, "reason": "entry_not_found", "entry_id": entry_id}, ensure_ascii=False))
        return 1

    manifest["send_gate"] = "HOLD"
    manifest["ready_for_external_send"] = False
    manifest["adjudication_applied_at_utc"] = _utc()

    report = {
        "schema": "rib55_overlay_adjudication_apply_v1",
        "generated_at_utc": _utc(),
        "entry_id": entry_id,
        "new_status": new_status,
        "dry_run": args.dry_run,
        "send_gate": manifest["send_gate"],
        "ready_for_external_send": manifest["ready_for_external_send"],
        "validation_ok": validation.get("ok"),
    }

    if not args.dry_run:
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "dry_run": args.dry_run, "new_status": new_status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
