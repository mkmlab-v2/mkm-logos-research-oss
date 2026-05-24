"""Market session calendar for commander morning briefing."""

from __future__ import annotations

from datetime import date

import scripts.commander_market_session_calendar_v1 as cal


def test_krx_weekend_closed() -> None:
    sat = date(2026, 5, 23)  # Saturday
    krx = cal.krx_session_status(sat)
    assert krx["trading_today"] is False
    assert krx["status"] == "weekend"
    assert "휴장" in krx["label_ko"]


def test_krx_weekday_open() -> None:
    fri = date(2026, 5, 22)
    krx = cal.krx_session_status(fri)
    assert krx["trading_today"] is True
    assert krx["status"] == "open"


def test_fetch_market_seal_weekend_kospi_closed(monkeypatch) -> None:
    import scripts.commander_market_session_calendar_v1 as cmod
    import scripts.multi_asset_market_adapter_v1 as ma

    monkeypatch.setattr(cmod, "parse_calendar_kst", lambda _=None: date(2026, 5, 23))
    monkeypatch.setattr(cmod, "calendar_kst_today", lambda: "2026-05-23")
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: None)

    seal = ma.fetch_market_seal()
    assert seal["kospi"]["direction"] == "market_closed"
    assert seal["krx_session"]["trading_today"] is False
    assert "휴장" in seal["session_banner_ko"]
