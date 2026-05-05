#!/usr/bin/env python3
"""Build or merge Track C bridge tasks into todo_queue_v1 (default: todo_queue_latest.json)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _bridge_tasks_to_queue_tasks(tasks_in: list[dict]) -> list[dict]:
    tasks_out: list[dict] = []
    for t in tasks_in:
        base = {k: v for k, v in t.items() if k in ("plan_ref", "plan_note")}
        rest = {k: v for k, v in t.items() if k not in ("plan_ref", "plan_note")}
        desc_parts = []
        if base.get("plan_ref"):
            desc_parts.append(f"Plan: {base['plan_ref']}")
        if base.get("plan_note"):
            desc_parts.append(base["plan_note"])
        if desc_parts:
            rest.setdefault("description", " | ".join(desc_parts))
        tasks_out.append(rest)
    return tasks_out


def _merge_tasks_preserving_state(existing: list[dict], incoming: list[dict], ts: str) -> list[dict]:
    """Merge by task_id while preserving execution lifecycle fields from existing queue."""
    existing_by_id = {str(t.get("task_id", "")): t for t in existing if t.get("task_id")}
    merged: list[dict] = []
    seen: set[str] = set()

    for item in incoming:
        tid = str(item.get("task_id", ""))
        if not tid:
            continue
        prior = existing_by_id.get(tid)
        if prior is None:
            merged.append(item)
            seen.add(tid)
            continue

        keep = dict(item)
        # Preserve execution state/history from existing queue.
        for field in ("state", "approval", "last_run", "created_at_utc", "updated_at_utc"):
            if field in prior:
                keep[field] = prior[field]
        # Recurring cadence: re-arm done tasks when due.
        cadence = int(keep.get("cadence_seconds") or 0)
        prior_state = str(prior.get("state", ""))
        if cadence > 0 and prior_state == "done":
            now_dt = _parse_utc(ts)
            done_dt = _parse_utc(((prior.get("last_run") or {}).get("finished_at_utc")))
            if now_dt is not None and done_dt is not None:
                if (now_dt - done_dt).total_seconds() >= cadence:
                    keep["state"] = "pending"
                    keep["updated_at_utc"] = ts
                    # Clear last_run so next execution writes fresh lifecycle.
                    keep.pop("last_run", None)
            keep.setdefault("updated_at_utc", ts)
        else:
            keep.setdefault("updated_at_utc", ts)
        merged.append(keep)
        seen.add(tid)

    # Keep non-bridge tasks (manual injections, ad-hoc ops tasks) untouched.
    for item in existing:
        tid = str(item.get("task_id", ""))
        if not tid or tid in seen:
            continue
        merged.append(item)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    ap.add_argument(
        "--bridge",
        type=Path,
        default=None,
        help="Bridge JSON (default: docs/final/artifacts/mkm_trackc_plan_orchestrator_bridge_v1.json)",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output todo_queue_v1 path (default: docs/final/artifacts/todo_queue_latest.json)",
    )
    ap.add_argument(
        "--merge-existing",
        action="store_true",
        help="Merge by task_id with existing queue and preserve task states/history.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve() if args.workspace_root else Path(__file__).resolve().parents[1]
    bridge_path = args.bridge or (
        root / "docs" / "final" / "artifacts" / "mkm_trackc_plan_orchestrator_bridge_v1.json"
    )
    out_path = args.output or (root / "docs" / "final" / "artifacts" / "todo_queue_latest.json")

    if not bridge_path.is_file():
        print(f"ERROR: bridge not found: {bridge_path}", file=__import__("sys").stderr)
        return 1

    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    if bridge.get("schema_version") != "mkm_trackc_plan_orchestrator_bridge_v1":
        print("ERROR: bridge schema_version mismatch", file=__import__("sys").stderr)
        return 1

    ts = _utc()
    tasks_in = bridge.get("tasks") or []
    tasks_out = _bridge_tasks_to_queue_tasks(tasks_in)

    if args.merge_existing and out_path.is_file():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if existing.get("schema_version") != "todo_queue_v1":
            print("ERROR: existing queue schema_version must be todo_queue_v1", file=__import__("sys").stderr)
            return 1
        tasks_out = _merge_tasks_preserving_state(existing.get("tasks") or [], tasks_out, ts)

    queue = {
        "schema_version": "todo_queue_v1",
        "generated_at_utc": ts,
        "workspace_root_hint": str(root),
        "notes": f"Generated from {bridge_path.name}; plan SSOT: {bridge.get('plan_ssot_rel', '')}",
        "tasks": tasks_out,
    }

    if args.dry_run:
        print(json.dumps(queue, indent=2, ensure_ascii=False))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    suffix = " [merge-existing]" if args.merge_existing else ""
    print(f"OK: wrote {out_path} ({len(tasks_out)} tasks){suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
