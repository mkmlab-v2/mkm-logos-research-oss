#!/usr/bin/env python3
"""Report GT approval progress toward strict production minimum."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PARENTS = {"TY", "SY", "TE", "SE"}

DEFAULT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_LABELED_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_labeled_queue_top126_latest.jsonl"
DEFAULT_OUT = ART / "sasang_gt_approval_progress_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _valid_gt_count(path: Path) -> int:
    n = 0
    for row in _read_jsonl(path):
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--labeled-queue", type=Path, default=DEFAULT_LABELED_QUEUE)
    ap.add_argument("--target-min-gt", type=int, default=128)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.labeled_queue.is_file():
        print(f"ERROR: missing labeled queue file: {args.labeled_queue}")
        return 2

    gt_now = _valid_gt_count(args.gt)
    approved = 0
    for row in _read_jsonl(args.labeled_queue):
        status = str(row.get("label_status") or "").strip().upper()
        approved_parent = str(row.get("approved_parent") or "").strip().upper()
        if status == "APPROVED_HUMAN_LABEL" and approved_parent in PARENTS:
            approved += 1

    target = int(args.target_min_gt)
    needed_now = max(0, target - gt_now)
    needed_after_current_approval = max(0, target - (gt_now + approved))
    readiness_after_approval = needed_after_current_approval == 0

    doc = {
        "schema": "sasang_gt_approval_progress_v1",
        "generated_at_utc": _now(),
        "gt_valid_rows_current": gt_now,
        "target_min_gt_rows": target,
        "approved_rows_in_queue": approved,
        "needed_rows_now": needed_now,
        "needed_rows_after_current_approval": needed_after_current_approval,
        "can_reach_target_with_current_approval": readiness_after_approval,
        "policy": {
            "approved_human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"approved_rows_in_queue={approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
