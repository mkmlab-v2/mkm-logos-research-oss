"""Deterministic tick → OHLCV bar aggregation (fixed-width time buckets)."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

import pandas as pd


def _bucket_start(ts: datetime, bar_interval_sec: int) -> int:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    sec = int(ts.timestamp())
    return sec - (sec % bar_interval_sec)


class TickOhlcAggregator:
    """Accumulates trades into OHLCV bars; ``push`` returns a completed bar dict when the bucket rolls."""

    def __init__(self, bar_interval_sec: int, max_stored_bars: int = 10_000) -> None:
        if bar_interval_sec < 1:
            raise ValueError("bar_interval_sec must be >= 1")
        self._interval = bar_interval_sec
        self._max = max_stored_bars
        self._completed: deque[dict[str, Any]] = deque(maxlen=max_stored_bars)
        self._cur_key: int | None = None
        self._o: float | None = None
        self._h: float | None = None
        self._l: float | None = None
        self._c: float | None = None
        self._v: float = 0.0

    def _reset_current(self, price: float, vol: float) -> None:
        self._o = self._h = self._l = self._c = price
        self._v = vol

    def push(self, ts: datetime, price: float, volume: float) -> dict[str, Any] | None:
        key = _bucket_start(ts, self._interval)
        if self._cur_key is None:
            self._cur_key = key
            self._reset_current(price, volume)
            return None

        if key == self._cur_key:
            assert self._o is not None and self._h is not None and self._l is not None
            self._h = max(self._h, price)
            self._l = min(self._l, price)
            self._c = price
            self._v += volume
            return None

        done = {
            "open": self._o,
            "high": self._h,
            "low": self._l,
            "close": self._c,
            "volume": self._v,
        }
        self._completed.append(done)
        while len(self._completed) > self._max:
            self._completed.popleft()

        self._cur_key = key
        self._reset_current(price, volume)
        return done

    def completed_count(self) -> int:
        return len(self._completed)

    def dataframe(self, max_rows: int | None = None) -> pd.DataFrame:
        rows = list(self._completed)
        if max_rows is not None:
            rows = rows[-max_rows:]
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        return pd.DataFrame(rows)
