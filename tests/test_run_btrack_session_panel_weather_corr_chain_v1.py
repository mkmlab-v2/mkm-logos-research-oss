# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_btrack_session_panel_weather_corr_chain_v1.py"
_WEATHER = _ROOT / "tests" / "fixtures" / "btrack_join_weather_smoke_v1.csv"
_OHLCV = _ROOT / "tests" / "fixtures" / "btrack_join_ohlcv_smoke_v1.csv"


def test_chain_panel_join_correlate_smoke(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_CHAIN),
            "--date-from",
            "2024-06-12",
            "--date-to",
            "2024-06-14",
            "--calendar-mode",
            "all",
            "--out-dir",
            str(tmp_path),
            "--tag",
            "pytest_smoke",
            "--weather-csv",
            str(_WEATHER),
            "--ohlcv-csv",
            str(_OHLCV),
            "--x-auto-prefixes",
            "elem_,wthr_,ohlcv_",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    corr = tmp_path / "btrack_joined_wide_correlation_pytest_smoke.json"
    assert corr.is_file()
    doc = json.loads(corr.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_joined_wide_correlation_v1"
    assert doc.get("params", {}).get("y_col") == "ohlcv_close"
    by_x = {c["x_col"]: c for c in doc.get("correlations") or []}
    assert "elem_fire" in by_x
