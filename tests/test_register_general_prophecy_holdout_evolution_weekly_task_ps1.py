from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "Register-GeneralProphecyHoldoutEvolutionWeeklyTask.ps1"


def test_register_holdout_evolution_weekly_task_whatif():
    cp = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-WorkspaceRoot",
            str(ROOT),
            "-WhatIf",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    text = (cp.stdout or "") + (cp.stderr or "")
    assert "GeneralProphecyHoldoutEvolutionWeeklyV1" in text
    assert "run_general_prophecy_daily_queue_refresh_v1.ps1" in text
    assert "HoldoutGateProfile ops" in text
