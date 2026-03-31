#!/usr/bin/env python3
"""Collect direct-watchdog KPI snapshot for 7-day rehearsal."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = PROJECT_ROOT / "memory"
KPI_DIR = MEMORY_DIR / "kpi"
WATCHDOG_LOG = MEMORY_DIR / "watchdog_direct.log"
HEARTBEAT_FILE = MEMORY_DIR / "trading_daemon_heartbeat.txt"
STOP_FILE = MEMORY_DIR / "STOP.txt"
STATUS_FILE = MEMORY_DIR / "trading_daemon_status.json"
TASK_NAME = "Bitcoin-Direct-Watchdog-5min"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _task_is_ready() -> bool:
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and "Ready" in proc.stdout


def _heartbeat_age_minutes() -> float | None:
    raw = _read_text(HEARTBEAT_FILE).strip()
    if not raw:
        return None
    try:
        hb = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if hb.tzinfo is None:
        # Daemon heartbeat currently writes local naive timestamps.
        now_local = datetime.now()
        return (now_local - hb).total_seconds() / 60.0
    now_utc = datetime.now(timezone.utc)
    return (now_utc - hb).total_seconds() / 60.0


def _watchdog_counters(log_text: str) -> dict:
    lines = log_text.splitlines()
    return {
        "log_lines": len(lines),
        "daemon_healthy": sum("Daemon healthy" in x for x in lines),
        "daemon_started": sum("Starting daemon process" in x for x in lines),
        "stale_restart": sum("heartbeat stale" in x.lower() for x in lines),
        "kill_switch_events": sum("STOP.txt exists" in x for x in lines),
    }


def main() -> int:
    KPI_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    log_text = _read_text(WATCHDOG_LOG)
    status = _safe_json(STATUS_FILE)
    hb_age = _heartbeat_age_minutes()

    exchange_24h = status.get("exchange_snapshot_24h") if isinstance(status.get("exchange_snapshot_24h"), dict) else {}
    snapshot = {
        "ts_utc": now.isoformat(),
        "scheduler_ready": _task_is_ready(),
        "kill_switch_on": STOP_FILE.exists(),
        "heartbeat_age_min": hb_age,
        "status_running": status.get("running"),
        "status_restart_count": status.get("restart_count"),
        "status_error_count": status.get("error_count"),
        "status_symbol": status.get("symbol"),
        "status_testnet": status.get("testnet"),
        "status_enable_trading": status.get("enable_trading"),
        "exchange_snapshot_24h_available": exchange_24h.get("available"),
        "exchange_snapshot_24h_fills_count": exchange_24h.get("fills_count"),
        "exchange_snapshot_24h_realized_pnl": exchange_24h.get("realized_pnl"),
        "exchange_snapshot_24h_commission": exchange_24h.get("commission"),
        "exchange_snapshot_24h_funding_fee": exchange_24h.get("funding_fee"),
        "exchange_snapshot_24h_net": exchange_24h.get("net"),
        "watchdog": _watchdog_counters(log_text),
    }

    day = now.strftime("%Y%m%d")
    jsonl_path = KPI_DIR / f"kpi_snapshot_{day}.jsonl"
    latest_path = KPI_DIR / "latest_kpi.json"

    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    latest_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
