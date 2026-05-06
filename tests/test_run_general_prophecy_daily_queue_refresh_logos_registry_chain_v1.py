from __future__ import annotations

import subprocess
from pathlib import Path


def test_daily_queue_script_declares_registry_outputs_in_retry_chain() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_general_prophecy_daily_queue_refresh_v1.ps1"
    body = script.read_text(encoding="utf-8")
    assert "Invoke-Step \"build_logos_63779_registry_v1\"" in body
    assert "Invoke-Step \"build_logos_morphology_registry_v1\"" in body
    assert "logos_63779_registry_v1_latest.json" in body
    assert "logos_morphology_registry_v1_latest.json" in body


def test_daily_queue_smoke_runs_retry_with_registry_builders_enabled() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_general_prophecy_daily_queue_refresh_v1.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(root),
        "-HoldoutGateProfile",
        "ops",
        "-IncludeLogosV2",
        "true",
        "-EnableLogosResponseV1Retry",
        "true",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = cp.stdout
    assert "logos_63779_registry_v1_latest.json" in out
    assert "logos_morphology_registry_v1_latest.json" in out
