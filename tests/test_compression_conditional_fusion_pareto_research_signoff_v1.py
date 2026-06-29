"""Smoke tests for compression conditional fusion Pareto research signoff."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json"
BUILDER = ROOT / "scripts/build_compression_conditional_fusion_pareto_research_signoff_v1.py"


def test_build_pareto_research_signoff_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--human-approve-research", "--reviewer", "commander"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_conditional_fusion_pareto_research_signoff_v1"
    assert doc["research_only"] is True
    assert doc["apply_active_forbidden"] is True
    assert doc["beat_frozen"] is False
    assert doc["recommended_research_headline_arm"] == "conditional_v3_ssot_merged"
    assert doc["commander_research_approval"] is True
    assert "conditional_v3_ssot_merged" in doc["pareto_front_arm_ids"]


def test_phase6_chain_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_ng40_dr_phase6_stub_pareto_completion_chain_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    chain_path = ROOT / "reports/ng40_dr_phase6_stub_pareto_completion_chain_v1_latest.json"
    assert chain_path.is_file()
    doc = json.loads(chain_path.read_text(encoding="utf-8"))
    assert doc["chain_ok"] is True
