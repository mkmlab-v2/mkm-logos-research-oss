#!/usr/bin/env python3
"""What-if analysis: strict readiness if top queue rows get approved."""
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
DEFAULT_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_priority_top126_latest.jsonl"
DEFAULT_OUT = ART / "sasang_gt_approval_whatif_latest.json"


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


def _gt_ids(path: Path) -> set[str]:
    out: set[str] = set()
    for row in _read_jsonl(path):
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            out.add(sid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--priority-queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--target-min-gt", type=int, default=128)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.priority_queue.is_file():
        print(f"ERROR: missing priority queue file: {args.priority_queue}")
        return 2

    gt_ids = _gt_ids(args.gt)
    queue_rows = _read_jsonl(args.priority_queue)
    queue_ids = {str(r.get("sample_id") or "").strip() for r in queue_rows if str(r.get("sample_id") or "").strip()}
    queue_ids = {x for x in queue_ids if x and x not in gt_ids}

    gt_now = len(gt_ids)
    queue_unique = len(queue_ids)
    target = int(args.target_min_gt)
    needed_now = max(0, target - gt_now)
    needed_after_full_approval = max(0, target - (gt_now + queue_unique))
    can_hit_target = needed_after_full_approval == 0

    doc = {
        "schema": "sasang_gt_approval_whatif_v1",
        "generated_at_utc": _now(),
        "gt_valid_rows_current": gt_now,
        "priority_queue_unique_rows": queue_unique,
        "target_min_gt_rows": target,
        "needed_rows_now": needed_now,
        "needed_rows_after_full_priority_approval": needed_after_full_approval,
        "can_hit_target_if_full_priority_approved": can_hit_target,
        "policy": {
            "human_approval_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"can_hit_target_if_full_priority_approved={can_hit_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
