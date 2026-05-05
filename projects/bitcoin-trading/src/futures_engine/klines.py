"""Binance futures_klines / CCXT OHLCV → high/low 시계열."""
from __future__ import annotations

from typing import Any


def highs_lows_from_klines(klines: list[Any]) -> tuple[list[float], list[float]]:
    """
    - python-binance ``futures_klines`` 행: [openTime, open, high, low, close, ...]
    - CCXT ``fetch_ohlcv`` 행: [timestamp, open, high, low, close, volume]
    """
    highs: list[float] = []
    lows: list[float] = []
    if not klines:
        return highs, lows
    first = klines[0]
    if isinstance(first, (list, tuple)) and len(first) >= 5:
        # Heuristic: CCXT ohlcv has ms timestamp int/float first; Binance has open time int
        try:
            float(first[1])
        except (TypeError, ValueError):
            return highs, lows
        # Both have high at index 2, low at 3
        for row in klines:
            if not isinstance(row, (list, tuple)) or len(row) < 4:
                continue
            highs.append(float(row[2]))
            lows.append(float(row[3]))
    return highs, lows
