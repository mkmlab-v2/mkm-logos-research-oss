from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_canon_singularity_strict_freeze_drift_task_ps1_print_only():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "register_canon_singularity_strict_freeze_drift_task.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PrintOnly",
        "-DailyAt",
        "07:10",
        "-AppendHistory",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    out = cp.stdout
    assert "PrintOnly: no task registration performed." in out
    assert "TaskName: MKM_CanonSingularity_StrictFreezeDrift" in out
    assert "AppendHistory: True" in out
    assert "--freeze-vfinal-json docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json" in out
    assert "--append-history" in out

