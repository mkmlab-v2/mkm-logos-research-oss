"""Smoke tests for Charter R4 monthly KOSPI lens ablation WF refresh."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_monthly_wf_refresh_dry_run(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "refresh.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_kospi_lens_ablation_monthly_wf_refresh_v1.py"),
            "--dry-run",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_lens_ablation_monthly_wf_refresh_v1"
    assert doc["charter_ref"] == "LENS_UTILIZATION_CHARTER_V1 R4"
    assert doc["dry_run"] is True
    assert doc["auto_promote"] is False
    assert doc["research_only"] is True


def test_register_scripts_exist():
    assert (ROOT / "scripts/Register-KospiLensAblationMonthlyWfRefreshTask.ps1").is_file()
    assert (ROOT / "scripts/Run-KospiLensAblationMonthlyWfRefresh_v1.ps1").is_file()
    assert (ROOT / "scripts/Invoke-KospiLensAblationWalkforward_v1.ps1").is_file()
