"""B-track min-confidence gate: bull/bear -> neutral when confidence below threshold."""

from __future__ import annotations

import os
from typing import Any


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def min_direction_confidence_threshold(rules: dict[str, Any] | None = None) -> float:
    env = os.environ.get("MKM_BTRACK_MIN_DIRECTION_CONFIDENCE", "").strip()
    if env:
        return max(0.0, min(1.0, _safe_float(env, 0.25)))
    rules = rules or {}
    return max(0.0, min(1.0, _safe_float(rules.get("min_direction_confidence"), 0.25)))


def apply_min_direction_confidence_gate(
    direction: str,
    confidence: float,
    *,
    rules: dict[str, Any] | None = None,
) -> tuple[str, float, dict[str, Any]]:
    """If directional call confidence is below threshold, emit neutral (no-call)."""
    thresh = min_direction_confidence_threshold(rules)
    d = str(direction or "").strip().lower()
    conf = max(0.0, min(1.0, _safe_float(confidence, 0.0)))
    if d in ("bull", "bear") and conf < thresh:
        return (
            "neutral",
            conf,
            {
                "applied": True,
                "threshold": round(thresh, 6),
                "prior_direction": d,
                "reason": "below_min_direction_confidence",
            },
        )
    return (
        d if d in ("bull", "bear", "neutral", "abstain") else "neutral",
        conf,
        {"applied": False, "threshold": round(thresh, 6)},
    )
