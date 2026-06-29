"""Smoke test for BTC direction-error spike."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_direction_error_spike() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_btc_direction_error_spike_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    doc = json.loads((ROOT / "reports/btrack_btc_direction_error_spike_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_direction_error_spike_v1"
    assert doc["n_type_a_miss_days"] >= 1
