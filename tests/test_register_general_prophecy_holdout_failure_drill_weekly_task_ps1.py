from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_general_prophecy_holdout_failure_drill_weekly_task_whatif():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "Register-GeneralProphecyHoldoutFailureDrillWeeklyTask.ps1"
    cp = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-WorkspaceRoot",
            str(root),
            "-TaskName",
            "GeneralProphecyHoldoutFailureDrillWeeklyV1",
            "-Day",
            "SUN",
            "-At",
            "08:30",
            "-WhatIf",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = cp.stdout
    assert "schtasks.exe /Create" in out
    assert "/SC WEEKLY" in out
    assert "/D SUN" in out
    assert "run_general_prophecy_holdout_failure_drill_v1.py" in out
