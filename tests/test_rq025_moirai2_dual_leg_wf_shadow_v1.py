# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_moirai_dual_leg_smoke_without_inference(tmp_path: Path) -> None:
    kospi = ROOT / "research/market_data/kospi_daily_external_yf.csv"
    btc = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not kospi.is_file() or not btc.is_file():
        pytest.skip("market csv missing")
    out = tmp_path / "moirai_dual.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_rq025_moirai2_dual_leg_wf_shadow_v1.py"),
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
    assert doc["schema"] == "rq025_moirai2_dual_leg_wf_shadow_v1"
    assert doc["send_gate"] == "HOLD"
    pooled = {a["arm_id"]: a for a in doc["dual_leg_pooled_arms"]}
    assert pooled["mom_20d"]["total_n_evaluated"] >= 1
