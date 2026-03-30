#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레짐·0.25 기반 리스크 정책 (1차 실물 레짐만 사용)

- primary_regime(실물 TE 국면) + divine_distance(0.25 centroid 거리) → macro_risk_level (0~1)
- 2차 성경 레짐은 리스크/포지션/트리거에 사용 금지 (해설·경고 전용)

참조: docs/final/헌법_이론_0.25_업데이트_할일_리스트_2026-03-08.md, regime-field-constitution
"""
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 1차 레짐(모니터링 regime_type)별 기본 리스크 수준 (0.0=안전, 1.0=최대 보수)
REGIME_BASE_RISK: dict = {
    "CRISIS": 0.85,
    "VOLATILE": 0.60,
    "TRANSITION": 0.40,
    "STABLE": 0.10,
    "TRENDING": 0.10,
    "UNKNOWN": 0.50,
}

# Divine Distance 구간별 가산 (0.25에서 멀수록 리스크 상향)
# 구간: (미만, 가산치) — 예: (0.15, 0), (0.30, 0.15), (0.50, 0.25), (inf, 0.35)
DIVINE_DISTANCE_BANDS: list = [
    (0.15, 0.0),
    (0.30, 0.15),
    (0.50, 0.25),
    (float("inf"), 0.35),
]


def get_regime_risk_level(
    primary_regime: Optional[str],
    divine_distance: Optional[float],
) -> float:
    """
    1차 레짐 + Divine Distance로 macro_risk_level (0.0~1.0) 계산.
    RiskManager.apply_macro_regime(level)에 그대로 전달 가능.

    Args:
        primary_regime: 모니터링 regime_type (CRISIS, VOLATILE, STABLE, TRENDING, TRANSITION, UNKNOWN)
        divine_distance: 전략의 centroid 거리 (None이면 거리 보정 없음)

    Returns:
        0.0~1.0 리스크 수준 (높을수록 포지션/일일손실 축소)
    """
    base = REGIME_BASE_RISK.get(
        (primary_regime or "").strip().upper() or "UNKNOWN",
        REGIME_BASE_RISK["UNKNOWN"],
    )
    boost = 0.0
    if divine_distance is not None:
        try:
            d = float(divine_distance)
            for threshold, add in DIVINE_DISTANCE_BANDS:
                if d < threshold:
                    boost = add
                    break
        except (TypeError, ValueError):
            pass
    level = min(1.0, base + boost)
    return max(0.0, level)


def get_regime_risk_params(
    primary_regime: Optional[str],
    divine_distance: Optional[float],
) -> Tuple[float, str]:
    """
    리스크 수준과 설명 문자열 반환 (로깅/디버깅용).

    Returns:
        (macro_risk_level, description)
    """
    level = get_regime_risk_level(primary_regime, divine_distance)
    regime_label = (primary_regime or "UNKNOWN").strip() or "UNKNOWN"
    dd_label = f"{divine_distance:.3f}" if divine_distance is not None else "N/A"
    desc = f"regime={regime_label}, dd={dd_label} → risk_level={level:.2f}"
    return level, desc
