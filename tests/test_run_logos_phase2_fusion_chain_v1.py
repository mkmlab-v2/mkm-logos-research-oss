"""Smoke: phase2 fusion chain dry-run and state summarizer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_phase2_fusion_chain_v1.py"


def test_phase2_fusion_dry_run_exit_zero():
    rc = subprocess.run(
        [sys.executable, str(CHAIN), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0
    assert "dry-run would run" in rc.stdout


def test_phase2_fusion_state_schema_fields():
    from scripts.run_logos_phase2_fusion_chain_v1 import _summarize_state

    state = _summarize_state()
    assert state.get("schema") == "logos_phase2_fusion_state_v1"
    assert state.get("hypothesis_tier") == "B"
    assert state.get("gating_status") == "NON_GATING"
