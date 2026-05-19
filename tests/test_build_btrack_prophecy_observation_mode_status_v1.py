"""Observation mode status builder smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_observation_mode_status() -> None:
    out = ROOT / "reports" / "_tmp_obs_mode_status_test.json"
    r = subprocess.run(
        [sys.executable, "scripts/build_btrack_prophecy_observation_mode_status_v1.py", "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_prophecy_observation_mode_status_v1"
    assert doc["mode"] == "observation_ops_b"
    assert doc["ensemble_frozen"]["auto_promote"] is False
    assert len(doc.get("operator_lines") or []) >= 2
    out.unlink(missing_ok=True)
