#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic OHLC bars from tick (price, time, volume) streams.

Replaces mock np.random OHLC in the realtime engine: each bar is time-bucketed,
open/first tick, high/low extrema, close/last tick, volume sum — no synthetic noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class _Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float


class TickOhlcAggregator:
    """
    Fixed-interval OHLC aggregation from ticks.

    Bar boundaries use ``int(ts.timestamp()) // interval_sec * interval_sec`` (UTC epoch seconds).
    """

    def __init__(self, bar_interval_sec: float = 60.0, max_stored_bars: int = 500) -> None:
        self.bar_interval_sec = max(1, int(bar_interval_sec))
        self.max_stored_bars = max(10, int(max_stored_bars))
        self._bars: List[_Bar] = []
        self._bucket: Optional[int] = None
        self._o = self._h = self._l = self._c = 0.0
        self._v = 0.0

    def completed_count(self) -> int:
        return len(self._bars)

    def push(self, ts: datetime, price: float, volume: float = 0.0) -> Optional[Dict[str, float]]:
        """
        Ingest one tick. Returns a dict of the *completed* bar (OHLCV) when a bucket rolls forward.
        """
        p = float(price)
        vol = float(volume) if volume is not None else 0.0
        bucket = int(ts.timestamp()) // self.bar_interval_sec

        completed: Optional[Dict[str, float]] = None

        if self._bucket is None:
            self._bucket = bucket
            self._o = self._h = self._l = self._c = p
            self._v = vol
        elif bucket == self._bucket:
            self._h = max(self._h, p)
            self._l = min(self._l, p)
            self._c = p
            self._v += vol
        elif bucket > self._bucket:
            completed = {
                "open": self._o,
                "high": self._h,
                "low": self._l,
                "close": self._c,
                "volume": self._v,
            }
            self._bars.append(
                _Bar(
                    open=float(completed["open"]),
                    high=float(completed["high"]),
                    low=float(completed["low"]),
                    close=float(completed["close"]),
                    volume=float(completed["volume"]),
                )
            )
            if len(self._bars) > self.max_stored_bars:
                self._bars = self._bars[-self.max_stored_bars :]
            self._bucket = bucket
            self._o = self._h = self._l = self._c = p
            self._v = vol
        else:
            # Clock skew / out-of-order tick: fold into current bar without closing future bars.
            self._h = max(self._h, p)
            self._l = min(self._l, p)
            self._c = p
            self._v += vol

        return completed

    def dataframe(self, max_rows: int = 200) -> pd.DataFrame:
        """Last ``max_rows`` *completed* bars as a DataFrame (open, high, low, close, volume)."""
        n = max(1, int(max_rows))
        slice_ = self._bars[-n:]
        if not slice_:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        rows: List[Dict[str, Any]] = [
            {
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in slice_
        ]
        return pd.DataFrame(rows)
