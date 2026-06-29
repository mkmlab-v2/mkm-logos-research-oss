"""Smoke test for continuous calibration sweep."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_continuous_calibration_sweep_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_btc_continuous_calibration_sweep_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    doc = json.loads((ROOT / "reports/btrack_btc_continuous_calibration_sweep_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_continuous_calibration_sweep_v1"
    assert len(doc.get("top_candidates") or []) >= 1
