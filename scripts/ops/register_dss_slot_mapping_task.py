# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.5, L:0.9, K:0.8, M:0.8}
# Balance: 86
# Purpose: Register Windows scheduled task for DSS slot mapping refresh.
# Keywords: scheduler, windows, schtasks, dss, automation
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REFRESH = ROOT / "scripts" / "ops" / "run_dss_slot_mapping_refresh.py"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_scheduler_plan_latest.json"


def _build_create_cmd(*, task_name: str, schedule: str, time_str: str, python_exe: str) -> list[str]:
    run_cmd = f'"{python_exe}" "{REFRESH}" --confidence-mode v2'
    return [
        "schtasks",
        "/Create",
        "/F",
        "/TN",
        task_name,
        "/SC",
        schedule,
        "/ST",
        time_str,
        "/TR",
        run_cmd,
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Register DSS slot mapping refresh in Windows Task Scheduler.")
    ap.add_argument("--task-name", default="MKM12_DSS_Slot_Mapping_Refresh")
    ap.add_argument("--schedule", choices=("DAILY", "WEEKLY"), default="DAILY")
    ap.add_argument("--time", default="03:30")
    ap.add_argument("--python-exe", default=sys.executable)
    ap.add_argument("--apply", action="store_true", help="Actually create/update scheduled task")
    args = ap.parse_args()

    cmd = _build_create_cmd(
        task_name=args.task_name,
        schedule=args.schedule,
        time_str=args.time,
        python_exe=args.python_exe,
    )
    payload = {
        "schema": "btrack_dss_scheduler_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task_name": args.task_name,
        "schedule": args.schedule,
        "time": args.time,
        "python_exe": args.python_exe,
        "refresh_script": str(REFRESH),
        "planned_command": cmd,
        "applied": False,
        "planned_only": True,
    }

    if args.apply:
        if sys.platform != "win32":
            print("ERROR: --apply is supported on Windows only.")
            return 2
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr)
            return r.returncode
        payload["applied"] = True
        payload["planned_only"] = False
        payload["apply_stdout"] = r.stdout.strip()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print("PLANNED COMMAND:")
    print(" ".join(cmd))
    if args.apply:
        print("APPLY: task registered/updated")
    else:
        print("APPLY: skipped (run with --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
