"""Oracle module vs HD-AE scheduler coexistence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_oracle_module_scheduler_coexistence_v1_latest.json"
STACK = ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json"


def test_oracle_module_task_in_tier4_ssot() -> None:
    stack = json.loads(STACK.read_text(encoding="utf-8-sig"))
    tier4 = stack.get("tier4_solo_intentional_keep") or []
    assert "\\MKM_Oracle_Module_Observability_Weekly" in tier4
    assert "\\MKM_HdAutonomousEvolution_Weekly" in tier4


@pytest.fixture(scope="module")
def coexistence_report() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_mkm_oracle_module_scheduler_coexistence_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_coexistence_ok(coexistence_report: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["coexistence_ok"] is True
    times = {t["default_sunday_local"] for t in doc.get("tasks") or []}
    assert len(times) == 2
