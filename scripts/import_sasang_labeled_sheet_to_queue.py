#!/usr/bin/env python3
"""Import human-labeled Sasang CSV sheet into labeled JSONL queue."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PARENTS = {"TY", "SY", "TE", "SE"}
ALLOWED_STATUS = {"PENDING_HUMAN_LABEL", "APPROVED_HUMAN_LABEL", "REJECTED_HUMAN_LABEL"}

DEFAULT_CSV = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_sheet_top126_latest.csv"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeled_queue_top126_latest.jsonl"
DEFAULT_REPORT = ART / "sasang_gt_labeled_import_report_latest.json"


def _norm_parent(v: str) -> str:
    return v.strip().upper()


def _norm_status(v: str) -> str:
    return v.strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet-csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.sheet_csv.is_file():
        print(f"ERROR: missing labeling sheet: {args.sheet_csv}")
        return 2

    rows_out: list[dict] = []
    total = 0
    approved = 0
    invalid = 0
    with args.sheet_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            sid = str(r.get("sample_id") or "").strip()
            suggested_parent = _norm_parent(str(r.get("suggested_parent") or ""))
            approved_parent = _norm_parent(str(r.get("approved_parent") or ""))
            status = _norm_status(str(r.get("label_status") or "PENDING_HUMAN_LABEL"))
            note = str(r.get("reviewer_note") or "").strip()
            src = str(r.get("source_file") or "").strip()
            pr = r.get("priority_score")
            sc = r.get("suggested_confidence")

            if not sid or status not in ALLOWED_STATUS:
                invalid += 1
                continue
            if suggested_parent and suggested_parent not in PARENTS:
                invalid += 1
                continue
            if approved_parent and approved_parent not in PARENTS:
                invalid += 1
                continue
            if status == "APPROVED_HUMAN_LABEL" and approved_parent not in PARENTS:
                invalid += 1
                continue

            if status == "APPROVED_HUMAN_LABEL":
                approved += 1

            row = {
                "sample_id": sid,
                "suggested_parent": suggested_parent or None,
                "approved_parent": approved_parent or None,
                "label_status": status,
                "reviewer_note": note,
                "source_file": src or None,
                "priority_score": float(pr) if isinstance(pr, str) and pr.strip() else None,
                "suggested_confidence": float(sc) if isinstance(sc, str) and sc.strip() else None,
            }
            rows_out.append(row)

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out) + ("\n" if rows_out else ""),
        encoding="utf-8",
    )
    report = {
        "schema": "sasang_gt_labeled_import_report_v1",
        "sheet_csv": str(args.sheet_csv.resolve()),
        "output_jsonl": str(args.out_jsonl.resolve()),
        "total_rows": total,
        "valid_rows": len(rows_out),
        "approved_rows": approved,
        "invalid_rows": invalid,
        "policy": {
            "approved_requires_parent": True,
            "auto_label_forbidden": True,
            "human_signoff_required": True,
        },
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_jsonl}")
    print(f"WROTE: {args.report_out}")
    print(f"approved_rows={approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
