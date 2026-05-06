#!/usr/bin/env python3
"""Evaluate 1+3 thresholds into ok/warning/critical gate level."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METRICS = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_window_metrics_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_threshold_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_gate_decision_latest.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _to_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evaluate(metrics: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    metrics_7d = metrics.get("window_7d_metrics", {})
    metrics_14d = metrics.get("window_14d_metrics", {})
    latest_gate_state = metrics.get("latest_gate_state", {})

    warning_policy = policy.get("thresholds", {}).get("warning", {})
    critical_policy = policy.get("thresholds", {}).get("critical", {})

    reasons: list[str] = []
    gate_level = "ok"

    # Critical checks first (fail-close precedence)
    if _to_int(metrics_14d.get("critical_violation_count")) >= _to_int(
        critical_policy.get("min_critical_violation_count_14d")
    ):
        gate_level = "critical"
        reasons.append("critical_violation_count_14d_threshold")

    if _to_int(metrics_14d.get("core_failure_count")) >= _to_int(
        critical_policy.get("min_core_failure_count_14d")
    ):
        gate_level = "critical"
        reasons.append("core_failure_count_14d_threshold")

    if _to_float(metrics_14d.get("degradation_ratio")) >= _to_float(
        critical_policy.get("min_degradation_ratio_14d")
    ):
        gate_level = "critical"
        reasons.append("degradation_ratio_14d_threshold")

    if bool(critical_policy.get("force_hold_on_emergency_stop", True)) and bool(
        metrics.get("emergency_stop", False)
    ):
        gate_level = "critical"
        reasons.append("emergency_stop_forced_hold")

    # Warning checks (only if not critical)
    if gate_level != "critical":
        if _to_int(metrics_7d.get("warning_signal_count")) >= _to_int(
            warning_policy.get("min_warning_signal_count_7d")
        ):
            gate_level = "warning"
            reasons.append("warning_signal_count_7d_threshold")

        if _to_float(metrics_7d.get("degradation_ratio")) >= _to_float(
            warning_policy.get("min_degradation_ratio_7d")
        ):
            gate_level = "warning"
            reasons.append("degradation_ratio_7d_threshold")

        if _to_int(metrics_7d.get("hold_event_count")) >= _to_int(
            warning_policy.get("min_hold_event_count_7d")
        ):
            gate_level = "warning"
            reasons.append("hold_event_count_7d_threshold")

    actions = policy.get("actions", {}).get(gate_level, [])
    review_hours = _to_int(policy.get("review_intervals_hours", {}).get(gate_level), default=24)
    next_review = _utc_now() + timedelta(hours=review_hours)

    return {
        "schema": "one_plus_three_gate_decision_v1",
        "generated_at_utc": _utc_now().isoformat().replace("+00:00", "Z"),
        "inputs": {
            "metrics_schema": metrics.get("schema"),
            "policy_schema": policy.get("schema"),
            "latest_gate_level": latest_gate_state.get("gate_level", "unknown"),
        },
        "gate_level": gate_level,
        "reason_codes": reasons or ["no_threshold_triggered"],
        "actions": actions,
        "next_review_utc": next_review.isoformat().replace("+00:00", "Z"),
        "windows": {
            "window_7d_metrics": metrics_7d,
            "window_14d_metrics": metrics_14d,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 1+3 warning/critical gate decision.")
    parser.add_argument("--metrics-json", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.metrics_json.exists():
        raise FileNotFoundError(f"Missing metrics file: {args.metrics_json}")
    if not args.policy_json.exists():
        raise FileNotFoundError(f"Missing policy file: {args.policy_json}")

    metrics = _load_json(args.metrics_json)
    policy = _load_json(args.policy_json)
    out = _evaluate(metrics, policy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"[1+3-gate] level={out['gate_level']} reasons={','.join(out['reason_codes'])} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
