"""Tests for build_btrack_prophecy_score_from_ohlcv (B-Track dawn score JSON)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_actual_direction_neutral_band() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _actual_direction

    assert _actual_direction(0.00001, 5.0) == "neutral"  # 1 bp
    assert _actual_direction(0.001, 5.0) == "bull"  # 10 bps


def test_row_pair_for_eval_date() -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _row_pair_for_eval_date

    rows = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 101.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    p, c = _row_pair_for_eval_date(rows, "2000-01-02")
    assert p["close"] == 100.0 and c["close"] == 101.0


def test_build_rows_kospi(tmp_path: Path) -> None:
    from scripts.build_btrack_prophecy_score_from_ohlcv import _build_rows

    hyp = {
        "prediction": {"instrument": "kospi", "direction": "bull"},
    }
    kospi = [
        {"date": "2000-01-01", "close": 100.0, "open": 1, "high": 1, "low": 1, "volume": 1},
        {"date": "2000-01-02", "close": 102.0, "open": 1, "high": 1, "low": 1, "volume": 1},
    ]
    rows, meta = _build_rows(
        hypothesis=hyp,
        eval_date="2000-01-02",
        neutral_bps=5.0,
        kospi_rows=kospi,
        btc_rows=None,
        inst="kospi",
        predicted="bull",
    )
    assert not meta.get("warnings") or meta["warnings"] == []
    assert len(rows) == 1
    assert rows[0]["actual_direction"] == "bull"
    assert rows[0]["predicted_direction"] == "bull"


def test_hypothesis_fixture_smoke() -> None:
    p = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
    if not p.is_file():
        pytest.skip("no hypothesis fixture")
    h = json.loads(p.read_text(encoding="utf-8"))
    assert h.get("schema") == "btrack_hypothesis_prophecy_v1"
    assert "prediction" in h
