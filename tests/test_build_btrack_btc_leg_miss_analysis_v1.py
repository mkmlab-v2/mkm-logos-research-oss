"""Smoke test for build_btrack_btc_leg_miss_analysis_v1.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_btc_leg_miss_analysis_runs() -> None:
    script = ROOT / "scripts/build_btrack_btc_leg_miss_analysis_v1.py"
    cp = subprocess.run([sys.executable, str(script)], cwd=str(ROOT), check=False)
    assert cp.returncode == 0
    out = ROOT / "reports/btrack_btc_leg_miss_analysis_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_btc_leg_miss_analysis_v1"
    assert doc.get("summary", {}).get("n_evaluated", 0) >= 1
