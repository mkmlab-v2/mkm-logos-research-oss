"""LOT_SIZE floor helper (no API keys, no network)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "projects" / "bitcoin-trading" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.binance_client import BinanceFuturesClient  # noqa: E402


def test_floor_below_min_returns_zero() -> None:
    assert BinanceFuturesClient._floor_quantity_to_lot(0.0005, 0.001, 9000.0, 0.001) == 0.0


def test_floor_to_step() -> None:
    assert BinanceFuturesClient._floor_quantity_to_lot(0.0015, 0.001, 9000.0, 0.001) == 0.001
    assert BinanceFuturesClient._floor_quantity_to_lot(0.002, 0.001, 9000.0, 0.001) == 0.002
