from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_canon_singularity_observation_streak_task_ps1_print_only():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_observation_streak_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-DailyAt",
        "07:25",
        "-Window",
        "3",
        "-MinPassCount",
        "3",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "PrintOnly: no task registration performed." in out
    assert "TaskName: MKM_CanonSingularity_ObservationStreak" in out
    assert "DailyAt: 07:25" in out
    assert "--window 3" in out
    assert "--min-pass-count 3" in out

