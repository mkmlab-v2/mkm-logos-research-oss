#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레짐별 전략 라우팅: 횡보장(Regime 0) 시 Mean Reversion, 추세장 시 Trend Following.

- TRANSITION / UNKNOWN + 저변동성 → use_mean_reversion True (역추세 신호 허용)
- CRISIS / VOLATILE / STABLE / TRENDING → use_mean_reversion False (기존 추세/돌파)
동적 앙상블 고도화 시 이 훅으로 분기.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 횡보로 간주할 레짐 (평균 회귀 전략 사용 후보)
SIDEWAYS_REGIMES = frozenset({"TRANSITION", "UNKNOWN"})
# 변동성 비율(현재/목표)이 이 값 이하면 '저변동성' 횡보
VOLATILITY_SIDEWAYS_CAP = 1.2


def use_mean_reversion(
    regime_type: Optional[str],
    volatility_ratio: Optional[float] = None,
) -> bool:
    """
    횡보장일 때 Mean Reversion 사용 여부.
    True면 변동성 돌파 대신 역추세(과매도 매수/과매수 매도) 신호를 허용.

    Args:
        regime_type: 모니터링 regime_type (CRISIS, VOLATILE, STABLE, TRENDING, TRANSITION, UNKNOWN)
        volatility_ratio: 현재 변동성/목표 변동성. None이면 레짐만으로 판단(TRANSITION/UNKNOWN이면 True)
    """
    rt = (regime_type or "UNKNOWN").strip().upper()
    if rt not in SIDEWAYS_REGIMES:
        return False
    if volatility_ratio is not None and volatility_ratio > VOLATILITY_SIDEWAYS_CAP:
        return False
    return True
