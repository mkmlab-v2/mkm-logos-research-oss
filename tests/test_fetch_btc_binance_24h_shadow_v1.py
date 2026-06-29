"""Binance BTC shadow sidecar."""

from __future__ import annotations

import json

from scripts.fetch_btc_binance_24h_shadow_v1 import dual_leg_agreement, fetch_binance_btc_shadow


def test_dual_leg_agreement() -> None:
    assert dual_leg_agreement("up", "up") == "agree"
    assert dual_leg_agreement("down", "up") == "disagree"
    assert dual_leg_agreement("flat", "up") == "partial"


def test_fetch_binance_shadow_offline(monkeypatch) -> None:
    def fake_fetch(url: str, timeout: float = 12.0):
        if "klines" in url:
            return [
                [1_700_000_000_000, "90000", "91000", "89000", "90500", "100", 1_700_086_400_000, "0", 0, "0", "0", "0"],
                [1_700_086_400_000, "90500", "92000", "90000", "91500", "100", 1_700_172_800_000, "0", 0, "0", "0", "0"],
            ]
        return {"priceChangePercent": "1.5", "lastPrice": "91500"}

    monkeypatch.setattr(
        "scripts.fetch_btc_binance_24h_shadow_v1._fetch_json",
        fake_fetch,
    )
    doc = fetch_binance_btc_shadow(calendar_kst="2026-06-01")
    assert doc["ok"] is True
    assert doc["latest_daily"]["direction"] == "up"
