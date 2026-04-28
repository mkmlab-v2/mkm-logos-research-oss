#!/usr/bin/env python3
"""Merge human-labeled Sasang queue rows into authoritative GT safely.

Only rows with `label_status=APPROVED_HUMAN_LABEL` are merged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PARENTS = {"TY", "SY", "TE", "SE"}

DEFAULT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_LABELED = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_priority_top126_latest.jsonl"
DEFAULT_OUT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "sasang_gt_merge_report_latest.json"


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--labeled-queue", type=Path, default=DEFAULT_LABELED)
    ap.add_argument("--out-gt", type=Path, default=DEFAULT_OUT_GT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--write", action="store_true", help="Actually write merged GT output.")
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.labeled_queue.is_file():
        print(f"ERROR: missing labeled queue file: {args.labeled_queue}")
        return 2

    gt_rows = _read_jsonl(args.gt)
    queue_rows = _read_jsonl(args.labeled_queue)
    by_sid: dict[str, dict[str, Any]] = {}
    for row in gt_rows:
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            by_sid[sid] = row

    approved = 0
    inserted = 0
    updated = 0
    for row in queue_rows:
        status = str(row.get("label_status") or "").strip().upper()
        if status != "APPROVED_HUMAN_LABEL":
            continue
        sid = str(row.get("sample_id") or "").strip()
        label = str(row.get("approved_parent") or row.get("suggested_parent") or "").strip().upper()
        if not sid or label not in PARENTS:
            continue
        approved += 1
        if sid in by_sid:
            current = by_sid[sid]
            prev = str(current.get("expected_parent") or "").strip().upper()
            if prev != label:
                current["expected_parent"] = label
                current["label_source"] = "human_label_queue_merge"
                updated += 1
        else:
            by_sid[sid] = {
                "sample_id": sid,
                "text": f"queued_sample_id={sid}",
                "expected_parent": label,
                "cohort": "GT_REAL_LATEST",
                "annotation_version": "v1",
                "label_source": "human_label_queue_merge",
            }
            inserted += 1

    merged_rows = [by_sid[sid] for sid in sorted(by_sid)]
    if args.write:
        _write_jsonl(args.out_gt, merged_rows)

    report = {
        "schema": "sasang_gt_merge_report_v1",
        "gt_path": str(args.gt.resolve()),
        "labeled_queue_path": str(args.labeled_queue.resolve()),
        "out_gt_path": str(args.out_gt.resolve()),
        "write_mode": bool(args.write),
        "gt_initial_rows": len(gt_rows),
        "approved_queue_rows": approved,
        "inserted_rows": inserted,
        "updated_rows": updated,
        "gt_final_rows": len(merged_rows),
        "policy": {
            "only_approved_human_labels_merged": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.report}")
    print(f"approved_queue_rows={approved}, inserted={inserted}, updated={updated}")
    if not args.write:
        print("DRY-RUN: no GT file changes written. Re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
