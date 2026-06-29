"""Oracle module weekly observability routine smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1"
REPORT = ROOT / "reports/mkm_oracle_module_observability_weekly_v1_latest.json"
RESUME = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"


def test_weekly_runner_exists() -> None:
    assert RUNNER.is_file()


@pytest.fixture(scope="module")
def weekly_run() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_weekly_report(weekly_run: None) -> None:
    doc = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert doc.get("chain_pass") is True
    assert doc.get("send_gate") == "HOLD"


def test_oracle_resume_pack_module_lane(weekly_run: None) -> None:
    doc = json.loads(RESUME.read_text(encoding="utf-8-sig"))
    lane = doc.get("oracle_module_lane") or {}
    assert lane.get("tier2_prep_ready") is True
    assert lane.get("cursor_rule") == ".cursor/rules/logos-oracle-module-tier2-prep-v1.mdc"
    assert "prism_ops_logos_oracle_module_tier2_prep" in {
        p.get("node_id") for p in doc.get("ops_memory_pins") or []
    }
