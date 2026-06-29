"""Smoke tests for B-track OHLCV static LUT builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_prior_map_matches_walkforward_sample() -> None:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import prior_map_from_csv
    from scripts.run_prophecy_per_date_combo_walkforward_v1 import _prior_map

    kospi = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    if not kospi.is_file():
        pytest.skip("kospi csv missing")
    lut = prior_map_from_csv(kospi)
    wf = _prior_map(kospi)
    assert lut == wf


def test_feature_map_matches_walkforward_sample() -> None:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import feature_map_from_csv
    from scripts.run_prophecy_per_date_combo_walkforward_v1 import _feature_map

    btc = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
    if not btc.is_file():
        pytest.skip("btc csv missing")
    lut = feature_map_from_csv(btc)
    wf = _feature_map(btc)
    assert lut == wf


def test_build_lut_cli_last_180(tmp_path: Path) -> None:
    import subprocess
    import sys

    kospi = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
    if not kospi.is_file() or not btc.is_file():
        pytest.skip("ohlcv csv missing")

    out = tmp_path / "lut.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_btrack_ohlcv_feature_lut_v1.py"),
        "--kospi-csv",
        str(kospi),
        "--btc-csv",
        str(btc),
        "--last-n-intersection",
        "180",
        "--output",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_ohlcv_feature_lut_v1"
    assert doc["research_only"] is True
    assert doc["stats"]["n_intersection_dates"] == 180
    assert len(doc["intersection_dates"]) == 180
    assert "ret_3" in next(iter(doc["features_by_instrument"]["btc"].values()))


def test_maps_from_lut_match_csv_tail() -> None:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import (
        load_lut_document,
        prior_and_feature_maps_from_lut,
        prior_map_from_csv,
        feature_map_from_csv,
    )

    lut_path = ROOT / "reports" / "btrack_ohlcv_feature_lut_v1_latest.json"
    kospi = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
    if not lut_path.is_file() or not kospi.is_file() or not btc.is_file():
        pytest.skip("lut or csv missing")

    doc = load_lut_document(lut_path)
    km, bm, kf, bf = prior_and_feature_maps_from_lut(doc)
    for d in doc["intersection_dates"][-5:]:
        assert km[d] == prior_map_from_csv(kospi)[d]
        assert bm[d] == prior_map_from_csv(btc)[d]
        assert kf[d] == feature_map_from_csv(kospi)[d]
        assert bf[d] == feature_map_from_csv(btc)[d]


def test_fills_cache_empty_ok(tmp_path: Path) -> None:
    from scripts.build_btrack_fills_daily_feature_cache_v1 import build_cache_document

    empty = tmp_path / "trades.json"
    empty.write_text("[]\n", encoding="utf-8")
    doc = build_cache_document(trades_path=empty, generated_at_utc="2026-06-09T00:00:00Z")
    assert doc["stats"]["n_fill_rows"] == 0
    assert doc["stats"]["n_daily_buckets"] == 0
    assert doc["align_panel_join_policy"]["auto_merge"] is False
