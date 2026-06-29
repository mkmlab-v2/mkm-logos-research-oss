"""Logos OL GraphRAG bridge Phase 2 chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_ol_graph_bridge_phase2_chain_v1.py"
REPORT = ROOT / "reports/logos_ol_graph_bridge_phase2_chain_v1_latest.json"
GOVERNANCE = ROOT / "reports/logos_concept_bridge_governance_v1_latest.json"


def test_logos_ol_graph_bridge_phase2_chain_smoke():
    proc = subprocess.run(
        [sys.executable, str(CHAIN)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc.get("governance_gate_pass") is True
    assert float(doc.get("human_reviewed_ratio") or 0) >= 0.5
    assert int(doc.get("llm_bridge_count") or 0) >= 1
    gov = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    assert gov.get("gate_pass") is True
    assert gov.get("governance_warning_zero_human") is False
