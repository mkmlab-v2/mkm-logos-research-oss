from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


RISK_SCORING_POLICY_REL = Path("ops") / "v2" / "policies" / "risk_scoring_policy.yaml"

_DEFAULT_POLICY = {
    "rules": {
        "watchdog_high": 95,
        "watchdog_medium": 70,
        "sentinel_blocked": 90,
        "policy_drift_present": 80,
        "cost_budget_breach": 75,
        "heartbeat_aging": 65,
        "incident_not_healthy": 60,
    },
    "thresholds": {"heartbeat_aging_minutes": 10},
    "mode_guardrail": {
        "force_shadow_score_threshold": 70,
        "block_execute_score_threshold": 85,
        "attach_incident_on_override": True,
    },
}


def _load_policy(project_root: Path) -> dict[str, Any]:
    path = project_root / RISK_SCORING_POLICY_REL
    if not path.exists():
        return _DEFAULT_POLICY
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = loaded.get("risk_scoring") or {}

        merged = {
            "rules": dict(_DEFAULT_POLICY["rules"]),
            "thresholds": dict(_DEFAULT_POLICY["thresholds"]),
            "mode_guardrail": dict(_DEFAULT_POLICY["mode_guardrail"]),
        }
        merged["rules"].update(raw.get("rules") or {})
        merged["thresholds"].update(raw.get("thresholds") or {})
        merged["mode_guardrail"].update(raw.get("mode_guardrail") or {})
        return merged
    except Exception:
        return _DEFAULT_POLICY


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def evaluate_risk_mode_guardrail(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    policy = _load_policy(project_root)
    rules = policy["rules"]
    thresholds = policy["thresholds"]
    mg = policy["mode_guardrail"]

    triggers: list[dict[str, Any]] = []

    wd = state.get("watchdog") or {}
    wd_risk = wd.get("risk_level")
    if wd_risk == "high":
        triggers.append({"key": "watchdog_high", "score": int(rules["watchdog_high"]), "reason": "watchdog risk high"})
    elif wd_risk == "medium":
        triggers.append({"key": "watchdog_medium", "score": int(rules["watchdog_medium"]), "reason": "watchdog risk medium"})

    if state.get("sentinel_approval") is False:
        triggers.append({"key": "sentinel_blocked", "score": int(rules["sentinel_blocked"]), "reason": "sentinel blocked"})

    pd = state.get("policy_drift") or {}
    if int(pd.get("drift_count") or 0) > 0:
        triggers.append({"key": "policy_drift_present", "score": int(rules["policy_drift_present"]), "reason": "policy drift present"})

    cg = state.get("cost_governor") or {}
    if cg.get("budget_ok") is False:
        triggers.append({"key": "cost_budget_breach", "score": int(rules["cost_budget_breach"]), "reason": "cost budget breach"})

    hb = _safe_float(wd.get("heartbeat_age_min"))
    hb_threshold = float(thresholds.get("heartbeat_aging_minutes", 10))
    if hb is not None and hb > hb_threshold:
        triggers.append({"key": "heartbeat_aging", "score": int(rules["heartbeat_aging"]), "reason": f"heartbeat age {hb:.2f}m > {hb_threshold:.2f}m"})

    incident_status = state.get("incident_status")
    if incident_status and str(incident_status).lower() != "healthy":
        triggers.append({"key": "incident_not_healthy", "score": int(rules["incident_not_healthy"]), "reason": f"incident status {incident_status}"})

    risk_score = max((int(t["score"]) for t in triggers), default=20)

    force_shadow_threshold = int(mg.get("force_shadow_score_threshold", 70))
    block_execute_threshold = int(mg.get("block_execute_score_threshold", 85))

    proposed_mode = "read-only"
    if risk_score >= force_shadow_threshold:
        proposed_mode = "shadow"

    block_execute = risk_score >= block_execute_threshold

    return {
        "risk_score": risk_score,
        "triggers": triggers,
        "proposed_mode": proposed_mode,
        "block_execute": block_execute,
        "mode_guardrail": {
            "force_shadow_score_threshold": force_shadow_threshold,
            "block_execute_score_threshold": block_execute_threshold,
            "attach_incident_on_override": bool(mg.get("attach_incident_on_override", True)),
        },
    }
