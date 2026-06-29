"""Smoke test for KOSPI-strong BTC neutral cap spike."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spike_runs_and_schema() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_btc_kospi_strong_neutral_cap_spike_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    out = ROOT / "reports/btrack_btc_kospi_strong_neutral_cap_spike_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_kospi_strong_neutral_cap_spike_v1"
    assert doc["research_only"] is True
    assert "baseline_btc" in doc and "counterfactual_btc" in doc
