"""4-axis promotion gate policy validation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py"
POLICY = ROOT / "docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1.md"
OUT = ROOT / "docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1_latest.json"


def test_validate_multi_axis_promotion_gate_policy_exit0():
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert POLICY.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["promotion_cascade_forbidden"] is True
    assert doc["send_gate"] == "HOLD"
    assert len(doc["axes"]) == 5
