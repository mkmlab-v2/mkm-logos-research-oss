from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MEMORY_DIR = PROJECT_ROOT / "memory"
HEARTBEAT = MEMORY_DIR / "trading_daemon_heartbeat.txt"
STOP_FILE = MEMORY_DIR / "STOP.txt"


def watchdog_node(state: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    action_hint = "KEEP"
    risk_level = "low"

    if STOP_FILE.exists():
        issues.append("Kill switch is ON")
        action_hint = "PAUSE"
        risk_level = "high"

    hb_age = None
    if HEARTBEAT.exists():
        raw = HEARTBEAT.read_text(encoding="utf-8", errors="ignore").strip()
        try:
            hb = datetime.fromisoformat(raw)
            hb_age = (datetime.now() - hb).total_seconds() / 60.0
        except Exception:
            issues.append("Heartbeat parse failed")
    else:
        issues.append("Heartbeat missing")

    if hb_age is None or hb_age > 15:
        issues.append("Heartbeat stale")
        if action_hint != "PAUSE":
            action_hint = "RESTART"
            risk_level = "medium"

    state["watchdog"] = {
        "risk_level": risk_level,
        "action_hint": action_hint,
        "issues": issues,
        "heartbeat_age_min": hb_age,
    }
    return state
