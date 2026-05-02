"""Unit tests for export_binance_fills_to_cursor_trade_history_v1 row normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_export_module():
    root = Path(__file__).resolve().parent.parent
    path = root / "scripts" / "export_binance_fills_to_cursor_trade_history_v1.py"
    spec = importlib.util.spec_from_file_location("export_binance_cth_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_row_from_native_maps_binance_futures_trade():
    ex = _load_export_module()
    raw = {
        "symbol": "BTCUSDT",
        "id": 999,
        "orderId": 12345,
        "side": "BUY",
        "price": "76000.0",
        "qty": "0.001",
        "quoteQty": "76.0",
        "realizedPnl": "-0.5",
        "commission": "-0.01",
        "commissionAsset": "USDT",
        "time": 1700000000000,
        "positionSide": "LONG",
        "maker": False,
    }
    row = ex._row_from_native(raw)
    assert row["timestamp"] == 1700000000000
    assert row["side"] == "BUY"
    assert row["position_side"] == "LONG"
    assert row["realized_pnl"] == -0.5
    assert row["trade_id"] == 999


def test_row_from_ccxt_maps_info_realized_pnl():
    ex = _load_export_module()
    raw = {
        "timestamp": 1700000001000,
        "datetime": "2023-11-14T00:00:01.000Z",
        "symbol": "BTC/USDT:USDT",
        "side": "sell",
        "amount": 0.002,
        "price": 76500.0,
        "info": {
            "symbol": "BTCUSDT",
            "id": 1000,
            "orderId": 555,
            "side": "SELL",
            "price": "76500",
            "qty": "0.002",
            "realizedPnl": "1.25",
            "commission": "-0.02",
            "commissionAsset": "USDT",
            "positionSide": "SHORT",
            "time": 1700000001000,
        },
    }
    row = ex._row_from_ccxt(raw)
    assert row["timestamp"] == 1700000001000
    assert row["side"] == "SELL"
    assert row["position_side"] == "SHORT"
    assert row["realized_pnl"] == 1.25


def test_normalize_rows_sorts_by_time():
    ex = _load_export_module()
    rows = [
        {"time": 3, "realizedPnl": "0", "symbol": "BTCUSDT", "side": "BUY", "qty": "0", "price": "1"},
        {"time": 1, "realizedPnl": "0", "symbol": "BTCUSDT", "side": "SELL", "qty": "0", "price": "1"},
    ]
    out = ex._normalize_rows(rows)
    assert [r["timestamp"] for r in out] == [1, 3]
