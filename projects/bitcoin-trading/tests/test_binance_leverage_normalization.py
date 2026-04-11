"""BinanceFuturesClient leverage/symbol coercion (-1102 mitigation)."""

import unittest

from src.api.binance_client import BinanceFuturesClient


class TestLeverageNormalization(unittest.TestCase):
    def test_coerce_float_yaml_style(self) -> None:
        self.assertEqual(BinanceFuturesClient._coerce_leverage_int(2.0), 2)
        self.assertEqual(BinanceFuturesClient._coerce_leverage_int("3"), 3)

    def test_coerce_clamp(self) -> None:
        self.assertEqual(BinanceFuturesClient._coerce_leverage_int(200), 125)
        self.assertEqual(BinanceFuturesClient._coerce_leverage_int(0), 1)

    def test_symbol_slash(self) -> None:
        self.assertEqual(
            BinanceFuturesClient._normalize_futures_symbol("btc/usdt"),
            "BTCUSDT",
        )

    def test_symbol_upper(self) -> None:
        self.assertEqual(
            BinanceFuturesClient._normalize_futures_symbol("btcusdt"),
            "BTCUSDT",
        )

    def test_symbol_invalid(self) -> None:
        self.assertIsNone(BinanceFuturesClient._normalize_futures_symbol(""))
        self.assertIsNone(BinanceFuturesClient._normalize_futures_symbol(None))


if __name__ == "__main__":
    unittest.main()
