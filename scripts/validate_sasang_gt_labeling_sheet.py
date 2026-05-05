#!/usr/bin/env python3
"""Validate human labeling sheet consistency before import/merge."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PARENTS = {"TY", "SY", "TE", "SE"}
ALLOWED_STATUS = {"PENDING_HUMAN_LABEL", "APPROVED_HUMAN_LABEL", "REJECTED_HUMAN_LABEL"}

DEFAULT_SHEET = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_sheet_top126_latest.csv"
DEFAULT_OUT = ART / "sasang_gt_labeling_sheet_validation_latest.json"


def _norm(v: str) -> str:
    return (v or "").strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet-csv", type=Path, default=DEFAULT_SHEET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.sheet_csv.is_file():
        print(f"ERROR: missing labeling sheet: {args.sheet_csv}")
        return 2

    total = 0
    approved = 0
    pending = 0
    rejected = 0
    invalid: list[dict[str, str | int]] = []
    seen_ids: set[str] = set()
    dupes = 0

    with args.sheet_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            total += 1
            sid = str(row.get("sample_id") or "").strip()
            status = _norm(str(row.get("label_status") or "PENDING_HUMAN_LABEL"))
            approved_parent = _norm(str(row.get("approved_parent") or ""))

            if sid:
                if sid in seen_ids:
                    dupes += 1
                seen_ids.add(sid)

            if status not in ALLOWED_STATUS:
                invalid.append({"line": idx, "sample_id": sid, "issue": "invalid_label_status"})
                continue
            if not sid:
                invalid.append({"line": idx, "sample_id": sid, "issue": "missing_sample_id"})
                continue
            if status == "APPROVED_HUMAN_LABEL":
                approved += 1
                if approved_parent not in PARENTS:
                    invalid.append({"line": idx, "sample_id": sid, "issue": "approved_without_valid_parent"})
            elif status == "PENDING_HUMAN_LABEL":
                pending += 1
            elif status == "REJECTED_HUMAN_LABEL":
                rejected += 1

    valid = len(invalid) == 0 and dupes == 0
    payload = {
        "schema": "sasang_gt_labeling_sheet_validation_v1",
        "sheet_csv": str(args.sheet_csv.resolve()),
        "total_rows": total,
        "approved_rows": approved,
        "pending_rows": pending,
        "rejected_rows": rejected,
        "duplicate_sample_id_rows": dupes,
        "invalid_rows_count": len(invalid),
        "valid_for_import": valid,
        "invalid_rows": invalid[:100],
        "policy": {
            "approved_requires_parent": True,
            "auto_label_forbidden": True,
            "human_signoff_required": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"valid_for_import={valid}")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
