#!/usr/bin/env python3
"""
PM2 daemon watchdog for Windows rehearsal.

Checks:
1) heartbeat freshness
2) status file age
3) optional kill switch handling
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = PROJECT_ROOT / "memory"
HEARTBEAT_FILE = MEMORY_DIR / "trading_daemon_heartbeat.txt"
STATUS_FILE = MEMORY_DIR / "trading_daemon_status.json"
STOP_FILE = MEMORY_DIR / "STOP.txt"
WATCHDOG_STATE_FILE = MEMORY_DIR / "watchdog_state.json"


@dataclass
class WatchdogConfig:
    app_name: str
    stale_minutes: int
    restart_cooldown_minutes: int
    dry_run: bool


def _parse_iso8601(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _minutes_since(dt: datetime) -> float:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 60.0


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _pm2(cmd: list[str], dry_run: bool) -> int:
    command = ["pm2"] + cmd
    if dry_run:
        print(f"[DRY-RUN] {' '.join(command)}")
        return 0
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode


def _should_restart(cfg: WatchdogConfig) -> tuple[bool, str]:
    if STOP_FILE.exists():
        return (False, "STOP.txt exists; restart intentionally blocked.")

    hb_text = HEARTBEAT_FILE.read_text(encoding="utf-8").strip() if HEARTBEAT_FILE.exists() else ""
    hb_time = _parse_iso8601(hb_text) if hb_text else None
    if hb_time is None:
        return (True, "Heartbeat missing or invalid.")

    hb_age = _minutes_since(hb_time)
    if hb_age > cfg.stale_minutes:
        return (True, f"Heartbeat stale: {hb_age:.1f}m > {cfg.stale_minutes}m")

    status = _load_json(STATUS_FILE)
    start_time = _parse_iso8601(str(status.get("start_time", ""))) if status else None
    if status and start_time is None:
        return (True, "Status exists but start_time is invalid.")

    return (False, f"Healthy. heartbeat_age={hb_age:.1f}m")


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchdog for PM2 trading daemon")
    parser.add_argument("--app", default="bitcoin-trading-daemon-win", help="PM2 app name")
    parser.add_argument("--stale-minutes", type=int, default=15, help="Heartbeat stale threshold")
    parser.add_argument("--restart-cooldown-minutes", type=int, default=10, help="Minimum interval between restarts")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args()

    cfg = WatchdogConfig(
        app_name=args.app,
        stale_minutes=args.stale_minutes,
        restart_cooldown_minutes=args.restart_cooldown_minutes,
        dry_run=args.dry_run,
    )

    state = _load_json(WATCHDOG_STATE_FILE)
    last_restart = _parse_iso8601(str(state.get("last_restart_at", ""))) if state else None

    should_restart, reason = _should_restart(cfg)
    print(f"[watchdog] {reason}")
    if not should_restart:
        return 0

    if last_restart is not None:
        mins = _minutes_since(last_restart)
        if mins < cfg.restart_cooldown_minutes:
            print(
                f"[watchdog] Restart skipped by cooldown: {mins:.1f}m < {cfg.restart_cooldown_minutes}m",
                file=sys.stderr,
            )
            return 2

    rc = _pm2(["restart", cfg.app_name], cfg.dry_run)
    if rc != 0:
        print(f"[watchdog] pm2 restart failed with exit code {rc}", file=sys.stderr)
        return rc

    if cfg.dry_run:
        print(f"[watchdog] Restart simulated for {cfg.app_name}")
        return 0

    _save_json(
        WATCHDOG_STATE_FILE,
        {
            "last_restart_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "app": cfg.app_name,
        },
    )
    print(f"[watchdog] Restart executed for {cfg.app_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
