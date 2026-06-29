#!/usr/bin/env python3
"""Validate personadiary_btrack_export_v1 JSON files in manual B-track inbox (no upload)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_btrack_export_v1.schema.json"
DEFAULT_INBOX = ROOT / "reports/constitution/btrack_pilot/personadiary_export_inbox"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "reports/personadiary_btrack_export_inbox_validation_latest.json",
    )
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    inbox = args.inbox_dir
    inbox.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    ok_count = 0
    for path in sorted(inbox.glob("*.json")):
        row = {"file": str(path.relative_to(ROOT)).replace("\\", "/"), "ok": False}
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=doc, schema=schema)
            if doc.get("auto_upload") is not False:
                raise ValueError("auto_upload must be false")
            row["ok"] = True
            row["pseudonym_id"] = doc.get("pseudonym_id")
            ok_count += 1
        except Exception as exc:  # noqa: BLE001 — aggregate validation report
            row["error"] = str(exc)[:280]
        rows.append(row)

    summary = {
        "schema": "personadiary_btrack_export_inbox_validation_v1",
        "validated_at_utc": _utc_now(),
        "inbox_dir": str(inbox.relative_to(ROOT)).replace("\\", "/"),
        "files_seen": len(rows),
        "files_ok": ok_count,
        "research_only": True,
        "hypothesis_tier": "B",
        "auto_upload": False,
        "rows": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json} ok={ok_count}/{len(rows)}")
    return 0 if ok_count == len(rows) else (1 if rows else 0)


if __name__ == "__main__":
    raise SystemExit(main())
