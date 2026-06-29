"""Phase 3 OL graph bridge chain smoke (subgraph audit panel)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_ol_graph_bridge_phase3_chain_v1.py"
REPORT = ROOT / "reports/logos_ol_graph_bridge_phase3_chain_v1_latest.json"
ALIGNMENT = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"
SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_subgraph_audit_slice_v1.json"
)


def test_logos_ol_graph_bridge_phase3_chain_smoke():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-pytest", "--skip-replay-batch"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc.get("showroom_audit_slice_gate_pass") is True
    assert doc.get("showroom_audit_panel_gate_pass") is True
    assert doc.get("phase3_complete") is True
    alignment = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    assert alignment.get("phase3_complete") is True
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert slice_doc["paths_public"]
    assert "subgraph router showroom audit panel (Phase 3)" not in (alignment.get("phase_gaps") or [])
