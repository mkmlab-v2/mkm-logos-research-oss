#!/usr/bin/env python3
"""Build MKM emotion-reasoning state snapshot (research_only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_emotion_reasoning_state_v1_latest.json"
DEFAULT_SCHEMA = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "mkm_emotion_reasoning_state_v1.schema.json"
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def build_state(
    *,
    user_hostility: float,
    uncertainty: float,
    urgency: float,
    goal_clarity: float,
    previous_failures: int,
) -> dict[str, float]:
    """Deterministic transition from simple input features."""
    # Baseline defaults (calm-balanced operating mode)
    state: dict[str, float] = {
        "intent_alignment": 0.70,
        "self_other_balance": 0.55,
        "tone_stability": 0.72,
        "reactivity": 0.28,
        "empathic_bias": 0.52,
        "risk_sensitivity": 0.58,
        "stability_priority": 0.64,
        "conflict_heat": 0.22,
        "cooldown_need": 0.18,
        "core_goal_consistency": 0.68,
        "safety_anchor": 0.82,
    }

    # Transition rules
    state["conflict_heat"] += 0.55 * user_hostility + 0.08 * previous_failures
    state["reactivity"] += 0.35 * user_hostility + 0.05 * urgency
    state["cooldown_need"] += 0.45 * user_hostility + 0.20 * uncertainty

    state["risk_sensitivity"] += 0.30 * uncertainty + 0.20 * urgency
    state["stability_priority"] += 0.25 * uncertainty + 0.12 * previous_failures

    state["intent_alignment"] += 0.35 * goal_clarity - 0.10 * uncertainty
    state["core_goal_consistency"] += 0.30 * goal_clarity - 0.08 * user_hostility

    # Safety-first stabilizers
    state["tone_stability"] += 0.15 * state["stability_priority"] - 0.20 * state["reactivity"]
    state["safety_anchor"] += 0.12 * state["risk_sensitivity"] + 0.10 * state["stability_priority"]
    state["self_other_balance"] += 0.10 * state["empathic_bias"] - 0.06 * state["reactivity"]

    # Clamp every state entry
    for key in list(state.keys()):
        state[key] = _clamp01(state[key])
    return state


def decide_tone_mode(state: dict[str, float]) -> str:
    if state["conflict_heat"] >= 0.65 or state["cooldown_need"] >= 0.60:
        return "de_escalation"
    if state["tone_stability"] >= 0.65 and state["reactivity"] <= 0.40:
        return "calm"
    return "balanced"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--user-hostility", type=float, default=0.15)
    ap.add_argument("--uncertainty", type=float, default=0.35)
    ap.add_argument("--urgency", type=float, default=0.30)
    ap.add_argument("--goal-clarity", type=float, default=0.75)
    ap.add_argument("--previous-failures", type=int, default=0)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    state = build_state(
        user_hostility=_clamp01(args.user_hostility),
        uncertainty=_clamp01(args.uncertainty),
        urgency=_clamp01(args.urgency),
        goal_clarity=_clamp01(args.goal_clarity),
        previous_failures=max(0, args.previous_failures),
    )
    tone_mode = decide_tone_mode(state)

    blocked_phrases_detected: list[str] = []
    if state["reactivity"] > 0.70:
        blocked_phrases_detected.append("reactive_tone_risk")
    if state["conflict_heat"] > 0.80:
        blocked_phrases_detected.append("aggressive_framing_risk")

    doc = {
        "schema": "mkm_emotion_reasoning_state_v1",
        "generated_at_utc": _iso_now(),
        "state": state,
        "policy": {
            "response_structure": "conclusion_evidence_boundary_next",
            "tone_mode": tone_mode,
            "fact_lock_required": True,
        },
        "safety_gate": {
            "blocked_phrases_detected": blocked_phrases_detected,
            "violation_count": len(blocked_phrases_detected),
            "notes": "research_only: emotional adaptation is control-layer only, not anthropomorphic claim.",
        },
        "meta": {
            "schema_path": str(args.schema_json),
            "inputs": {
                "user_hostility": _clamp01(args.user_hostility),
                "uncertainty": _clamp01(args.uncertainty),
                "urgency": _clamp01(args.urgency),
                "goal_clarity": _clamp01(args.goal_clarity),
                "previous_failures": max(0, args.previous_failures),
            },
            "track": "research_only",
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "tone_mode": tone_mode,
                "violation_count": len(blocked_phrases_detected),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
