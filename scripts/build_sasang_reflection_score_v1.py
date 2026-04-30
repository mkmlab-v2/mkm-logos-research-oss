#!/usr/bin/env python3
"""Build a quantified Sasang-theory reflection score (3-axis + total)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_MAPPING = ART / "emotion_state_mapping_latest.json"
DEFAULT_PREFLIGHT = ART / "emotion_state_live_preflight_gate_latest.json"
DEFAULT_WEEKLY = ART / "layer1_layer5_weekly_ops_report_latest.json"
DEFAULT_PROFILE = ART / "cursor_ai_operating_profile_v1_latest.json"
DEFAULT_LAYER1 = ART / "layer1_router_benchmark_latest.json"
DEFAULT_LAYER5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_INTEGRATED = ART / "layer1_layer5_integrated_gate_report_latest.json"
DEFAULT_DECISIONS_LOG = ROOT / "reports" / "agent_decisions_log.jsonl"
DEFAULT_WEEKLY_HISTORY = ART / "layer1_layer5_weekly_ops_history_log.jsonl"
DEFAULT_OUT = ART / "sasang_theory_reflection_score_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _parse_dt(ts: Any) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _axis_structural(mapping: dict[str, Any], profile: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    states = mapping.get("states") if isinstance(mapping.get("states"), list) else []
    state_count = len([s for s in states if isinstance(s, dict)])
    state_names = [str(s.get("state")) for s in states if isinstance(s, dict) and s.get("state")]
    unique_signals = {
        str((s.get("activation_rule") or {}).get("input_signal"))
        for s in states
        if isinstance(s, dict) and isinstance(s.get("activation_rule"), dict) and (s.get("activation_rule") or {}).get("input_signal")
    }

    track = str(mapping.get("track") or "")
    track_ok = track == "b_track_sandbox_only"
    profile_enabled = bool(((profile.get("emotion_control") or {}).get("enabled")))

    score = 0.0
    if state_count >= 3:
        score += 0.40
    elif state_count == 2:
        score += 0.25
    elif state_count == 1:
        score += 0.10
    score += min(0.20, 0.10 * float(len(unique_signals)))
    if track_ok:
        score += 0.20
    if profile_enabled:
        score += 0.20

    return min(1.0, score), {
        "state_count": state_count,
        "state_names": state_names,
        "unique_activation_signals": sorted(unique_signals),
        "track": track,
        "track_is_b_sandbox_only": track_ok,
        "profile_emotion_control_enabled": profile_enabled,
    }


def _axis_control(preflight: dict[str, Any], profile: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    thresholds = preflight.get("thresholds") if isinstance(preflight.get("thresholds"), dict) else {}
    checks_dynamic = preflight.get("checks_dynamic") if isinstance(preflight.get("checks_dynamic"), dict) else {}
    checks_static = preflight.get("checks_static") if isinstance(preflight.get("checks_static"), dict) else {}

    kmh_dynamic = bool(thresholds.get("enable_kmh_dynamic"))
    tau_prime_present = "tau_prime" in thresholds
    dynamic_gate_ok = all(bool(v) for v in checks_dynamic.values()) if checks_dynamic else False
    static_gate_ok = all(bool(v) for v in checks_static.values()) if checks_static else False
    decision_go = str(preflight.get("decision") or "") == "GO_LIVE_CANDIDATE"

    profile_ctrl = profile.get("emotion_control") if isinstance(profile.get("emotion_control"), dict) else {}
    alpha_present = profile_ctrl.get("alpha") is not None
    tau_bounds_present = (profile_ctrl.get("tau_min") is not None) and (profile_ctrl.get("tau_max") is not None)

    score = 0.0
    if kmh_dynamic:
        score += 0.25
    if tau_prime_present:
        score += 0.15
    if dynamic_gate_ok:
        score += 0.25
    if static_gate_ok:
        score += 0.15
    if decision_go:
        score += 0.10
    if alpha_present and tau_bounds_present:
        score += 0.10

    return min(1.0, score), {
        "kmh_dynamic_enabled": kmh_dynamic,
        "tau_prime_present": tau_prime_present,
        "dynamic_checks_all_true": dynamic_gate_ok,
        "static_checks_all_true": static_gate_ok,
        "preflight_decision": preflight.get("decision"),
        "profile_alpha_present": alpha_present,
        "profile_tau_bounds_present": tau_bounds_present,
    }


def _axis_outcome(weekly: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    summary = weekly.get("summary") if isinstance(weekly.get("summary"), dict) else {}
    base_pass = str(weekly.get("base_overall_status") or summary.get("base_weekly_status") or "") == "PASS"
    weekly_pass = str(weekly.get("overall_status") or "") == "PASS"
    streak_status_pass = str(summary.get("weekly_streak_gate_status") or "") == "PASS"
    preflight_go = str(summary.get("emotion_preflight_decision") or "") == "GO_LIVE_CANDIDATE"
    memory_pass = str(summary.get("memory_validation_status") or "") == "PASS"
    integrated_go = str(summary.get("integrated_decision") or "") == "GO_CONTROLLED"

    score = 0.0
    if base_pass:
        score += 0.20
    if weekly_pass:
        score += 0.20
    if streak_status_pass:
        score += 0.20
    if preflight_go:
        score += 0.15
    if memory_pass:
        score += 0.10
    if integrated_go:
        score += 0.15

    return min(1.0, score), {
        "base_overall_status": weekly.get("base_overall_status") or summary.get("base_weekly_status"),
        "overall_status": weekly.get("overall_status"),
        "weekly_streak_gate_status": summary.get("weekly_streak_gate_status"),
        "emotion_preflight_decision": summary.get("emotion_preflight_decision"),
        "memory_validation_status": summary.get("memory_validation_status"),
        "integrated_decision": summary.get("integrated_decision"),
    }


def _compute_penalties(
    layer1: dict[str, Any],
    layer5: dict[str, Any],
    integrated: dict[str, Any],
    profile: dict[str, Any],
    decisions_log_rows: list[dict[str, Any]],
    weekly_history_rows: list[dict[str, Any]],
    *,
    lookback_hours: int,
    weekly_history_window: int,
    max_penalty: float,
) -> tuple[float, list[dict[str, Any]]]:
    penalties: list[dict[str, Any]] = []
    gates = profile.get("gates") if isinstance(profile.get("gates"), dict) else {}
    runtime = profile.get("runtime") if isinstance(profile.get("runtime"), dict) else {}
    max_tool_calls = int(runtime.get("max_tool_calls") or 12)
    max_p95_runtime_ms = float(gates.get("max_layer5_runtime_ms") or 500.0)

    layer5_metrics = layer5.get("metrics") if isinstance(layer5.get("metrics"), dict) else {}
    p95 = float(layer5_metrics.get("p95_gate_runtime_ms") or 0.0)
    if p95 > max_p95_runtime_ms:
        overflow_ratio = min(1.0, (p95 - max_p95_runtime_ms) / max(max_p95_runtime_ms, 1.0))
        penalties.append(
            {
                "type": "latency_over_budget",
                "penalty": round(0.20 * overflow_ratio, 4),
                "actual": p95,
                "budget": max_p95_runtime_ms,
            }
        )

    now_utc = datetime.now(timezone.utc)
    lookback_cutoff = now_utc.timestamp() - max(1, int(lookback_hours)) * 3600
    recent_decisions: list[dict[str, Any]] = []
    for row in decisions_log_rows:
        dt = _parse_dt(row.get("timestamp"))
        if dt is None:
            continue
        if dt.timestamp() >= lookback_cutoff:
            recent_decisions.append(row)

    decision_events = len(recent_decisions)
    events_per_hour = float(decision_events) / max(float(lookback_hours), 1.0)
    max_events_per_hour = float(runtime.get("max_decision_events_per_hour") or max_tool_calls)
    if events_per_hour > max_events_per_hour:
        overflow_ratio = min(1.0, (events_per_hour - max_events_per_hour) / max(max_events_per_hour, 1.0))
        penalties.append(
            {
                "type": "decision_event_pressure",
                "penalty": round(0.10 * overflow_ratio, 4),
                "actual_events_per_hour": round(events_per_hour, 4),
                "budget_events_per_hour": max_events_per_hour,
                "lookback_hours": int(lookback_hours),
            }
        )

    retry_counts = [int(r.get("retry_count") or 0) for r in recent_decisions]
    retry_avg = (sum(retry_counts) / float(len(retry_counts))) if retry_counts else 0.0
    retry_max = max(retry_counts) if retry_counts else 0
    max_retry_avg = float(runtime.get("max_retry_avg") or 0.25)
    if retry_avg > max_retry_avg:
        overflow_ratio = min(1.0, (retry_avg - max_retry_avg) / max(max_retry_avg, 0.01))
        penalties.append(
            {
                "type": "retry_pressure",
                "penalty": round(0.10 * overflow_ratio, 4),
                "actual_retry_avg": round(retry_avg, 4),
                "actual_retry_max": retry_max,
                "budget_retry_avg": max_retry_avg,
                "lookback_hours": int(lookback_hours),
            }
        )

    hist = weekly_history_rows[-max(1, int(weekly_history_window)) :]
    hold_rows = 0
    for row in hist:
        status = str(row.get("base_weekly_status") or row.get("overall_status") or "")
        if status != "PASS":
            hold_rows += 1
    hold_ratio = (float(hold_rows) / float(len(hist))) if hist else 0.0
    max_hold_ratio = float(runtime.get("max_weekly_hold_ratio") or 0.5)
    if hold_ratio > max_hold_ratio:
        overflow_ratio = min(1.0, (hold_ratio - max_hold_ratio) / max(max_hold_ratio, 0.01))
        penalties.append(
            {
                "type": "recovery_pressure",
                "penalty": round(0.10 * overflow_ratio, 4),
                "actual_hold_ratio": round(hold_ratio, 4),
                "budget_hold_ratio": max_hold_ratio,
                "weekly_history_window": int(weekly_history_window),
            }
        )

    reasons = integrated.get("reasons") if isinstance(integrated.get("reasons"), list) else []
    if reasons:
        penalties.append(
            {
                "type": "recovery_needed",
                "penalty": 0.10,
                "actual": len(reasons),
                "note": "Integrated gate reported reasons requiring recovery actions.",
            }
        )

    total_penalty = min(float(max_penalty), sum(float(p.get("penalty") or 0.0) for p in penalties))
    return total_penalty, penalties


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_LAYER1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_LAYER5)
    ap.add_argument("--integrated-json", type=Path, default=DEFAULT_INTEGRATED)
    ap.add_argument("--decisions-log-jsonl", type=Path, default=DEFAULT_DECISIONS_LOG)
    ap.add_argument("--weekly-history-jsonl", type=Path, default=DEFAULT_WEEKLY_HISTORY)
    ap.add_argument("--weight-structural", type=float, default=0.34)
    ap.add_argument("--weight-control", type=float, default=0.33)
    ap.add_argument("--weight-outcome", type=float, default=0.33)
    ap.add_argument("--lookback-hours", type=int, default=24)
    ap.add_argument("--weekly-history-window", type=int, default=8)
    ap.add_argument("--max-penalty", type=float, default=0.30)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mapping = _read_json(args.mapping_json)
    preflight = _read_json(args.preflight_json)
    weekly = _read_json(args.weekly_json)
    profile = _read_json(args.profile_json)
    layer1 = _read_json(args.layer1_json)
    layer5 = _read_json(args.layer5_json)
    integrated = _read_json(args.integrated_json)
    decisions_log_rows = _read_jsonl(args.decisions_log_jsonl)
    weekly_history_rows = _read_jsonl(args.weekly_history_jsonl)

    structural_score, structural_evidence = _axis_structural(mapping, profile)
    control_score, control_evidence = _axis_control(preflight, profile)
    outcome_score, outcome_evidence = _axis_outcome(weekly)

    w_sum = float(args.weight_structural) + float(args.weight_control) + float(args.weight_outcome)
    if w_sum <= 0:
        w_structural, w_control, w_outcome = 0.34, 0.33, 0.33
        w_sum = 1.0
    else:
        w_structural = float(args.weight_structural) / w_sum
        w_control = float(args.weight_control) / w_sum
        w_outcome = float(args.weight_outcome) / w_sum

    total = (
        w_structural * structural_score
        + w_control * control_score
        + w_outcome * outcome_score
    )
    total_penalty, penalties = _compute_penalties(
        layer1,
        layer5,
        integrated,
        profile,
        decisions_log_rows,
        weekly_history_rows,
        lookback_hours=int(args.lookback_hours),
        weekly_history_window=int(args.weekly_history_window),
        max_penalty=float(args.max_penalty),
    )
    adjusted_total = max(0.0, total - total_penalty)

    out = {
        "schema": "sasang_theory_reflection_score_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "mapping_json": str(args.mapping_json).replace("\\", "/"),
            "preflight_json": str(args.preflight_json).replace("\\", "/"),
            "weekly_json": str(args.weekly_json).replace("\\", "/"),
            "profile_json": str(args.profile_json).replace("\\", "/"),
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "integrated_json": str(args.integrated_json).replace("\\", "/"),
            "decisions_log_jsonl": str(args.decisions_log_jsonl).replace("\\", "/"),
            "weekly_history_jsonl": str(args.weekly_history_jsonl).replace("\\", "/"),
        },
        "weights": {
            "structural": w_structural,
            "control": w_control,
            "outcome": w_outcome,
        },
        "scores": {
            "structural_reflection": round(structural_score, 4),
            "control_reflection": round(control_score, 4),
            "outcome_reflection": round(outcome_score, 4),
            "total_reflection": round(total, 4),
            "total_reflection_100": round(total * 100.0, 1),
            "total_penalty": round(total_penalty, 4),
            "adjusted_total_reflection": round(adjusted_total, 4),
            "adjusted_total_reflection_100": round(adjusted_total * 100.0, 1),
        },
        "penalties": penalties,
        "evidence": {
            "structural": structural_evidence,
            "control": control_evidence,
            "outcome": outcome_evidence,
        },
        "interpretation": {
            "tier": (
                "high" if adjusted_total >= 0.80 else
                "medium" if adjusted_total >= 0.60 else
                "low"
            ),
            "note": "This score measures operational reflection of Sasang-inspired control, not anthropomorphic emotion.",
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "total_reflection_100": out["scores"]["total_reflection_100"],
                "adjusted_total_reflection_100": out["scores"]["adjusted_total_reflection_100"],
                "penalty_count": len(penalties),
                "tier": out["interpretation"]["tier"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
