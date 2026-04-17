# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.5, M:0.5}
# Balance: 91
# Purpose: Detect local-time and solar-term boundary risks for saju verification.
# Keywords: saju, boundary, risk, review, dst, solar-term
"""Boundary risk guard for CONFIRMED/REVIEW gate decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from scripts.core.solar_term_ssot import SOLAR_TERM_DAY_APPROX


@dataclass(frozen=True)
class BoundaryInput:
    year: int
    month: int
    day: int
    hour: int
    minute: int


def evaluate_boundary_risks(inp: BoundaryInput) -> dict[str, Any]:
    dt = datetime(inp.year, inp.month, inp.day, inp.hour, inp.minute)
    minute_of_day = dt.hour * 60 + dt.minute
    reasons: list[str] = []

    # Zi boundary is one of the most common policy split points.
    if 23 * 60 - 30 <= minute_of_day <= 23 * 60 + 30 or minute_of_day <= 30:
        reasons.append("near_zi_boundary_window")

    # Near 2-hour branch boundaries (03:00, 05:00, ...).
    branch_boundaries = [60, 180, 300, 420, 540, 660, 780, 900, 1020, 1140, 1260, 1380]
    for boundary in branch_boundaries:
        if abs(minute_of_day - boundary) <= 10:
            reasons.append("near_branch_boundary_window")
            break

    # Solar-term anchor day proximity (fallback engine boundary).
    anchor_day = int(SOLAR_TERM_DAY_APPROX.get(inp.month, 1))
    if abs(inp.day - anchor_day) <= 1:
        reasons.append("near_solar_term_anchor_day")

    return {
        "is_boundary_risk": len(reasons) > 0,
        "reasons": reasons,
        "meta": {
            "solar_term_anchor_day_approx": anchor_day,
            "branch_boundary_window_minutes": 10,
            "zi_boundary_window_minutes": 30,
        },
    }

