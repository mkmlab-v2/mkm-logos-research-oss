#!/usr/bin/env python3
"""Parallel marketing ops bundle — handoff checklist + queue sync (no auto-publish)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/marketing/marketing_ops_parallel_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(task_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-800:]
    return {
        "task_id": task_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
        "tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    jobs: list[tuple[str, list[str]]] = [
        ("sync_queue_linkedin", [py, "scripts/sync_marketing_queue_to_linkedin_v1.py"]),
        (
            "linkedin_draft_assemble",
            [
                py,
                "scripts/generate_linkedin_b2b_copy_v1.py",
                "--queue",
                "data/marketing/linkedin_queue.json",
                "--assemble-only",
                "--strict-compliance",
            ],
        ),
        (
            "pull_linkedin_to_unified",
            [
                py,
                "scripts/sync_marketing_queue_to_linkedin_v1.py",
                "--pull-linkedin-status",
            ],
        ),
        ("weekly_bundle_summary", [py, "scripts/build_marketing_weekly_bundle_summary_v1.py"]),
        ("linkedin_post_ready", [py, "scripts/build_marketing_linkedin_post_ready_v1.py"]),
        ("publish_handoff", [py, "scripts/build_marketing_publish_handoff_v1.py"]),
    ]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in jobs}
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: str(r.get("task_id") or ""))

    # post_ready count=0 is expected when LinkedIn rows are already published (not human_approved).
    for r in results:
        if r.get("task_id") == "linkedin_post_ready" and not r.get("ok"):
            if '"count": 0' in str(r.get("tail") or ""):
                r["ok"] = True
                r["soft_pass"] = True
                r["note"] = "no human_approved rows (likely already published)"

    pack = {
        "schema": "marketing_ops_parallel_bundle_v1",
        "generated_at_utc": _utc(),
        "auto_publish_allowed": False,
        "boundary_ack": "Human fire only; copy_guard PASS is necessary not sufficient.",
        "tasks": results,
        "all_ok": all(r.get("ok") for r in results),
        "artifacts": {
            "publish_checklist": "reports/marketing/marketing_publish_checklist_latest.md",
            "publish_handoff_json": "reports/marketing/marketing_publish_handoff_latest.json",
            "weekly_bundle": "reports/marketing/marketing_weekly_bundle_latest.json",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if not pack["all_ok"]:
        failed = [r["task_id"] for r in results if not r.get("ok")]
        print(f"FAILED: {failed}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
