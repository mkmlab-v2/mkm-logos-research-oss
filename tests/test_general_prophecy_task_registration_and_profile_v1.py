from __future__ import annotations

import subprocess
from pathlib import Path


def test_register_general_prophecy_task_whatif_includes_ops_profile():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "Register-GeneralProphecyDailyQueueTask.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(root),
        "-TaskName",
        "GeneralProphecyDailyQueueV1",
        "-DailyAt",
        "09:00",
        "-HoldoutGateProfile",
        "ops",
        "-WhatIf",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = cp.stdout
    assert "run_general_prophecy_daily_queue_refresh_v1.ps1" in out
    assert "-HoldoutGateProfile ops" in out


def test_general_prophecy_daily_queue_refresh_exposes_holdout_profile_param():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_general_prophecy_daily_queue_refresh_v1.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Get-Command -Name '{script}' -Syntax",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert "HoldoutGateProfile" in cp.stdout


def test_general_prophecy_daily_queue_refresh_wires_logos_registry_builders():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_general_prophecy_daily_queue_refresh_v1.ps1"
    body = script.read_text(encoding="utf-8")
    assert "build_logos_63779_registry_v1.py" in body
    assert "build_logos_morphology_registry_v1.py" in body
    assert "Invoke-Step \"build_logos_63779_registry_v1\"" in body
    assert "Invoke-Step \"build_logos_morphology_registry_v1\"" in body
