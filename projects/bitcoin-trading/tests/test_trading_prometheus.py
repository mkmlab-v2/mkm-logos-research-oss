"""Optional Prometheus exporter helpers (daemon metrics)."""

import os
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class TestTradingPrometheus(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("MKM_PROMETHEUS_METRICS_PORT", None)

    def test_refresh_noop_when_exporter_disabled(self) -> None:
        os.environ["MKM_PROMETHEUS_METRICS_PORT"] = "0"
        from src.monitoring import trading_prometheus as tp

        tp.start_prometheus_exporter_if_enabled("BTCUSDT")
        d = SimpleNamespace(
            running=True,
            enable_trading=False,
            testnet=True,
            restart_count=0,
            error_count=0,
            symbol="BTCUSDT",
            engine=None,
            start_time=datetime.now(),
            successful_trades=0,
            failed_trades=0,
        )
        tp.refresh_prometheus_from_daemon(d, exchange_snapshot={"available": False})


if __name__ == "__main__":
    unittest.main()
