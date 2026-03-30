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


def main() -> int:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_tag = now.strftime("%Y-%m-%d")

    kpi = _safe_json(LATEST_KPI)
    status = _safe_json(STATUS_JSON)
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
    md.append("## 2) Watchdog Event Summary")
    wd = kpi.get("watchdog", {}) if isinstance(kpi.get("watchdog"), dict) else {}
    md.append(f"- daemon_healthy_count: {wd.get('daemon_healthy')}")
    md.append(f"- daemon_started_count: {wd.get('daemon_started')}")
    md.append(f"- stale_restart_count: {wd.get('stale_restart')}")
    md.append(f"- kill_switch_event_count: {wd.get('kill_switch_events')}")
    md.append("")
    md.append("## 3) Git Drift (Top 25)")
    if git_lines:
        for line in git_lines:
            md.append(f"- `{line}`")
    else:
        md.append("- clean")
    md.append("")
    md.append("## 4) Last 25 Watchdog Logs")
    if log_lines:
        md.append("```text")
        md.extend(log_lines)
        md.append("```")
    else:
        md.append("- no watchdog logs")
    md.append("")
    md.append("## 5) Operator Decision")
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
