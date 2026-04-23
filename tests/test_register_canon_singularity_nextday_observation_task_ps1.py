from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_canon_singularity_nextday_observation_task_ps1_print_only():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_nextday_observation_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-DailyAt",
        "07:20",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "PrintOnly: no task registration performed." in out
    assert "TaskName: MKM_CanonSingularity_NextdayObservation" in out
    assert "DailyAt: 07:20" in out
    assert "build_canon_singularity_nextday_observation_report_v1.py" in out

