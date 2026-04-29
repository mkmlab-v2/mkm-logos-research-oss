#!/usr/bin/env python3
"""Build Logos regime/risk-gate state from insight template + optional observations."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "docs" / "final" / "artifacts" / "logos_regime_risk_gate_insights_template_v1.json"
DEFAULT_OBS = ROOT / "docs" / "final" / "artifacts" / "logos_regime_risk_gate_observations_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "logos_regime_risk_gate_state_latest.json"
DEFAULT_LOG = ROOT / "reports" / "logos_regime_risk_gate_log.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _eval_condition(trigger_value: float, expr: str) -> bool:
    s = (expr or "").strip().lower()
    if s.startswith(">="):
        return trigger_value >= _safe_float(s[2:].strip(), 0.0)
    if s.startswith(">"):
        return trigger_value > _safe_float(s[1:].strip(), 0.0)
    if s.startswith("<="):
        return trigger_value <= _safe_float(s[2:].strip(), 0.0)
    if s.startswith("<"):
        return trigger_value < _safe_float(s[1:].strip(), 0.0)
    if s.startswith("=="):
        return abs(trigger_value - _safe_float(s[2:].strip(), 0.0)) < 1e-12
    return False


def _action_rank(action: str, priority: list[str]) -> int:
    try:
        return priority.index(action)
    except ValueError:
        return len(priority)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--observations-json", type=Path, default=DEFAULT_OBS)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--default-trigger-value", type=float, default=0.0)
    args = ap.parse_args()

    template = _load_json(args.template_json)
    observations = _load_json(args.observations_json)
    obs_values = observations.get("metrics") if isinstance(observations.get("metrics"), dict) else observations
    if not isinstance(obs_values, dict):
        obs_values = {}

    rules = template.get("insight_rules") if isinstance(template.get("insight_rules"), list) else []
    priorities = (
        ((template.get("decision_binding") or {}).get("action_priority"))
        if isinstance((template.get("decision_binding") or {}).get("action_priority"), list)
        else []
    )
    if not priorities:
        priorities = [
            "FORCE_HOLD",
            "HOLD_POINTER_ROUTE",
            "REDUCE_EXPOSURE",
            "NO_NEW_ALERTS_UNTIL_RESET",
            "OBSERVATION_ONLY_ALERT",
            "NO_CHANGE",
        ]

    rows: list[dict[str, Any]] = []
    triggered_actions: list[str] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id") or "").strip()
        metric = str(item.get("trigger_metric") or "").strip()
        cond = str(item.get("trigger_condition") or "").strip()
        action = str(item.get("effective_action") or "NO_CHANGE")
        raw_v = obs_values.get(metric, args.default_trigger_value)
        val = _safe_float(raw_v, args.default_trigger_value)
        triggered = _eval_condition(val, cond)
        if triggered:
            triggered_actions.append(action)
        rows.append(
            {
                "insight_id": rid,
                "role": item.get("role"),
                "alert_level": item.get("alert_level"),
                "trigger_metric": metric,
                "trigger_condition": cond,
                "trigger_value": val,
                "triggered": triggered,
                "effective_action_if_triggered": action,
                "validation_metric": item.get("validation_metric"),
                "validation_goal": item.get("validation_goal"),
            }
        )

    lock_state = bool(obs_values.get("price_output_locked", False))
    if lock_state:
        triggered_actions.append("FORCE_HOLD")
    if not triggered_actions:
        triggered_actions.append("NO_CHANGE")
    effective_action = sorted(triggered_actions, key=lambda x: _action_rank(x, priorities))[0]

    now = _iso_now()
    out = {
        "schema": "logos_regime_risk_gate_state_v1",
        "generated_at_utc": now,
        "template_ref": str(args.template_json),
        "observations_ref": str(args.observations_json),
        "lock_state": {"price_output_locked": lock_state},
        "triggered_rule_count": sum(1 for r in rows if r.get("triggered")),
        "effective_action": effective_action,
        "rows": rows,
        "decision_binding": {
            "action_priority": priorities,
            "conflict_resolution": ((template.get("decision_binding") or {}).get("conflict_resolution")),
        },
        "notes": [
            "Template-driven evaluation only (research mode).",
            "Directional execution is prohibited while price_output_locked=true.",
        ],
    }
    _write_json(args.state_json, out)

    for r in rows:
        _append_jsonl(
            args.log_jsonl,
            {
                "ts_utc": now,
                "schema": "logos_regime_risk_gate_log_row_v1",
                "insight_id": r.get("insight_id"),
                "trigger_metric": r.get("trigger_metric"),
                "trigger_value": r.get("trigger_value"),
                "triggered": r.get("triggered"),
                "effective_action": effective_action,
                "lock_state": lock_state,
                "note": "state_build",
            },
        )

    print(f"WROTE: {args.state_json}")
    print(f"APPEND: {args.log_jsonl}")
    print(f"effective_action={effective_action} triggered={out['triggered_rule_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

