"""run_multilens_p1_production_chain.py — plan/dry-run contract (no full P1 eval)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_multilens_p1_production_chain.py"


def test_json_plan_schema_and_step_count() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--json-plan"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["schema"] == "multilens_p1_chain_plan_v1"
    assert doc["track"] == "production"
    assert len(doc["steps"]) == 4
    assert doc["steps"][0]["id"] == "p1_ab_efficiency"
    assert doc["steps"][-1]["id"] == "p1_final_selection"


def test_json_plan_includes_compression_when_flagged() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--json-plan", "--include-compression-chain"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert len(doc["steps"]) == 5
    assert doc["steps"][-1]["id"] == "compression_automation_chain"


def test_dry_run_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "p1_ab_balanced" in r.stdout
