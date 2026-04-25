"""Regression: _execute_trade early exits (no network)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

import src.integration.realtime_trading_with_monitoring as rtm


def _mock_monitor_factory(*_a, **_k):
    m = MagicMock()
    m.enable_monitoring = True
    m.enable_trading = True
    return m


def _mock_compression_factory(*_a, **_k):
    return MagicMock()


class TestExecuteTradeGuards(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        os.environ["DISABLE_PROPHECY_STACK"] = "1"

    def tearDown(self) -> None:
        os.environ.pop("DISABLE_PROPHECY_STACK", None)

    async def test_same_side_pyramiding_blocked(self) -> None:
        mock_client = MagicMock()
        mock_client.get_klines.return_value = []
        mock_client.get_account_info.return_value = {"available_balance": 10000.0}
        mock_client.get_current_price.return_value = 100000.0
        mock_client.get_position.return_value = {
            "side": "SHORT",
            "quantity": 0.003,
            "entry_price": 90000.0,
            "mark_price": 90000.0,
            "unrealized_pnl": 0.0,
        }
        mock_client.get_recent_fills.return_value = []

        with (
            patch.object(rtm, "BinanceFuturesClient", return_value=mock_client),
            patch.object(rtm, "BinanceRealtimeConnector", MagicMock()),
            patch.object(rtm, "UnifiedTradingMonitor", side_effect=_mock_monitor_factory),
            patch.object(rtm, "CompressionTradingBridge", side_effect=_mock_compression_factory),
        ):
            eng = rtm.RealtimeTradingWithMonitoring(
                symbol="BTCUSDT",
                testnet=True,
                initial_capital=10000.0,
                leverage=2,
                enable_monitoring=True,
                enable_trading=True,
            )
            eng.risk_guardian = None

            await eng._execute_trade("SELL", 0.55)

        self.assertEqual(eng.last_execution_trace.get("reason"), "same_side_pyramiding_blocked")
        self.assertEqual(eng.last_4ai_trace.get("ai4_audit", {}).get("final_reason"), "same_side_pyramiding_blocked")
        mock_client.open_short_position.assert_not_called()

    async def test_invalid_mark_price(self) -> None:
        mock_client = MagicMock()
        mock_client.get_klines.return_value = []
        mock_client.get_account_info.return_value = {"available_balance": 10000.0}
        mock_client.get_current_price.return_value = 0.0
        mock_client.get_position.return_value = None

        with (
            patch.object(rtm, "BinanceFuturesClient", return_value=mock_client),
            patch.object(rtm, "BinanceRealtimeConnector", MagicMock()),
            patch.object(rtm, "UnifiedTradingMonitor", side_effect=_mock_monitor_factory),
            patch.object(rtm, "CompressionTradingBridge", side_effect=_mock_compression_factory),
        ):
            eng = rtm.RealtimeTradingWithMonitoring(
                symbol="BTCUSDT",
                testnet=True,
                initial_capital=10000.0,
                leverage=2,
                enable_monitoring=True,
                enable_trading=True,
            )
            eng.risk_guardian = None

            await eng._execute_trade("BUY", 0.55)

        self.assertEqual(eng.last_execution_trace.get("reason"), "invalid_mark_price")
        mock_client.open_long_position.assert_not_called()

    async def test_risk_manager_blocked(self) -> None:
        mock_client = MagicMock()
        mock_client.get_klines.return_value = []
        mock_client.get_account_info.return_value = {"available_balance": 10000.0}
        mock_client.get_current_price.return_value = 100000.0
        mock_client.get_position.return_value = None
        mock_client.get_recent_fills.return_value = []

        with (
            patch.object(rtm, "BinanceFuturesClient", return_value=mock_client),
            patch.object(rtm, "BinanceRealtimeConnector", MagicMock()),
            patch.object(rtm, "UnifiedTradingMonitor", side_effect=_mock_monitor_factory),
            patch.object(rtm, "CompressionTradingBridge", side_effect=_mock_compression_factory),
        ):
            eng = rtm.RealtimeTradingWithMonitoring(
                symbol="BTCUSDT",
                testnet=True,
                initial_capital=10000.0,
                leverage=2,
                enable_monitoring=True,
                enable_trading=True,
            )
            eng.risk_guardian = None
            eng.risk_manager.can_trade = MagicMock(return_value=False)  # type: ignore[method-assign]

            await eng._execute_trade("BUY", 0.55)

        self.assertEqual(eng.last_execution_trace.get("reason"), "risk_manager_blocked")
        mock_client.open_long_position.assert_not_called()


if __name__ == "__main__":
    unittest.main()
