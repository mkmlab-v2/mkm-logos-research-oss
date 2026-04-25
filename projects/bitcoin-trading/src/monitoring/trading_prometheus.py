# -*- coding: utf-8 -*-
"""
Optional Prometheus /metrics for the bitcoin trading daemon.

Install: pip install prometheus_client
Enable: MKM_PROMETHEUS_METRICS_PORT=9108 (default 9108); set 0 to disable.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_HAVE_PROM = False
try:
    from prometheus_client import Counter, Gauge, start_http_server

    _HAVE_PROM = True
except ImportError:  # pragma: no cover - optional dependency
    Counter = None  # type: ignore[misc, assignment]
    Gauge = None  # type: ignore[misc, assignment]
    start_http_server = None  # type: ignore[misc, assignment]

_server_started = False
_metrics: Dict[str, Any] = {}


def _sym(daemon: Any) -> str:
    return str(getattr(daemon, "symbol", None) or "UNKNOWN")


def start_prometheus_exporter_if_enabled(symbol: str) -> None:
    """Register metrics and start :PORT/metrics (once). No-op if lib missing or port disabled."""
    global _server_started, _metrics
    if not _HAVE_PROM:
        logger.info("prometheus_client not installed; metrics exporter disabled.")
        return

    raw = os.environ.get("MKM_PROMETHEUS_METRICS_PORT", "9108").strip().lower()
    if raw in ("", "0", "off", "false", "no", "none"):
        logger.info("Prometheus metrics disabled (MKM_PROMETHEUS_METRICS_PORT=%s).", raw or "(empty)")
        return
    try:
        port = int(raw)
    except ValueError:
        logger.warning("Invalid MKM_PROMETHEUS_METRICS_PORT=%r; metrics disabled.", raw)
        return
    if port <= 0:
        return

    if not _metrics:
        L = ["symbol"]
        _metrics["daemon_running"] = Gauge(
            "mkm_trading_daemon_running",
            "Main daemon loop considers itself running (1/0).",
            L,
        )
        _metrics["daemon_enable_trading"] = Gauge(
            "mkm_trading_daemon_enable_trading",
            "Daemon-level enable_trading flag (1/0).",
            L,
        )
        _metrics["testnet"] = Gauge(
            "mkm_trading_testnet",
            "Binance testnet mode (1=testnet).",
            L,
        )
        _metrics["restart_count"] = Gauge(
            "mkm_trading_daemon_restart_count",
            "Engine restart attempts in this daemon process.",
            L,
        )
        _metrics["error_count"] = Gauge(
            "mkm_trading_daemon_error_count",
            "Cumulative daemon/engine error count.",
            L,
        )
        _metrics["uptime_seconds"] = Gauge(
            "mkm_trading_daemon_uptime_seconds",
            "Daemon uptime in seconds.",
            L,
        )
        _metrics["successful_trades"] = Gauge(
            "mkm_trading_daemon_successful_trades",
            "Synced successful trade / fill counter (daemon view).",
            L,
        )
        _metrics["failed_trades"] = Gauge(
            "mkm_trading_daemon_failed_trades",
            "Failed trade / circuit counter (daemon view).",
            L,
        )
        _metrics["exchange_fills_24h"] = Gauge(
            "mkm_trading_exchange_fills_24h",
            "24h user trades count from exchange snapshot when available.",
            L,
        )
        _metrics["engine_running"] = Gauge(
            "mkm_trading_engine_running",
            "Trading engine asyncio loop running (1/0).",
            L,
        )
        _metrics["engine_trading_enabled"] = Gauge(
            "mkm_trading_engine_trading_enabled",
            "Engine enable_trading (1/0).",
            L,
        )
        _metrics["ws_ticks"] = Gauge(
            "mkm_trading_engine_ws_tick_count",
            "WebSocket tick counter from engine when available.",
            L,
        )
        _metrics["maker_only"] = Gauge(
            "mkm_trading_engine_maker_only",
            "Engine runtime maker_only (1/0).",
            L,
        )
        _metrics["strict_maker"] = Gauge(
            "mkm_trading_engine_strict_maker_enforcement",
            "Engine strict maker enforcement (1/0).",
            L,
        )
        _metrics["risk_guard_paused"] = Gauge(
            "mkm_trading_risk_guardian_trading_paused",
            "Risk guardian paused trading (1/0).",
            L,
        )
        _metrics["last_trace_skipped"] = Gauge(
            "mkm_trading_last_execution_was_skipped",
            "1 if last_execution_trace.decision is skipped.",
            L,
        )
        _metrics["refresh_total"] = Counter(
            "mkm_trading_prometheus_refresh_total",
            "How often the daemon pushed a metrics refresh.",
            L,
        )

    if not _server_started:
        assert start_http_server is not None
        start_http_server(port)
        _server_started = True
        logger.info("Prometheus exporter: listening on 0.0.0.0:%s (/metrics) symbol=%s", port, symbol)


def refresh_prometheus_from_daemon(
    daemon: Any,
    *,
    exchange_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Update gauges from daemon + optional engine. Safe no-op if exporter disabled."""
    if not _HAVE_PROM or not _metrics:
        return

    sym = _sym(daemon)
    labels = {"symbol": sym}

    def _set(name: str, value: float) -> None:
        _metrics[name].labels(**labels).set(float(value))

    try:
        _set("daemon_running", 1.0 if getattr(daemon, "running", False) else 0.0)
        _set("daemon_enable_trading", 1.0 if getattr(daemon, "enable_trading", False) else 0.0)
        _set("testnet", 1.0 if getattr(daemon, "testnet", True) else 0.0)
        _set("restart_count", float(getattr(daemon, "restart_count", 0) or 0))
        _set("error_count", float(getattr(daemon, "error_count", 0) or 0))
        st = getattr(daemon, "start_time", None)
        if st is not None:
            _set("uptime_seconds", max(0.0, (datetime.now() - st).total_seconds()))
        else:
            _set("uptime_seconds", 0.0)
        _set("successful_trades", float(getattr(daemon, "successful_trades", 0) or 0))
        _set("failed_trades", float(getattr(daemon, "failed_trades", 0) or 0))

        fills = None
        if isinstance(exchange_snapshot, dict) and exchange_snapshot.get("available"):
            fc = exchange_snapshot.get("fills_count")
            if isinstance(fc, (int, float)):
                fills = float(fc)
        if fills is not None:
            _set("exchange_fills_24h", fills)
        else:
            _set("exchange_fills_24h", -1.0)

        eng = getattr(daemon, "engine", None)
        if eng is not None:
            _set("engine_running", 1.0 if getattr(eng, "running", False) else 0.0)
            _set("engine_trading_enabled", 1.0 if getattr(eng, "enable_trading", False) else 0.0)
            _set("ws_ticks", float(getattr(eng, "ws_tick_count", 0) or 0))
            rc = getattr(eng, "_maker_only", None)
            _set("maker_only", 1.0 if rc else 0.0)
            sm = getattr(eng, "_strict_maker_enforcement", None)
            _set("strict_maker", 1.0 if sm else 0.0)
            try:
                st_eng = eng.get_status() if hasattr(eng, "get_status") else {}
            except Exception:
                st_eng = {}
            rg = st_eng.get("risk_guardian") if isinstance(st_eng, dict) else None
            if isinstance(rg, dict) and "trading_paused" in rg:
                _set("risk_guard_paused", 1.0 if rg.get("trading_paused") else 0.0)
            else:
                _set("risk_guard_paused", 0.0)
            let = st_eng.get("last_execution_trace") if isinstance(st_eng, dict) else None
            if isinstance(let, dict) and str(let.get("decision", "")).lower() == "skipped":
                _set("last_trace_skipped", 1.0)
            else:
                _set("last_trace_skipped", 0.0)
        else:
            _set("engine_running", 0.0)
            _set("engine_trading_enabled", 0.0)
            _set("ws_ticks", 0.0)
            _set("maker_only", 0.0)
            _set("strict_maker", 0.0)
            _set("risk_guard_paused", 0.0)
            _set("last_trace_skipped", 0.0)

        _metrics["refresh_total"].labels(**labels).inc()
    except Exception as e:
        logger.debug("prometheus refresh skipped: %s", e)
