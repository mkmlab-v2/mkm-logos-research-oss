# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_fabba_backend_ab_dual_leg_smoke(tmp_path: Path) -> None:
    kospi = ROOT / "research/market_data/kospi_daily_external_yf.csv"
    btc = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not kospi.is_file() or not btc.is_file():
        pytest.skip("market csv missing")
    out = tmp_path / "fabba_ab.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_prophecy_fabba_backend_ab_dual_leg_v1.py"),
            "--last-n-intersection",
            "60",
            "--n-folds",
            "4",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_backend_ab_dual_leg_v1"
    assert doc["fabba_native_available"] is False
    assert doc["compare"]["wf_results_identical_fallback"] is True
