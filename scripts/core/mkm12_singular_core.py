"""MKM12 singular core scoring contract."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "mkm12_singular_core_v1"
GRID = 0.25
# Default threshold tuned for current A-track governance operation.
# Can still be overridden via MKM_SINGULAR_CORE_THRESHOLD.
THRESHOLD = 0.2


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


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
    grid = _env_float("MKM_SINGULAR_CORE_GRID", GRID)
    if grid <= 0:
        grid = GRID
    threshold = _env_float("MKM_SINGULAR_CORE_THRESHOLD", THRESHOLD)
    threshold = _clamp(threshold, 0.0, 1.0)

    s = _normalize_01(core_input.s)
    l = _normalize_01(core_input.l)
    k = _normalize_01(core_input.k)
    m = _normalize_01(core_input.m)
    weighted = (s * 0.25) + (l * 0.35) + (k * 0.20) + (m * 0.20)
    raw_score = _clamp((weighted - 0.5) / 0.5, -1.0, 1.0)
    grid_score = _clamp(round_to_grid(raw_score, grid), -1.0, 1.0)

    if grid_score >= threshold:
        decision = "PASS_LONG"
        reason = "score_above_long_threshold"
    elif grid_score <= -threshold:
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
        "grid": grid,
        "threshold": threshold,
        "contract_version": CONTRACT_VERSION,
        "inputs": {"S": s, "L": l, "K": k, "M": m},
    }
