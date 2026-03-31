"""MKM12 singular core scoring contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "mkm12_singular_core_v1"
GRID = 0.25
THRESHOLD = 0.75


@dataclass(frozen=True)
class CoreInput:
    s: float
    l: float
    k: float
    m: float


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def round_to_grid(v: float, grid: float = GRID) -> float:
    if grid <= 0:
        return v
    return round(v / grid) * grid


def _normalize_01(v: float) -> float:
    return _clamp(v, 0.0, 1.0)


def compute_core_score(core_input: CoreInput) -> dict[str, Any]:
    s = _normalize_01(core_input.s)
    l = _normalize_01(core_input.l)
    k = _normalize_01(core_input.k)
    m = _normalize_01(core_input.m)
    weighted = (s * 0.25) + (l * 0.35) + (k * 0.20) + (m * 0.20)
    raw_score = _clamp((weighted - 0.5) / 0.5, -1.0, 1.0)
    grid_score = _clamp(round_to_grid(raw_score), -1.0, 1.0)

    if grid_score >= THRESHOLD:
        decision = "PASS_LONG"
        reason = "score_above_long_threshold"
    elif grid_score <= -THRESHOLD:
        decision = "PASS_SHORT"
        reason = "score_below_short_threshold"
    else:
        decision = "HOLD"
        reason = "score_inside_locked_band"

    return {
        "score_raw": round(raw_score, 6),
        "score_grid": round(grid_score, 6),
        "decision": decision,
        "reason": reason,
        "grid": GRID,
        "threshold": THRESHOLD,
        "contract_version": CONTRACT_VERSION,
        "inputs": {"S": s, "L": l, "K": k, "M": m},
    }
