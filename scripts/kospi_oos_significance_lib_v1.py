#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI OOS binomial significance — Wilson / Wald / Clopper-Pearson [HYPO]."""

from __future__ import annotations

import math
from typing import Any

Z_95 = 1.959963984540054


def wald_ci(k: int, n: int, *, z: float = Z_95) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    margin = z * math.sqrt(p * (1.0 - p) / n)
    return (max(0.0, p - margin), min(1.0, p + margin))


def wilson_ci(k: int, n: int, *, z: float = Z_95) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
    return (max(0.0, center - half), min(1.0, center + half))


def clopper_pearson_ci(k: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial (Clopper-Pearson) via bracket search — stable for small n."""
    if n <= 0:
        return (0.0, 0.0)
    half = alpha / 2.0
    if k == 0:
        lo = 0.0
    else:
        # lower: P(X >= k | p) = alpha/2
        lo = _cp_solve_tail_ge(k, n, half)
    if k == n:
        hi = 1.0
    else:
        # upper: P(X >= k+1 | p) = 1 - alpha/2
        hi = _cp_solve_tail_ge(k + 1, n, 1.0 - half)
    return (max(0.0, lo), min(1.0, hi))


def _binom_tail_le(k_obs: int, n: int, p: float) -> float:
    return sum(math.comb(n, x) * (p**x) * ((1.0 - p) ** (n - x)) for x in range(0, k_obs + 1))


def _binom_tail_ge(k_obs: int, n: int, p: float) -> float:
    return sum(math.comb(n, x) * (p**x) * ((1.0 - p) ** (n - x)) for x in range(k_obs, n + 1))


def _cp_solve_tail_ge(k_thresh: int, n: int, target: float) -> float:
    """Solve p such that P(X >= k_thresh | p) = target (monotone increasing in p)."""
    lo_p, hi_p = 0.0, 1.0
    for _ in range(64):
        mid = (lo_p + hi_p) / 2.0
        tail = _binom_tail_ge(k_thresh, n, mid)
        if tail > target:
            hi_p = mid
        else:
            lo_p = mid
    return (lo_p + hi_p) / 2.0


def binomial_two_sided_p(k: int, n: int, p0: float = 0.5) -> float:
    if n <= 0:
        return 1.0
    tail_lo = sum(
        math.comb(n, x) * (p0**x) * ((1.0 - p0) ** (n - x)) for x in range(0, k + 1)
    )
    tail_hi = sum(
        math.comb(n, x) * (p0**x) * ((1.0 - p0) ** (n - x)) for x in range(k, n + 1)
    )
    return min(1.0, 2.0 * min(tail_lo, tail_hi))


def binomial_greater_p(k: int, n: int, p0: float = 0.5) -> float:
    """One-sided P[X >= k] under Binomial(n, p0)."""
    if n <= 0:
        return 1.0
    return sum(
        math.comb(n, x) * (p0**x) * ((1.0 - p0) ** (n - x)) for x in range(k, n + 1)
    )


def significance_block(
    *,
    label: str,
    successes: float,
    n: int,
    null_p: float = 0.5,
    z: float = Z_95,
) -> dict[str, Any]:
    """successes may be fractional for soft metric (use rounded k for CIs)."""
    k_int = int(round(successes))
    rate = successes / n if n else None
    w_lo, w_hi = wald_ci(k_int, n, z=z)
    wil_lo, wil_hi = wilson_ci(k_int, n, z=z)
    cp_lo, cp_hi = clopper_pearson_ci(k_int, n)
    contains_null = wil_lo <= null_p <= wil_hi
    return {
        "label": label,
        "n": n,
        "successes": successes,
        "successes_rounded_for_ci": k_int,
        "rate": round(rate, 6) if rate is not None else None,
        "null_hypothesis_p": null_p,
        "wald_95_ci": [round(w_lo, 4), round(w_hi, 4)],
        "wilson_95_ci": [round(wil_lo, 4), round(wil_hi, 4)],
        "clopper_pearson_95_ci": [round(cp_lo, 4), round(cp_hi, 4)],
        "null_inside_wilson_ci": contains_null,
        "reject_h0_p_equals_null_two_sided_005": not contains_null,
        "binom_two_sided_p": round(binomial_two_sided_p(k_int, n, null_p), 6) if n else None,
        "binom_one_sided_p_ge_observed": round(binomial_greater_p(k_int, n, null_p), 6) if n else None,
        "verdict_ko": (
            f"H0:p={null_p} 기각 실패 — Wilson CI가 {null_p} 포함 (우연과 구별 불가)"
            if contains_null
            else f"H0:p={null_p} 기각 가능 — Wilson CI가 {null_p} 미포함"
        ),
    }


def metrics_from_eval_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in rows if isinstance(r, dict) and r.get("outcome")]
    hits = sum(1 for r in scored if r.get("outcome") == "HIT")
    fails = sum(1 for r in scored if r.get("outcome") == "FAIL")
    neutral = sum(1 for r in scored if r.get("outcome") == "NEUTRAL_DRAW")
    n_dir = hits + fails
    soft_successes = hits + 0.5 * neutral
    bull_pred_bear = sum(
        1
        for r in scored
        if r.get("outcome") == "FAIL"
        and str(r.get("predicted_direction") or "").lower() == "bull"
        and str(r.get("actual_direction") or "").lower() == "bear"
    )
    return {
        "n_scored": len(scored),
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "n_directional_bets": n_dir,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round(soft_successes / len(scored), 4) if scored else None,
        "soft_successes": soft_successes,
        "fail_bull_pred_bear_actual": bull_pred_bear,
        "fail_pattern_ko": (
            f"FAIL {fails}건 중 bull→bear {bull_pred_bear}건"
            if fails
            else "no_fail_days"
        ),
    }
