# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_JOIN = _ROOT / "scripts" / "join_btrack_session_panel_weather_ohlcv_v1.py"
_PANEL = _ROOT / "tests" / "fixtures" / "btrack_join_panel_smoke_v1.csv"
_WEATHER = _ROOT / "tests" / "fixtures" / "btrack_join_weather_smoke_v1.csv"
_OHLCV = _ROOT / "tests" / "fixtures" / "btrack_join_ohlcv_smoke_v1.csv"


def test_join_panel_weather_ohlcv_smoke(tmp_path: Path) -> None:
    out_csv = tmp_path / "joined.csv"
    out_meta = tmp_path / "joined.meta.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--panel-csv",
            str(_PANEL),
            "--weather-csv",
            str(_WEATHER),
            "--weather-date-col",
            "date",
            "--ohlcv-csv",
            str(_OHLCV),
            "--ohlcv-date-col",
            "Date",
            "--out-csv",
            str(out_csv),
            "--out-meta-json",
            str(out_meta),
            "--pearson-x",
            "elem_fire",
            "--pearson-y",
            "wthr_rain_mm",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    with out_csv.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 3
    assert rows[0]["wthr_rain_mm"] == "10.0"
    assert rows[0]["ohlcv_close"] == "100"
    assert rows[1]["wthr_temp_c"] == "25"
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("schema") == "btrack_session_panel_weather_ohlcv_join_v1"
    assert meta.get("counts", {}).get("n_panel_rows") == 3
    assert meta.get("pearson", {}).get("pearson_r") == pytest.approx(1.0, abs=1e-6)
