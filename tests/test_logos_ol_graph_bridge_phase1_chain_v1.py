"""Logos OL GraphRAG bridge Phase 1 chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_ol_graph_bridge_phase1_chain_v1.py"
REPORT = ROOT / "reports/logos_ol_graph_bridge_phase1_chain_v1_latest.json"


def test_logos_ol_graph_bridge_phase1_chain_smoke():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-phase0-parallel"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc.get("lemma_edge_count", 0) >= 10
    assert doc.get("corpus_split_gate_pass") is True
