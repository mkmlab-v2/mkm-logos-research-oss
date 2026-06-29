"""Public-facing engineering scan smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts/check_agent_handoff_governance_public_facing_scan_v1.py"


def test_public_facing_scan_passes():
    r = subprocess.run(
        [sys.executable, str(SCAN)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    out = ROOT / "reports/agent_handoff_governance_public_facing_scan_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["engineering_cross_check_pass"] is True
    assert doc["ready_for_external_send"] is False
    assert doc["legal_review_status"] == "PENDING"
