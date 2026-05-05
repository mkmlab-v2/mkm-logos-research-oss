#!/usr/bin/env python3
"""Bulk-update review_status for Layer-5 review queue by case_id list."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_status_update_summary_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _read_case_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    if path.suffix.lower() == ".jsonl":
        for row in _read_jsonl(path):
            cid = row.get("case_id")
            if isinstance(cid, str) and cid.strip():
                ids.add(cid.strip())
        return ids

    # csv/txt fallback: first column or line
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        if path.suffix.lower() == ".csv":
            reader = csv.reader(fh)
            for row in reader:
                if not row:
                    continue
                cid = str(row[0]).strip()
                if cid and cid.lower() != "case_id" and not cid.startswith("#"):
                    ids.add(cid)
        else:
            for line in fh:
                cid = line.strip()
                if cid and not cid.startswith("#"):
                    ids.add(cid)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--ids-file", type=Path, required=True, help="CSV/TXT/JSONL file containing case_id list")
    ap.add_argument("--set-status", choices=("approved", "rejected", "draft"), required=True)
    ap.add_argument("--only-draft", action="store_true", help="Update only rows currently in draft")
    args = ap.parse_args()

    ids = _read_case_ids(args.ids_file)
    rows = _read_jsonl(args.input_jsonl)
    updated = 0
    missing_ids = set(ids)

    for row in rows:
        cid = row.get("case_id")
        if not isinstance(cid, str):
            continue
        if cid not in ids:
            continue
        current = str(row.get("review_status", "draft")).lower()
        if args.only_draft and current != "draft":
            continue
        row["review_status"] = args.set_status
        updated += 1
        if cid in missing_ids:
            missing_ids.remove(cid)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "schema": "layer5_review_status_update_summary_v1",
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "ids_file": str(args.ids_file).replace("\\", "/"),
        "set_status": args.set_status,
        "only_draft": bool(args.only_draft),
        "requested_id_count": len(ids),
        "updated_row_count": updated,
        "missing_id_count": len(missing_ids),
        "missing_ids_preview": sorted(list(missing_ids))[:20],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "updated": updated, "missing": len(missing_ids)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
