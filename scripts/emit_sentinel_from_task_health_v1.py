#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
STATE_PATH = ART / "sentinel_task_health_state_latest.json"
PENDING_APPROVAL_PATH = ART / "inspector_pending_approval_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _run_powershell(script: str) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return (proc.stdout or "").strip()


def _task_result(task_name: str) -> int | None:
    out = _run_powershell(
        f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
        "if($i){ Write-Output $i.LastTaskResult }"
    )
    if not out:
        return None
    try:
        return int(out.splitlines()[-1].strip())
    except ValueError:
        return None


def _emit_sentinel(task_name: str, observed: int, threshold: int, level: str, severity: str) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_sentinel_realtime_v1.py"),
        "--severity",
        severity,
        "--category",
        "runtime",
        "--signal-key",
        f"task_failure:{task_name}",
        "--observed-value",
        str(observed),
        "--threshold",
        str(threshold),
        "--level",
        level,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return proc.returncode


def _notify_slack_if_needed(level: str) -> None:
    # Best-effort notification; never fail the sentinel emitter on webhook trouble.
    if str(level).strip().upper() != "L2":
        return
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "send_sentinel_realtime_alert_slack_v1.py"),
    ]
    try:
        subprocess.run(cmd, cwd=str(ROOT), check=False)
    except Exception:
        return


def _write_pending_approval(task_name: str, observed: int, threshold: int, level: str) -> None:
    requested_action_id = "retry_scheduled_task"
    if task_name == "MKM_Internal_Inspector_Daily":
        # For inspector self-health, request a non-destructive environment preview first.
        requested_action_id = "preview_python_cache_cleanup"

    payload = {
        "schema": "inspector_pending_approval_v1",
        "ts_utc": _now_iso(),
        "status": "pending_commander_approval",
        "requested_action": {
            "action_id": requested_action_id,
            "level": level,
            "task_name": task_name,
            "approval_required": True,
            "reason": f"failure_streak {observed} >= threshold {threshold}",
        },
        "approval_protocol": {
            "token_schema": "commander_approval_token_v1",
            "token_example_path": "docs/final/artifacts/approvals/approval_<correlation_id>.json",
        },
    }
    PENDING_APPROVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_APPROVAL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit sentinel runtime alerts from core task health.")
    ap.add_argument(
        "--tasks",
        nargs="+",
        default=["GeneralProphecyDailyQueueV1", "VibeDailyProphecyEvolutionLoop", "MKM_Internal_Inspector_Daily"],
    )
    ap.add_argument("--warn-failure-streak", type=int, default=1)
    ap.add_argument("--critical-failure-streak", type=int, default=3)
    ap.add_argument("--force-critical", action="store_true", help="Emit one synthetic L2 alert for smoke testing.")
    args = ap.parse_args()

    state = _read_json(STATE_PATH)
    prev = state.get("tasks") if isinstance(state.get("tasks"), dict) else {}

    out_state: dict[str, Any] = {"schema": "sentinel_task_health_state_v1", "ts_utc": _now_iso(), "tasks": {}}
    emitted = 0
    if args.force_critical:
        task = (args.tasks[0] if args.tasks else "GeneralProphecyDailyQueueV1")
        rc = _emit_sentinel(task, args.critical_failure_streak, args.critical_failure_streak, "L2", "high")
        if rc == 0:
            emitted += 1
            _write_pending_approval(task, args.critical_failure_streak, args.critical_failure_streak, "L2")
            _notify_slack_if_needed("L2")

    for task in args.tasks:
        last_result = _task_result(task)
        prev_row = prev.get(task) if isinstance(prev, dict) else {}
        prev_streak = int(prev_row.get("failure_streak") or 0) if isinstance(prev_row, dict) else 0
        if last_result is None:
            out_state["tasks"][task] = {"last_task_result": None, "failure_streak": prev_streak}
            continue
        failure_streak = prev_streak + 1 if last_result != 0 else 0
        out_state["tasks"][task] = {"last_task_result": last_result, "failure_streak": failure_streak}

        if failure_streak >= args.critical_failure_streak:
            rc = _emit_sentinel(task, failure_streak, args.critical_failure_streak, "L2", "high")
            if rc == 0:
                emitted += 1
                _write_pending_approval(task, failure_streak, args.critical_failure_streak, "L2")
                _notify_slack_if_needed("L2")
        elif failure_streak >= args.warn_failure_streak:
            rc = _emit_sentinel(task, failure_streak, args.warn_failure_streak, "L1", "medium")
            if rc == 0:
                emitted += 1

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(out_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {STATE_PATH}")
    print(f"sentinel_emitted_count: {emitted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

