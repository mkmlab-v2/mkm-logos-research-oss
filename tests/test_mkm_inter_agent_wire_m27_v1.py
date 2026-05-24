"""M27: Weekly smoke runner readiness + Track C dashboard MD inter-agent section."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_weekly_smoke_readiness():
    from scripts.build_mkm_inter_agent_rq019_weekly_smoke_readiness_v1 import build_readiness

    doc = build_readiness(require_task_registered=False, run_regression=True)
    assert doc.get("ok")
    assert (ROOT / doc["runner_script"]).is_file()


def test_trackc_dashboard_md_inter_agent_section():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    md = (ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md").read_text(encoding="utf-8")
    assert "## Inter-agent RQ-019 (B-track research)" in md
    assert "language_dev_m12_m25_ready" in md


def test_weekly_smoke_scripts_exist():
    for name in (
        "Run-MkmInterAgentRq019WeeklySmoke_v1.ps1",
        "Register-MkmInterAgentRq019WeeklySmokeTask.ps1",
        "Verify-MkmInterAgentRq019WeeklyScheduledTask_v1.ps1",
    ):
        assert (ROOT / "scripts" / name).is_file()
