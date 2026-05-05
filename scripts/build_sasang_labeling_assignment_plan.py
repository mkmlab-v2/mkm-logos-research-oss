#!/usr/bin/env python3
"""Build reviewer assignment plan for Sasang labeling sheet."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SHEET = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_sheet_top126_latest.csv"
DEFAULT_PLAN = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_assignment_plan_latest.json"
DEFAULT_REPORT = ART / "sasang_gt_labeling_assignment_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet-csv", type=Path, default=DEFAULT_SHEET)
    ap.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--reviewers", nargs="+", default=["R1", "R2", "R3"])
    args = ap.parse_args()

    if not args.sheet_csv.is_file():
        print(f"ERROR: missing labeling sheet: {args.sheet_csv}")
        return 2
    reviewers = [r.strip() for r in args.reviewers if r.strip()]
    if not reviewers:
        print("ERROR: reviewers list is empty")
        return 2

    rows = []
    with args.sheet_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = str(row.get("sample_id") or "").strip()
            if sid:
                rows.append(row)

    assignments = {r: [] for r in reviewers}
    for i, row in enumerate(rows):
        reviewer = reviewers[i % len(reviewers)]
        assignments[reviewer].append(
            {
                "sample_id": str(row.get("sample_id") or "").strip(),
                "suggested_parent": str(row.get("suggested_parent") or "").strip(),
                "suggested_confidence": row.get("suggested_confidence"),
                "priority_score": row.get("priority_score"),
                "source_file": str(row.get("source_file") or "").strip(),
            }
        )

    plan = {
        "schema": "sasang_gt_labeling_assignment_plan_v1",
        "generated_at_utc": _now(),
        "sheet_path": str(args.sheet_csv.resolve()),
        "reviewers": reviewers,
        "assignments": assignments,
        "policy": {
            "human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.plan_out.parent.mkdir(parents=True, exist_ok=True)
    args.plan_out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "sasang_gt_labeling_assignment_report_v1",
        "generated_at_utc": _now(),
        "plan_path": str(args.plan_out.resolve()),
        "reviewer_count": len(reviewers),
        "total_rows": len(rows),
        "rows_per_reviewer": {k: len(v) for k, v in assignments.items()},
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.plan_out}")
    print(f"WROTE: {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
