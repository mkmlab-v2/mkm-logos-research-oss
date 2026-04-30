#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.8}
# Balance: 90
# Purpose: Read-only 24h health check for genius governance scheduler + core artifacts.
# Keywords: scheduler, health check, genius governance, artifacts, monitoring
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def query_task(task_name: str) -> dict[str, Any]:
    ps_script = (
        "$tn = "
        + json.dumps(task_name)
        + "; "
        + "$t = Get-ScheduledTask -TaskName $tn.TrimStart('\\') -ErrorAction Stop; "
        + "$i = Get-ScheduledTaskInfo -TaskName $tn.TrimStart('\\') -ErrorAction Stop; "
        + "[PSCustomObject]@{"
        + "State = $t.State.ToString(); "
        + "LastRunTime = $i.LastRunTime.ToString('o'); "
        + "LastTaskResult = $i.LastTaskResult "
        + "} | ConvertTo-Json -Compress"
    )
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    status = None
    last_run_time = None
    last_result = None
    if cp.returncode == 0 and cp.stdout.strip():
        try:
            obj = json.loads(cp.stdout.strip())
            if isinstance(obj, dict):
                status = obj.get("State")
                last_run_time = obj.get("LastRunTime")
                last_result = obj.get("LastTaskResult")
        except json.JSONDecodeError:
            pass

    healthy = cp.returncode == 0 and last_result is not None and int(last_result) == 0
    return {
        "task_name": task_name,
        "query_exit_code": cp.returncode,
        "status": status,
        "last_run_time": last_run_time,
        "last_result": int(last_result) if last_result is not None else None,
        "healthy": healthy,
    }


def artifact_health(path: Path, max_age_hours: float) -> dict[str, Any]:
    obj = read_json(path)
    generated_at = str(obj.get("generated_at_utc") or "")
    age_hours = None
    fresh = False
    if generated_at:
        dt = parse_utc(generated_at)
        if dt is not None:
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
            fresh = age_hours <= max_age_hours
    status_value = obj.get("status")
    return {
        "path": str(path).replace("\\", "/"),
        "exists": path.is_file(),
        "generated_at_utc": generated_at or None,
        "age_hours": round(age_hours, 3) if age_hours is not None else None,
        "fresh": fresh,
        "status": status_value,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 24h scheduler/artifact health snapshot for genius governance.")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/genius_governance_scheduler_health_check_latest.json",
    )
    ap.add_argument("--max-artifact-age-hours", type=float, default=26.0)
    args = ap.parse_args()

    tasks = [
        r"\MKM_GeniusReasoning_MonthlyRefresh",
        r"\MKM_GeniusDispatch_Chaos_MonthlyDrill",
        r"\MKM_GeniusHumanReview_HoldRehearsal_Monthly",
    ]

    task_rows = [query_task(name) for name in tasks]
    suite_path = resolve("docs/final/artifacts/genius_governance_monthly_suite_status_latest.json")
    dashboard_path = resolve("docs/final/artifacts/cursor_ai_unified_status_dashboard_latest.json")
    suite = artifact_health(suite_path, float(args.max_artifact_age_hours))
    dashboard = artifact_health(dashboard_path, float(args.max_artifact_age_hours))

    suite_doc = read_json(suite_path)
    dashboard_doc = read_json(dashboard_path)
    suite_pass = str(suite_doc.get("status", "")).upper() == "PASS"
    dashboard_go = str(dashboard_doc.get("status", "")).upper() == "GO"
    tasks_ok = all(bool(r.get("healthy")) for r in task_rows)

    out = {
        "schema": "genius_governance_scheduler_health_check_v1",
        "generated_at_utc": now_utc(),
        "inputs": {
            "tasks": tasks,
            "max_artifact_age_hours": float(args.max_artifact_age_hours),
        },
        "tasks": task_rows,
        "artifacts": {
            "monthly_suite": suite,
            "unified_dashboard": dashboard,
        },
        "summary": {
            "tasks_ok": tasks_ok,
            "monthly_suite_pass": suite_pass,
            "unified_dashboard_go": dashboard_go,
        },
        "status": "PASS" if (tasks_ok and suite_pass and dashboard_go and suite.get("fresh") and dashboard.get("fresh")) else "HOLD",
    }

    out_path = resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(out_path).replace("\\", "/"), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
