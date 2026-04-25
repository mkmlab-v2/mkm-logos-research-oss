"""Optional OpenTelemetry init (daemon)."""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


class TestTradingOtel(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "MKM_OTEL_ENABLED",
            "MKM_OTEL_CONSOLE",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
        ):
            os.environ.pop(k, None)

    def test_span_is_noop_when_disabled(self) -> None:
        os.environ.pop("MKM_OTEL_ENABLED", None)
        from src.monitoring import trading_otel

        with trading_otel.span("noop_test", attributes={"k": "v"}):
            pass


if __name__ == "__main__":
    unittest.main()
