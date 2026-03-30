#!/usr/bin/env python3
"""W3 auxiliary adapter (B-track only, non-gating).

This adapter ports a *minimal* subset of trading-path ideas into W3 as
auxiliary metadata only. The returned values MUST NOT be used for ranking,
promotion gates, or A-track claims.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuxMacroSignal:
    geumhwa_aux_score: float
    transition_pressure: float


@dataclass(frozen=True)
class AuxPersonalSignal:
    bomyeong_guard_score: float
    taeyang_risk_flag: bool


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_aux_macro_signal(*, state_id: int, logos_ref: str, cycle: str) -> AuxMacroSignal:
    """Compute macro auxiliary signal without side effects.

    Notes:
    - This is a deterministic heuristic adapter.
    - It is intentionally shallow and does not replace W3 scoring.
    """
    sid = int(state_id or 0)
    state_anchor = 1.0 if sid == 13 else (0.7 if sid in {8, 4} else 0.4)
    symbol_anchor = 1.0 if logos_ref else 0.0
    cycle_anchor = 1.0 if cycle else 0.0
    geumhwa_aux_score = _clamp01((0.55 * state_anchor) + (0.30 * symbol_anchor) + (0.15 * cycle_anchor))
    transition_pressure = _clamp01(abs(13 - sid) / 13.0)
    return AuxMacroSignal(
        geumhwa_aux_score=round(geumhwa_aux_score, 6),
        transition_pressure=round(transition_pressure, 6),
    )


def compute_aux_personal_signal(*, sasang_type: str, state_candidate_id: int | None) -> AuxPersonalSignal:
    """Compute personal auxiliary signal without side effects."""
    st = (sasang_type or "").strip().lower()
    taeyang = st == "tae_yang"
    sid = int(state_candidate_id) if state_candidate_id is not None else 0
    # Guard score grows when taeyang profile is matched with its pilot anchor.
    anchor_match = 1.0 if sid == 13 else (0.6 if sid in {8, 4} else 0.3)
    base = 0.45 if taeyang else 0.35
    bomyeong_guard_score = _clamp01(base + (0.4 * anchor_match))
    taeyang_risk_flag = taeyang and sid == 13
    return AuxPersonalSignal(
        bomyeong_guard_score=round(bomyeong_guard_score, 6),
        taeyang_risk_flag=taeyang_risk_flag,
    )
