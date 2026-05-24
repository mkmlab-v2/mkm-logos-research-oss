#!/usr/bin/env python3
"""M27: Weekly smoke runner + optional Windows task registration readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_weekly_smoke_readiness_v1_latest.json"
TASK_NAME = "MKM_InterAgent_RQ019_Weekly_Smoke"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _windows_task_registered() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"registered": False, "platform": sys.platform, "note": "non_windows"}
    cp = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "registered": cp.returncode == 0,
        "exit_code": cp.returncode,
        "task_name": TASK_NAME,
    }


def build_readiness(*, require_task_registered: bool = False, run_regression: bool = True) -> dict[str, Any]:
    runner_ps1 = ROOT / "scripts" / "Run-MkmInterAgentRq019WeeklySmoke_v1.ps1"
    register_ps1 = ROOT / "scripts" / "Register-MkmInterAgentRq019WeeklySmokeTask.ps1"
    verify_ps1 = ROOT / "scripts" / "Verify-MkmInterAgentRq019WeeklyScheduledTask_v1.ps1"

    regression: dict[str, Any] = {"ok": True, "skipped": True}
    if run_regression:
        from scripts.run_mkm_inter_agent_rq019_regression_chain_v1 import run_chain

        regression = run_chain(skip_pytest=True, quick=True)

    task = _windows_task_registered()
    scripts_ok = runner_ps1.is_file() and register_ps1.is_file() and verify_ps1.is_file()

    status = {}
    status_path = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))

    task_ok = bool(task.get("registered")) if require_task_registered else True
    ok = scripts_ok and bool(regression.get("ok")) and task_ok

    return {
        "ok": ok,
        "schema": "mkm_inter_agent_rq019_weekly_smoke_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "runner_script": runner_ps1.relative_to(ROOT).as_posix(),
        "register_script": register_ps1.relative_to(ROOT).as_posix(),
        "verify_script": verify_ps1.relative_to(ROOT).as_posix(),
        "regression_chain": regression,
        "windows_scheduled_task": task,
        "require_task_registered": require_task_registered,
        "encoding_status_m26_ready": status.get("rq_019_language_dev_m26_ready"),
        "operator_hint": (
            "Register: powershell -File scripts/Register-MkmInterAgentRq019WeeklySmokeTask.ps1. "
            "Manual smoke: powershell -File scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1"
        ),
        "boundary_ack": "Weekly smoke is B-track observability only; not live trading or Track A promotion.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--require-task-registered", action="store_true")
    ap.add_argument("--skip-regression", action="store_true")
    args = ap.parse_args()
    doc = build_readiness(
        require_task_registered=args.require_task_registered,
        run_regression=not args.skip_regression,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
