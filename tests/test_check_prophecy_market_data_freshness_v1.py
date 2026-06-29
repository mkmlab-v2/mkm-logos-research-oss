# @MKM12-METADATA
# Type: Logic
# Purpose: Prophecy OHLCV freshness gate — stale vs fresh legs.

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_freshness_fresh_kospi_leg(tmp_path: Path) -> None:
    from scripts.check_prophecy_market_data_freshness_v1 import build_report

    csv_path = tmp_path / "kospi.csv"
    today = date.today()
    d0 = (today - timedelta(days=1)).isoformat()
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        f"{d0},100,101,99,100.5,1000\n",
        encoding="utf-8",
    )
    report = build_report(
        kospi_csv=csv_path,
        btc_csv=tmp_path / "missing_btc.csv",
        max_stale_days=7,
        ref=today,
    )
    assert report["all_ok"] is True
    assert report["legs"]["kospi"]["ok"] is True
    assert report["legs"]["btc"]["ok"] is True  # optional missing


def test_freshness_stale_kospi_fails_strict(tmp_path: Path) -> None:
    from scripts.check_prophecy_market_data_freshness_v1 import build_report

    csv_path = tmp_path / "kospi.csv"
    old = (date.today() - timedelta(days=30)).isoformat()
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        f"{old},100,101,99,100.5,1000\n",
        encoding="utf-8",
    )
    report = build_report(
        kospi_csv=csv_path,
        btc_csv=tmp_path / "missing_btc.csv",
        max_stale_days=7,
        ref=date.today(),
    )
    assert report["all_ok"] is False
    assert report["legs"]["kospi"]["stale"] is True


def test_freshness_cli_exit_strict_on_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    import scripts.check_prophecy_market_data_freshness_v1 as mod

    csv_path = tmp_path / "kospi.csv"
    old = (date.today() - timedelta(days=30)).isoformat()
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        f"{old},100,101,99,100.5,1000\n",
        encoding="utf-8",
    )
    argv = [
        "check_prophecy_market_data_freshness_v1.py",
        "--kospi-csv",
        str(csv_path),
        "--btc-csv",
        str(tmp_path / "btc.csv"),
        "--stdout-only",
        "--strict",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 1
