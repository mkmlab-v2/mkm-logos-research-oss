from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = PROJECT_ROOT / "ops" / "v2" / "policies" / "risk_policy.yaml"


def _load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def sentinel_node(state: dict[str, Any]) -> dict[str, Any]:
    policy = _load_policy().get("risk_policy", {})
    wd = state.get("watchdog", {})
    ath = state.get("athena", {})

    approval = True
    message = "approved"

    if wd.get("risk_level") == "high":
        approval = False
        message = "blocked: high risk"

    if ath.get("decision") == "PAUSE_WITH_KILL_SWITCH":
        approval = False
        message = "blocked: pause decision"

    execute_approval_valid = bool(state.get("execute_approval_valid", False))
    if (
        state.get("execution_mode") == "execute"
        and policy.get("require_human_approval_for_execute", True)
        and not execute_approval_valid
    ):
        approval = False
        message = "blocked: execute mode requires human approval"

    state["sentinel_approval"] = approval
    state["sentinel_message"] = message
    state.setdefault("incidents", []).append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "sentinel",
            "severity": "info" if approval else "warning",
            "message": message,
            "details": {
                "watchdog_risk": wd.get("risk_level"),
                "athena_decision": ath.get("decision"),
            },
        }
    )
    return state
