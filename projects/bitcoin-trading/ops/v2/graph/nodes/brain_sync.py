from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BRAIN_SYNC = PROJECT_ROOT / "memory" / "brain_sync" / "latest.md"
LATEST_STATE = PROJECT_ROOT / "memory" / "v2" / "latest_state.json"


def _state_is_recent(max_age_minutes: int = 30) -> bool:
    if not LATEST_STATE.exists():
        return False
    try:
        data = json.loads(LATEST_STATE.read_text(encoding="utf-8"))
    except Exception:
        return False

    ts = data.get("timestamp")
    if not isinstance(ts, str) or not ts.strip():
        return False
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - dt <= timedelta(minutes=max_age_minutes)


def brain_sync_node(state: dict[str, Any]) -> dict[str, Any]:
    if not BRAIN_SYNC.exists():
        state["brain_sync"] = {
            "sync_fresh": False,
            "note_path": str(BRAIN_SYNC),
            "summary": "Brain sync note missing",
        }
        return state

    text = BRAIN_SYNC.read_text(encoding="utf-8", errors="ignore")
    # Support both legacy note format and v2 on-demand format.
    has_legacy_markers = "Runtime Snapshot" in text and "Watchdog Event Summary" in text
    has_ondemand_markers = "Brain Sync On Demand" in text and "Runtime Snapshot" in text
    fresh = (has_legacy_markers or has_ondemand_markers) and _state_is_recent()
    state["brain_sync"] = {
        "sync_fresh": fresh,
        "note_path": str(BRAIN_SYNC),
        "summary": "Brain sync healthy" if fresh else "Brain sync stale_or_incomplete",
    }
    return state
