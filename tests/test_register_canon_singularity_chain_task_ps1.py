from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_canon_singularity_chain_task_ps1_print_only():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_chain_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-HealthProfile",
        "balanced",
        "-DailyAt",
        "06:40",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "PrintOnly: no task registration performed." in out
    assert "HealthProfile: balanced" in out
    assert "-HealthMaxFailCount 1" in out
    assert "-HealthMinPassRate 0.9" in out
    assert "-HealthAllowYellow" in out

