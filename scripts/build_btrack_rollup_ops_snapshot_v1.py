#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def task_query(task_name: str) -> dict[str, Any]:
    cmd = ["schtasks", "/Query", "/TN", f"\\{task_name}", "/V", "/FO", "LIST"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = (proc.stdout or "").splitlines()
    kv: dict[str, str] = {}
    for line in body:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        kv[k.strip()] = v.strip()
    return {
        "task_name": task_name,
        "exists": proc.returncode == 0,
        "return_code": proc.returncode,
        "status": kv.get("Status"),
        "next_run_time": kv.get("Next Run Time"),
        "last_result": kv.get("Last Result"),
        "task_to_run": kv.get("Task To Run"),
        "schedule_type": kv.get("Schedule Type"),
        "schedule_months": kv.get("Months"),
        "schedule_days": kv.get("Days"),
        "start_time": kv.get("Start Time"),
    }


def artifact_entry(path: Path) -> dict[str, Any]:
    doc = read_json(path)
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "generated_at_utc": (doc or {}).get("generated_at_utc"),
    }


def task_ready(task: dict[str, Any]) -> bool:
    return bool(task.get("exists")) and str(task.get("status") or "").lower() == "ready"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build B-track rollup operations snapshot.")
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/btrack_rollup_ops_snapshot_latest.json",
        help="Output JSON path",
    )
    ap.add_argument("--default-task-name", default="MKM_BTrack99_Weekly_Rollup")
    ap.add_argument("--extended-task-name", default="MKM_BTrack99_Weekly_Rollup_Extended")
    args = ap.parse_args()

    out_path = (ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = {
        "weekly_gate": ART / "trackb_weekly_gate_recheck_latest.json",
        "promotion_precheck": ART / "trackb_promotion_precheck_draft_latest.json",
        "compression_leaderboard": ART / "btrack_compression_leaderboard_latest.json",
        "weekly_consolidation": ART / "btrack_weekly_consolidation_latest.json",
    }
    artifacts = {k: artifact_entry(v) for k, v in files.items()}

    default_task = task_query(args.default_task_name)
    extended_task = task_query(args.extended_task_name)

    payload: dict[str, Any] = {
        "schema": "btrack_rollup_ops_snapshot_v1",
        "generated_at_utc": utc_now_iso(),
        "artifacts": artifacts,
        "tasks": {
            "default_rollup": default_task,
            "extended_rollup": extended_task,
        },
    }

    all_artifacts_exist = all(v["exists"] for v in artifacts.values())
    all_tasks_registered = bool(default_task["exists"] and extended_task["exists"])
    payload["summary"] = {
        "all_artifacts_exist": all_artifacts_exist,
        "all_tasks_registered": all_tasks_registered,
        "default_task_ready": task_ready(default_task),
        "extended_task_ready": task_ready(extended_task),
        "ops_watch_ok": all_artifacts_exist and all_tasks_registered and task_ready(default_task),
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

