#!/usr/bin/env python3
"""Export Sasang GT priority queue to a human-labeling CSV sheet."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_priority_top126_latest.jsonl"
DEFAULT_CSV = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_sheet_top126_latest.csv"
DEFAULT_REPORT = ART / "sasang_gt_labeling_sheet_report_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.queue.is_file():
        print(f"ERROR: missing queue file: {args.queue}")
        return 2

    rows = _read_jsonl(args.queue)
    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "suggested_parent",
                "suggested_confidence",
                "source_file",
                "priority_score",
                "approved_parent",
                "label_status",
                "reviewer_note",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "sample_id": str(r.get("sample_id") or ""),
                    "suggested_parent": str(r.get("suggested_parent") or ""),
                    "suggested_confidence": r.get("suggested_confidence"),
                    "source_file": str(r.get("source_file") or ""),
                    "priority_score": r.get("priority_score"),
                    "approved_parent": "",
                    "label_status": "PENDING_HUMAN_LABEL",
                    "reviewer_note": "",
                }
            )

    report = {
        "schema": "sasang_gt_labeling_sheet_report_v1",
        "generated_at_utc": _now(),
        "queue_path": str(args.queue.resolve()),
        "sheet_path": str(args.csv_out.resolve()),
        "row_count": len(rows),
        "required_columns_for_merge": ["sample_id", "approved_parent", "label_status"],
        "label_status_allowed": ["PENDING_HUMAN_LABEL", "APPROVED_HUMAN_LABEL", "REJECTED_HUMAN_LABEL"],
        "policy": {
            "human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.csv_out}")
    print(f"WROTE: {args.report_out}")
    print(f"row_count={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
