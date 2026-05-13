# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_JOIN = _ROOT / "scripts" / "join_btrack_session_panel_weather_ohlcv_v1.py"
_CORR = _ROOT / "scripts" / "correlate_btrack_joined_wide_csv_v1.py"
_PANEL = _ROOT / "tests" / "fixtures" / "btrack_join_panel_smoke_v1.csv"
_WEATHER = _ROOT / "tests" / "fixtures" / "btrack_join_weather_smoke_v1.csv"
_OHLCV = _ROOT / "tests" / "fixtures" / "btrack_join_ohlcv_smoke_v1.csv"


def test_correlate_after_join_smoke(tmp_path: Path) -> None:
    wide = tmp_path / "wide.csv"
    r0 = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--panel-csv",
            str(_PANEL),
            "--weather-csv",
            str(_WEATHER),
            "--ohlcv-csv",
            str(_OHLCV),
            "--out-csv",
            str(wide),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r0.returncode == 0, r0.stderr

    r1 = subprocess.run(
        [
            sys.executable,
            str(_CORR),
            "--input-csv",
            str(wide),
            "--y-col",
            "elem_fire",
            "--x-cols",
            "wthr_rain_mm,ohlcv_close",
            "--min-pairs",
            "3",
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r1.returncode == 0, r1.stderr
    doc = json.loads(r1.stdout)
    assert doc.get("schema") == "btrack_joined_wide_correlation_v1"
    by_x = {c["x_col"]: c for c in doc.get("correlations") or []}
    assert by_x["wthr_rain_mm"].get("status") == "computed"
    assert by_x["wthr_rain_mm"].get("pearson_r") == pytest.approx(1.0, abs=1e-6)
    assert by_x["ohlcv_close"].get("n_pairs") == 3


def test_correlate_x_auto_prefixes_smoke(tmp_path: Path) -> None:
    wide = tmp_path / "wide.csv"
    r0 = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--panel-csv",
            str(_PANEL),
            "--weather-csv",
            str(_WEATHER),
            "--ohlcv-csv",
            str(_OHLCV),
            "--out-csv",
            str(wide),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r0.returncode == 0, r0.stderr
    r1 = subprocess.run(
        [
            sys.executable,
            str(_CORR),
            "--input-csv",
            str(wide),
            "--y-col",
            "elem_fire",
            "--x-auto-prefixes",
            "wthr_,ohlcv_",
            "--min-pairs",
            "3",
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r1.returncode == 0, r1.stderr
    doc = json.loads(r1.stdout)
    ids = {c["x_col"] for c in doc.get("correlations") or []}
    assert "wthr_rain_mm" in ids and "ohlcv_close" in ids
