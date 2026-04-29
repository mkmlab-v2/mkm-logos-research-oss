#!/usr/bin/env python3
"""Simulate GT merge impact from priority queue approvals (no writes)."""
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
DEFAULT_PRIORITY = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_priority_top126_latest.jsonl"
DEFAULT_OUT = ART / "sasang_gt_merge_impact_simulation_latest.json"


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
    ids: set[str] = set()
    for row in _read_jsonl(path):
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            ids.add(sid)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--priority-queue", type=Path, default=DEFAULT_PRIORITY)
    ap.add_argument("--approve-top-n", type=int, default=126)
    ap.add_argument("--strict-target-min-gt", type=int, default=128)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.priority_queue.is_file():
        print(f"ERROR: missing priority queue file: {args.priority_queue}")
        return 2

    gt_ids = _gt_ids(args.gt)
    queue = _read_jsonl(args.priority_queue)
    n = max(0, int(args.approve_top_n))
    selected = queue[:n]
    approved_ids = {
        str(r.get("sample_id") or "").strip()
        for r in selected
        if str(r.get("sample_id") or "").strip()
    }
    approved_ids = {x for x in approved_ids if x not in gt_ids}

    gt_now = len(gt_ids)
    added = len(approved_ids)
    gt_after = gt_now + added
    target = int(args.strict_target_min_gt)
    needed_after = max(0, target - gt_after)
    strict_pairable_ready = gt_after >= target

    payload = {
        "schema": "sasang_gt_merge_impact_simulation_v1",
        "generated_at_utc": _now(),
        "gt_valid_rows_current": gt_now,
        "approve_top_n": n,
        "unique_new_rows_from_selected": added,
        "gt_rows_after_simulated_merge": gt_after,
        "strict_target_min_gt_rows": target,
        "needed_rows_after_simulation": needed_after,
        "strict_pairable_ready_after_simulation": strict_pairable_ready,
        "policy": {
            "simulation_only_no_gt_writes": True,
            "human_approval_required_for_real_merge": True,
            "auto_label_forbidden": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"strict_pairable_ready_after_simulation={strict_pairable_ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
