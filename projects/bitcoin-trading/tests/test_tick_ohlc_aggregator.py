"""Deterministic tick→OHLC aggregation (no random bars)."""

import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from src.market.tick_ohlc_aggregator import TickOhlcAggregator


class TestTickOhlcAggregator(unittest.TestCase):
    def test_single_bucket_updates_high_low_close_volume(self) -> None:
        agg = TickOhlcAggregator(bar_interval_sec=60, max_stored_bars=100)
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertIsNone(agg.push(t0, 100.0, 1.0))
        self.assertIsNone(agg.push(t0 + timedelta(seconds=5), 110.0, 2.0))
        self.assertIsNone(agg.push(t0 + timedelta(seconds=10), 105.0, 1.0))
        self.assertEqual(agg.completed_count(), 0)

    def test_bucket_roll_closes_bar_deterministically(self) -> None:
        agg = TickOhlcAggregator(bar_interval_sec=10, max_stored_bars=100)
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        done = agg.push(t0, 100.0, 1.0)
        self.assertIsNone(done)
        agg.push(t0 + timedelta(seconds=3), 120.0, 1.0)
        done = agg.push(t0 + timedelta(seconds=10), 115.0, 2.0)
        self.assertIsNotNone(done)
        self.assertEqual(done["open"], 100.0)
        self.assertEqual(done["high"], 120.0)
        self.assertEqual(done["low"], 100.0)
        self.assertEqual(done["close"], 120.0)
        self.assertEqual(done["volume"], 2.0)
        self.assertEqual(agg.completed_count(), 1)

    def test_dataframe_order_and_columns(self) -> None:
        agg = TickOhlcAggregator(bar_interval_sec=5, max_stored_bars=50)
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        for i in range(3):
            b = base + timedelta(seconds=5 * i)
            agg.push(b, 10.0 + i, 1.0)
            agg.push(b + timedelta(seconds=2), 10.0 + i + 0.5, 0.5)
            agg.push(b + timedelta(seconds=4), 10.0 + i + 0.25, 0.25)
            if i < 2:
                agg.push(b + timedelta(seconds=5), 10.0 + i + 1.0, 0.1)
        df = agg.dataframe(max_rows=10)
        self.assertEqual(list(df.columns), ["open", "high", "low", "close", "volume"])
        self.assertGreaterEqual(len(df), 2)
        self.assertTrue((df["high"] >= df["open"]).all())
        self.assertTrue((df["high"] >= df["close"]).all())
        self.assertTrue((df["low"] <= df["open"]).all())
        self.assertTrue((df["low"] <= df["close"]).all())

    def test_empty_dataframe(self) -> None:
        agg = TickOhlcAggregator(bar_interval_sec=60)
        df = agg.dataframe()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)


if __name__ == "__main__":
    unittest.main()
