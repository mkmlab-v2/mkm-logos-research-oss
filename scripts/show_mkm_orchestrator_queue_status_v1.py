#!/usr/bin/env python3
"""Print human-readable todo_queue + HITL backlog summary (no secrets, no network)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def _needs_hitl_rule(task: dict) -> bool:
    if task.get("sensitivity_level") == "high":
        return True
    appr = task.get("approval") or {}
    return appr.get("required") is True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    ap.add_argument(
        "--queue",
        type=Path,
        default=None,
        help="Queue JSON (default: docs/final/artifacts/todo_queue_latest.json)",
    )
    args = ap.parse_args()

    root = _root(args.workspace_root)
    queue_path = args.queue
    if queue_path is None:
        queue_path = root / "docs" / "final" / "artifacts" / "todo_queue_latest.json"
    else:
        queue_path = queue_path.resolve()

    print(f"queue_path: {queue_path}")
    if not queue_path.is_file():
        print("status: MISSING (run bootstrap or apply_trackc_plan_bridge_to_queue_v1.py)")
        return 1

    data = json.loads(queue_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "todo_queue_v1":
        print("ERROR: schema_version must be todo_queue_v1", file=sys.stderr)
        return 1

    tasks = data.get("tasks") or []
    print(f"tasks: {len(tasks)}  generated_at_utc: {data.get('generated_at_utc', '')}")
    print()
    print(f"{'task_id':<28} {'state':<18} {'sens':<6} {'app_req':<8} {'resolution':<12} hitl_rule")
    print("-" * 96)
    batch_eligible = 0
    for t in tasks:
        tid = str(t.get("task_id", ""))[:26]
        st = str(t.get("state", ""))[:16]
        sens = str(t.get("sensitivity_level", ""))[:4]
        appr = t.get("approval") or {}
        req = str(appr.get("required", False))[:6]
        res = str(appr.get("resolution", ""))[:10]
        rule = _needs_hitl_rule(t)
        hitl = "yes" if rule else "no"
        print(f"{tid:<28} {st:<18} {sens:<6} {req:<8} {res:<12} {hitl}")
        st_full = t.get("state", "")
        if appr.get("resolution") == "approved":
            continue
        if st_full == "awaiting_approval" or (st_full == "pending" and rule):
            batch_eligible += 1

    print("-" * 96)
    print(
        f"batch-approve would touch: {batch_eligible} task(s) "
        f"(awaiting_approval, or pending+hitl_rule; not already approved)"
    )
    print()

    backlog = root / "reports" / "mkm_orchestrator_approval_backlog_latest.json"
    print(f"backlog_snapshot: {backlog}")
    if not backlog.is_file():
        print("  (file absent — run mkm_orchestrator_poll_v1.py once to generate)")
    else:
        b = json.loads(backlog.read_text(encoding="utf-8"))
        pend = b.get("pending_approval") or []
        print(f"  pending_approval rows: {len(pend)}")
        for row in pend[:12]:
            print(f"    - {row.get('task_id')}  {row.get('state')}")
        if len(pend) > 12:
            print(f"    ... +{len(pend) - 12} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
