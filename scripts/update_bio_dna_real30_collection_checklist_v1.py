# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.86, K:0.45, M:0.72}
# Balance: 91
# Purpose: Update real-30 DNA collection checklist entries safely from CLI.
# Keywords: bio, dna, checklist, tracker, sample, status, pipeline
"""Update `bio_dna_real30_collection_checklist_v1.json` sample status fields.

Usage examples:
  py scripts/update_bio_dna_real30_collection_checklist_v1.py --sample-id fp_m3847 --status in_progress --owner ops_team
  py scripts/update_bio_dna_real30_collection_checklist_v1.py --sample-id fp_m3847 --set consent_signed=true --set sample_collected=true
  py scripts/update_bio_dna_real30_collection_checklist_v1.py --sample-id fp_m3847 --advance-stage sequencing
  py scripts/update_bio_dna_real30_collection_checklist_v1.py --list-pending --limit 10
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CHECKLIST = Path("docs/final/artifacts/bio_dna_real30_collection_checklist_v1.json")

ALLOWED_STATUS = {"pending", "in_progress", "blocked", "done"}
BOOL_FIELDS = {
    "consent_signed",
    "sample_collected",
    "sequencing_started",
    "vcf_generated",
    "qc_pass",
    "pipeline_reflected",
}
STAGE_PRESETS: dict[str, dict[str, bool]] = {
    "consent": {
        "consent_signed": True,
        "sample_collected": True,
    },
    "sequencing": {
        "sequencing_started": True,
        "vcf_generated": True,
    },
    "qc": {
        "qc_pass": True,
    },
    "pipeline": {
        "pipeline_reflected": True,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_bool(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"expected boolean value, got: {text!r}")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"checklist not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_sample(payload: dict[str, Any], sample_id: str) -> dict[str, Any]:
    samples = payload.get("samples")
    if not isinstance(samples, list):
        raise ValueError("invalid checklist format: missing samples list")
    for row in samples:
        if str(row.get("sample_id")) == sample_id:
            return row
    raise ValueError(f"sample_id not found: {sample_id}")


def _list_pending(payload: dict[str, Any], limit: int) -> int:
    samples = payload.get("samples", [])
    pending = [s for s in samples if str(s.get("status")) != "done"]
    for row in pending[:limit]:
        sid = row.get("sample_id")
        status = row.get("status")
        owner = row.get("owner")
        flags = []
        for key in ("consent_signed", "sample_collected", "sequencing_started", "vcf_generated", "qc_pass", "pipeline_reflected"):
            if row.get(key):
                flags.append(key)
        print(f"{sid}\tstatus={status}\towner={owner}\tcompleted={','.join(flags) if flags else '-'}")
    print(f"pending_count={len(pending)} total={len(samples)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Update bio DNA real-30 collection checklist.")
    ap.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--sample-id", type=str, default=None)
    ap.add_argument("--status", type=str, choices=sorted(ALLOWED_STATUS), default=None)
    ap.add_argument("--owner", type=str, default=None)
    ap.add_argument("--notes", type=str, default=None)
    ap.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set boolean fields, e.g. --set consent_signed=true",
    )
    ap.add_argument(
        "--advance-stage",
        choices=sorted(STAGE_PRESETS.keys()),
        default=None,
        help="Apply stage preset booleans.",
    )
    ap.add_argument("--list-pending", action="store_true", help="List samples where status != done.")
    ap.add_argument("--limit", type=int, default=30, help="List output limit for --list-pending.")
    ap.add_argument("--dry-run", action="store_true", help="Print changes without writing file.")
    ns = ap.parse_args()

    payload = _load_json(ns.checklist)

    if ns.list_pending:
        return _list_pending(payload, max(1, ns.limit))

    if not ns.sample_id:
        raise ValueError("--sample-id is required unless --list-pending is used")

    sample = _find_sample(payload, ns.sample_id)
    changed: dict[str, Any] = {}

    if ns.status is not None and sample.get("status") != ns.status:
        sample["status"] = ns.status
        changed["status"] = ns.status
    if ns.owner is not None and sample.get("owner") != ns.owner:
        sample["owner"] = ns.owner
        changed["owner"] = ns.owner
    if ns.notes is not None and sample.get("notes") != ns.notes:
        sample["notes"] = ns.notes
        changed["notes"] = ns.notes

    if ns.advance_stage:
        for key, value in STAGE_PRESETS[ns.advance_stage].items():
            if sample.get(key) != value:
                sample[key] = value
                changed[key] = value

    for pair in ns.set:
        if "=" not in pair:
            raise ValueError(f"--set expects KEY=VALUE, got: {pair!r}")
        key, raw_value = pair.split("=", 1)
        key = key.strip()
        if key not in BOOL_FIELDS:
            raise ValueError(f"unsupported --set field: {key!r}. allowed={sorted(BOOL_FIELDS)}")
        value = _parse_bool(raw_value)
        if sample.get(key) != value:
            sample[key] = value
            changed[key] = value

    if not changed:
        print(f"no_change sample_id={ns.sample_id}")
        return 0

    payload["last_updated_utc"] = _utc_now()
    payload["last_update"] = {
        "sample_id": ns.sample_id,
        "changed_fields": changed,
        "updated_at_utc": payload["last_updated_utc"],
    }

    if ns.dry_run:
        print(json.dumps(payload["last_update"], ensure_ascii=False, indent=2))
        return 0

    _save_json(ns.checklist, payload)
    print(f"updated checklist={ns.checklist} sample_id={ns.sample_id} changed={sorted(changed.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
