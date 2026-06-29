"""Smoke tests for Agent Handoff Governance Phase 1 readiness check."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_agent_handoff_governance_phase1_readiness_v1.py"
BUILD = ROOT / "scripts/build_agent_handoff_governance_phase1_pack_v1.py"
KPI = ROOT / "docs/final/artifacts/agent_handoff_governance_pilot_kpi_v1_latest.json"


def test_build_and_readiness_exit_zero():
    r = subprocess.run([sys.executable, str(BUILD)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout
    r2 = subprocess.run([sys.executable, str(CHECK)], cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr or r2.stdout


def test_kpi_schema_field():
    doc = json.loads(KPI.read_text(encoding="utf-8"))
    assert doc["schema"] == "agent_handoff_governance_pilot_kpi_v1"
    assert doc["research_only"] is True
