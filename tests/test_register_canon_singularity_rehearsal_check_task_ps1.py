from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_canon_singularity_rehearsal_check_task_ps1_print_only():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_rehearsal_check_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-DailyAt",
        "06:50",
        "-AppendHistory",
        "-AutoRunStrictOnAlert",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "PrintOnly: no task registration performed." in out
    assert "TaskName: MKM_CanonSingularity_RehearsalCheck" in out
    assert "AppendHistory: True" in out
    assert "AutoRunStrictOnAlert: True" in out
    assert "-AppendHistory" in out
    assert "-AutoRunStrictOnAlert" in out


def test_register_canon_singularity_rehearsal_check_task_ps1_defaults_auto_enabled():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_rehearsal_check_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-DailyAt",
        "06:50",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "AppendHistory: True" in out
    assert "AutoRunStrictOnAlert: True" in out
    assert "-AppendHistory" in out
    assert "-AutoRunStrictOnAlert" in out

