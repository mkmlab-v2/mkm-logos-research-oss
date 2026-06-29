"""Showroom v6 subgraph audit panel builder + gate smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_showroom_v6_subgraph_audit_panel_v1.py"
CHECKER = ROOT / "scripts/check_logos_showroom_v6_subgraph_audit_panel_v1.py"
PANEL = ROOT / "reports/logos_showroom_v6_subgraph_audit_panel_v1_latest.json"


def test_build_and_gate_showroom_v6_audit_panel():
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(PANEL.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_showroom_v6_subgraph_audit_panel_v1"
    assert doc["non_gating"] is True
    assert doc["wire_audit_panel"]["wire_audit_ui_present"] is True
    assert doc["wire_audit_panel"]["subgraph_audit_ui_present"] is True

    proc2 = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc2.returncode == 0, proc2.stderr or proc.stdout
