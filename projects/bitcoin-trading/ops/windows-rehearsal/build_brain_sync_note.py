#!/usr/bin/env python3
"""Build daily brain-sync markdown from watchdog and KPI state."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = PROJECT_ROOT / "memory"
KPI_DIR = MEMORY_DIR / "kpi"
BRAIN_DIR = MEMORY_DIR / "brain_sync"
WATCHDOG_LOG = MEMORY_DIR / "watchdog_direct.log"
LATEST_KPI = KPI_DIR / "latest_kpi.json"
STATUS_JSON = MEMORY_DIR / "trading_daemon_status.json"


def _safe_text(path: Path) -> str:
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


def _git_status_short() -> list[str]:
    cmd = ["git", "status", "--short", "--", "projects/bitcoin-trading"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        return ["git status failed"]
    lines = [x.rstrip() for x in proc.stdout.splitlines() if x.strip()]
    return lines[:25]


def _last_watchdog_lines(n: int = 25) -> list[str]:
    text = _safe_text(WATCHDOG_LOG)
    lines = [x for x in text.splitlines() if x.strip()]
    return lines[-n:]


def _exchange_snapshot_24h(status: dict) -> dict:
    raw = status.get("exchange_snapshot_24h")
    if isinstance(raw, dict):
        return raw
    return {
        "available": False,
        "fills_count": None,
        "realized_pnl": None,
        "commission": None,
        "funding_fee": None,
        "net": None,
    }


def _kpi_exchange_history_insight(limit: int = 288) -> dict:
    """
    Build lightweight insight from KPI JSONL history.
    limit=288 ~= 24h at 5min cadence (safe upper bound for mixed cadence).
    """
    history_files = sorted(KPI_DIR.glob("kpi_snapshot_*.jsonl"), reverse=True)
    if not history_files:
        return {"available": False, "reason": "no_kpi_history"}

    rows: list[dict] = []
    try:
        for line in history_files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception:
        return {"available": False, "reason": "kpi_read_error"}

    if not rows:
        return {"available": False, "reason": "empty_kpi_history"}

    tail = rows[-limit:]
    net_series: list[float] = []
    fills_series: list[float] = []
    for row in tail:
        net = row.get("exchange_snapshot_24h_net")
        fills = row.get("exchange_snapshot_24h_fills_count")
        if isinstance(net, (int, float)):
            net_series.append(float(net))
        if isinstance(fills, (int, float)):
            fills_series.append(float(fills))

    if not net_series:
        return {"available": False, "reason": "no_exchange_24h_series"}

    latest_net = net_series[-1]
    first_net = net_series[0]
    net_delta = latest_net - first_net
    max_net = max(net_series)
    min_net = min(net_series)

    latest_fills = fills_series[-1] if fills_series else None
    avg_net_per_fill = None
    if isinstance(latest_fills, (int, float)) and latest_fills > 0:
        avg_net_per_fill = latest_net / latest_fills

    return {
        "available": True,
        "samples": len(tail),
        "series_points": len(net_series),
        "net_first": round(first_net, 8),
        "net_latest": round(latest_net, 8),
        "net_delta": round(net_delta, 8),
        "net_min": round(min_net, 8),
        "net_max": round(max_net, 8),
        "fills_latest": int(latest_fills) if isinstance(latest_fills, (int, float)) else None,
        "avg_net_per_fill_latest": round(avg_net_per_fill, 8) if avg_net_per_fill is not None else None,
    }


def main() -> int:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_tag = now.strftime("%Y-%m-%d")

    kpi = _safe_json(LATEST_KPI)
    status = _safe_json(STATUS_JSON)
    exchange_24h = _exchange_snapshot_24h(status)
    exchange_insight = _kpi_exchange_history_insight()
    git_lines = _git_status_short()
    log_lines = _last_watchdog_lines(25)

    md = []
    md.append(f"# Brain Sync Daily Note ({date_tag})")
    md.append("")
    md.append("## 1) Runtime Snapshot")
    md.append(f"- scheduler_ready: {kpi.get('scheduler_ready')}")
    md.append(f"- kill_switch_on: {kpi.get('kill_switch_on')}")
    md.append(f"- heartbeat_age_min: {kpi.get('heartbeat_age_min')}")
    md.append(f"- status_running: {status.get('running')}")
    md.append(f"- restart_count: {status.get('restart_count')}")
    md.append(f"- error_count: {status.get('error_count')}")
    md.append(f"- symbol: {status.get('symbol')}")
    md.append(f"- testnet: {status.get('testnet')}")
    md.append(f"- enable_trading: {status.get('enable_trading')}")
    md.append("")
    md.append("## 2) Exchange Snapshot (24h, realized)")
    md.append(f"- available: {exchange_24h.get('available')}")
    md.append(f"- fills_count: {exchange_24h.get('fills_count')}")
    md.append(f"- realized_pnl: {exchange_24h.get('realized_pnl')}")
    md.append(f"- commission: {exchange_24h.get('commission')}")
    md.append(f"- funding_fee: {exchange_24h.get('funding_fee')}")
    md.append(f"- net: {exchange_24h.get('net')}")
    md.append("")
    md.append("## 3) Exchange Insight (history from KPI JSONL)")
    md.append(f"- available: {exchange_insight.get('available')}")
    if exchange_insight.get("available"):
        md.append(f"- samples: {exchange_insight.get('samples')} (series_points={exchange_insight.get('series_points')})")
        md.append(f"- net_first -> net_latest: {exchange_insight.get('net_first')} -> {exchange_insight.get('net_latest')} (delta={exchange_insight.get('net_delta')})")
        md.append(f"- net_range: min={exchange_insight.get('net_min')} / max={exchange_insight.get('net_max')}")
        md.append(f"- fills_latest: {exchange_insight.get('fills_latest')}")
        md.append(f"- avg_net_per_fill_latest: {exchange_insight.get('avg_net_per_fill_latest')}")
    else:
        md.append(f"- reason: {exchange_insight.get('reason')}")
    md.append("")
    md.append("## 4) Watchdog Event Summary")
    wd = kpi.get("watchdog", {}) if isinstance(kpi.get("watchdog"), dict) else {}
    md.append(f"- daemon_healthy_count: {wd.get('daemon_healthy')}")
    md.append(f"- daemon_started_count: {wd.get('daemon_started')}")
    md.append(f"- stale_restart_count: {wd.get('stale_restart')}")
    md.append(f"- kill_switch_event_count: {wd.get('kill_switch_events')}")
    md.append("")
    md.append("## 5) Git Drift (Top 25)")
    if git_lines:
        for line in git_lines:
            md.append(f"- `{line}`")
    else:
        md.append("- clean")
    md.append("")
    md.append("## 6) Last 25 Watchdog Logs")
    if log_lines:
        md.append("```text")
        md.extend(log_lines)
        md.append("```")
    else:
        md.append("- no watchdog logs")
    md.append("")
    md.append("## 7) Operator Decision")
    md.append("- Keep current mode / Pause with STOP.txt / Adjust threshold")

    content = "\n".join(md) + "\n"
    file_path = BRAIN_DIR / f"brain_sync_{now.strftime('%Y%m%d')}.md"
    latest = BRAIN_DIR / "latest.md"

    file_path.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")

    print(str(file_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
