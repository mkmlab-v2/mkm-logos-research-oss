#!/usr/bin/env python3
"""Mark a todo_queue_v1 task as HITL-approved (idempotent). Use --batch-approve for all awaiting / pending HITL rows."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _workspace_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def _approval_required(task: dict) -> bool:
    if task.get("sensitivity_level") == "high":
        return True
    appr = task.get("approval") or {}
    return appr.get("required") is True


def _approve_task_inplace(task: dict, ts: str) -> bool:
    """Return True if task was updated (not already approved)."""
    tid = task.get("task_id", "")
    appr = task.setdefault("approval", {})
    appr.setdefault("idempotency_key", f"{tid}-v1")
    appr["required"] = appr.get("required", True)
    if appr.get("resolution") == "approved":
        return False
    appr["resolution"] = "approved"
    appr["resolved_at_utc"] = ts
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    ap.add_argument(
        "--queue",
        type=Path,
        default=None,
        help="Queue JSON path (default: docs/final/artifacts/todo_queue_latest.json)",
    )
    ap.add_argument("--task-id", default=None, help="Single task_id to approve")
    ap.add_argument(
        "--batch-approve",
        action="store_true",
        help="Approve every task in awaiting_approval or pending that still needs HITL (same rules as poll)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if bool(args.task_id) == bool(args.batch_approve):
        print("ERROR: specify exactly one of --task-id or --batch-approve", file=sys.stderr)
        return 2

    root = _workspace_root(args.workspace_root)
    queue_path = args.queue
    if queue_path is None:
        queue_path = root / "docs" / "final" / "artifacts" / "todo_queue_latest.json"
    else:
        queue_path = queue_path.resolve()

    if not queue_path.is_file():
        print(f"ERROR: queue file not found: {queue_path}", file=sys.stderr)
        return 1

    text = queue_path.read_text(encoding="utf-8")
    data = json.loads(text)
    if data.get("schema_version") != "todo_queue_v1":
        print("ERROR: schema_version must be todo_queue_v1", file=sys.stderr)
        return 1

    tasks = data.get("tasks") or []

    if args.batch_approve:
        targets: list[dict] = []
        for t in tasks:
            st = t.get("state", "")
            appr = t.get("approval") or {}
            if appr.get("resolution") == "approved":
                continue
            if st == "awaiting_approval":
                targets.append(t)
            elif st == "pending" and _approval_required(t):
                targets.append(t)

        if not targets:
            print("OK: no tasks pending HITL approval")
            return 0

        if args.dry_run:
            print(
                json.dumps(
                    {"would_approve_task_ids": [t.get("task_id") for t in targets]},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        ts = _utc_now()
        updated: list[str] = []
        for t in targets:
            tid = t.get("task_id", "")
            if _approve_task_inplace(t, ts):
                updated.append(str(tid))

        data["generated_at_utc"] = ts

        queue_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"OK: batch-approved {len(updated)} task(s) -> {queue_path}: {', '.join(updated)}")
        return 0

    hit = None
    for t in tasks:
        if t.get("task_id") == args.task_id:
            hit = t
            break
    if hit is None:
        print(f"ERROR: task_id not found: {args.task_id}", file=sys.stderr)
        return 1

    appr = hit.setdefault("approval", {})
    key = appr.get("idempotency_key") or f"{args.task_id}-v1"
    appr["idempotency_key"] = key
    appr["required"] = appr.get("required", True)
    if appr.get("resolution") == "approved":
        print(f"OK: already approved (idempotent): {args.task_id}")
        return 0

    ts = _utc_now()
    appr["resolution"] = "approved"
    appr["resolved_at_utc"] = ts

    data["generated_at_utc"] = ts

    if args.dry_run:
        print(json.dumps(hit, indent=2, ensure_ascii=False))
        return 0

    queue_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: approved task {args.task_id} -> {queue_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
