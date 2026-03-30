from __future__ import annotations

from datetime import datetime
from typing import Any


def athena_node(state: dict[str, Any]) -> dict[str, Any]:
    wd = state.get("watchdog", {})
    bs = state.get("brain_sync", {})

    decision = "KEEP_RUNNING"
    reason = "Runtime and sync healthy"

    if wd.get("action_hint") == "PAUSE":
        decision = "PAUSE_WITH_KILL_SWITCH"
        reason = "; ".join(wd.get("issues", [])) or "Kill switch policy"
    elif wd.get("action_hint") == "RESTART":
        decision = "REQUEST_RESTART"
        reason = "; ".join(wd.get("issues", [])) or "Watchdog requested restart"
    elif not bs.get("sync_fresh", False):
        reason = "Runtime healthy but brain sync stale"

    state["athena"] = {
        "decision": decision,
        "reason": reason,
        "requires_human_approval": state.get("execution_mode", "read-only") == "execute",
    }

    state.setdefault("decisions", []).append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "bot_name": "athena",
            "action": decision,
            "reasoning": reason,
        }
    )
    return state
