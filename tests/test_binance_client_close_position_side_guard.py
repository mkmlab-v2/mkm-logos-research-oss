from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "projects" / "bitcoin-trading" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import api.binance_client as bc  # noqa: E402


def _mk_client(positions: list[dict]):
    c = bc.BinanceFuturesClient.__new__(bc.BinanceFuturesClient)
    c.maker_only = False
    c.client = SimpleNamespace()
    recorded: list[dict] = []

    def _call_client(fn):
        # infer which function is requested by execution order
        if not recorded:
            recorded.append({"kind": "positions_called"})
            return positions
        # order submit phase
        order = fn()
        recorded.append({"kind": "order", "order": order})
        return order

    def _futures_create_order(**kwargs):
        return kwargs

    c.client.futures_position_information = lambda symbol: positions
    c.client.futures_create_order = _futures_create_order
    c._call_client = _call_client
    c._build_client_order_id = lambda prefix: f"{prefix}-id"
    return c, recorded


def test_close_position_targets_requested_short_only(monkeypatch):
    monkeypatch.setattr(bc, "USE_CCXT", False)
    positions = [
        {"positionSide": "LONG", "positionAmt": "0.003"},
        {"positionSide": "SHORT", "positionAmt": "-0.001"},
    ]
    c, recorded = _mk_client(positions)
    order = c.close_position(symbol="BTCUSDT", position_side="SHORT")
    assert order is not None
    assert order["positionSide"] == "SHORT"
    assert order["side"] == "BUY"
    assert float(order["quantity"]) == 0.001


def test_close_position_returns_none_when_requested_side_absent(monkeypatch):
    monkeypatch.setattr(bc, "USE_CCXT", False)
    positions = [{"positionSide": "LONG", "positionAmt": "0.003"}]
    c, _ = _mk_client(positions)
    order = c.close_position(symbol="BTCUSDT", position_side="SHORT")
    assert order is None

