"""Phase 1A baseline vs dual-plane comparison smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "scripts/build_universal_root_phase1a_baseline_compare_v1.py"
CHECKER = REPO / "scripts/check_universal_root_phase1a_baseline_compare_v1.py"
ART = REPO / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"


def test_phase1a_build_and_gate():
    r = subprocess.run([sys.executable, str(BUILDER)], cwd=str(REPO), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    doc = json.loads(ART.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "universal_root_phase1a_baseline_compare_v1"
    assert doc["pair_count"] == 500
    ids = {m["id"] for m in doc["methods"]}
    assert ids == {"B0", "B1", "B2", "B3", "B4"}
    b4 = next(m for m in doc["methods"] if m["id"] == "B4")
    assert b4["forbidden_headline"] is True

    g = subprocess.run([sys.executable, str(CHECKER), "--strict"], cwd=str(REPO), capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
