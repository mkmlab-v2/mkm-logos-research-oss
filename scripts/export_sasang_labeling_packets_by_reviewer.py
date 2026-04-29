#!/usr/bin/env python3
"""Export per-reviewer labeling CSV packets from assignment plan."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PLAN = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeling_assignment_plan_latest.json"
DEFAULT_OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "reviewer_packets"
DEFAULT_REPORT = ART / "sasang_labeling_packets_report_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.plan.is_file():
        print(f"ERROR: missing assignment plan: {args.plan}")
        return 2

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    assignments: dict[str, list[dict[str, Any]]] = plan.get("assignments") or {}
    if not isinstance(assignments, dict):
        print("ERROR: invalid assignment plan format")
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    counts: dict[str, int] = {}
    for reviewer, rows in assignments.items():
        if not isinstance(rows, list):
            continue
        out_csv = args.out_dir / f"sasang_gt_labeling_packet_{reviewer}.csv"
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
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
        files[reviewer] = str(out_csv.resolve())
        counts[reviewer] = len(rows)

    report = {
        "schema": "sasang_labeling_packets_report_v1",
        "assignment_plan_path": str(args.plan.resolve()),
        "packet_dir": str(args.out_dir.resolve()),
        "reviewer_packet_files": files,
        "rows_per_reviewer": counts,
        "policy": {
            "human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
