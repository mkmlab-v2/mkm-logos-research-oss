# @MKM12-METADATA
# Type: Logic
# Purpose: KOSPI CSV loader accepts Date-header yfinance exports.

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_VIX = _ROOT / "research" / "market_data" / "vix_daily_external_yf.csv"


def test_load_kospi_yf_rows_date_header_fixture() -> None:
    pytest.importorskip("pandas")
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    assert _VIX.is_file()
    rows = load_kospi_yf_rows(_VIX)
    assert len(rows) >= 10
    assert set(rows[0].keys()) == {"date", "open", "high", "low", "close", "volume"}
    assert len(rows[0]["date"]) == 10
