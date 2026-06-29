"""Post-Phase3 OL bridge closure smoke (deck MD + optional PDF)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_ol_graph_bridge_post_phase3_closure_v1.py"
REPORT = ROOT / "reports/logos_ol_graph_bridge_post_phase3_closure_v1_latest.json"
DECK_MD = ROOT / "reports/logos_ops_deck/logos_ol_bridge_deck_v1.md"


def test_logos_ol_graph_bridge_post_phase3_closure_smoke():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-pytest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc.get("phase3_complete") is True
    assert doc.get("human_signoff_required") is True
    deck = DECK_MD.read_text(encoding="utf-8")
    assert "NON_GATING" in deck
    assert "`True`" in deck or "True" in deck
