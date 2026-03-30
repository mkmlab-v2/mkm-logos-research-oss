#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.3, L:0.6, K:0.7, M:0.4}
# Balance: 83
# Purpose: 글로벌 유동성 로더를 감싸 트레이딩 전략에서 바로 사용할 수 있는 feature vector를 제공한다.
# Keywords: global liquidity, feature engine, exogenous, macro

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import logging

from src.data.global_liquidity_loader import GlobalLiquidityLoader, GlobalLiquidityPoint

logger = logging.getLogger(__name__)


@dataclass
class GlobalLiquidityFeature:
    """전략에서 바로 사용할 수 있는 글로벌 유동성 피처 래퍼."""

    as_of: date
    features: Dict[str, float]


class GlobalLiquidityFeatureEngine:
    """
    GlobalLiquidityLoader 위에 얇은 래퍼를 올려,
    전략 레이어에서 날짜 기반으로 feature vector를 간단히 조회할 수 있게 해준다.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.loader = GlobalLiquidityLoader(workspace_root=workspace_root)
        self._loaded: bool = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.loader.load()
            self._loaded = True

    def get_feature_for_date(self, d: date) -> Optional[GlobalLiquidityFeature]:
        """
        특정 날짜의 글로벌 유동성 피처를 반환한다.

        Args:
            d: 조회 날짜

        Returns:
            GlobalLiquidityFeature 또는 데이터가 없으면 None
        """
        self._ensure_loaded()
        point: Optional[GlobalLiquidityPoint] = self.loader.get_features_for_date(d)
        if point is None:
            logger.debug("GlobalLiquidityFeatureEngine: 날짜 %s 에 대한 유동성 데이터 없음", d)
            return None
        return GlobalLiquidityFeature(as_of=point.as_of, features=point.features)

    def is_m2_contraction(
        self, as_of: date, lookback_days: int = 35
    ) -> Tuple[bool, str]:
        """
        as_of 시점에서 M2(미국) 수축 구간 여부를 판별한다.
        (현재 시점 m2_us < lookback_days 전 m2_us 이면 수축으로 간주)

        Returns:
            (True, reason) 수축이면 롱 차단 권장
            (False, "") 수축 아님 또는 데이터 부재로 판단 보류
        """
        self._ensure_loaded()
        past = as_of - timedelta(days=lookback_days)
        point_now = self.loader.get_features_for_latest_on_or_before(as_of)
        point_past = self.loader.get_features_for_latest_on_or_before(past)
        if point_now is None or point_past is None:
            return False, ""
        m2_now = point_now.features.get("m2_us")
        m2_past = point_past.features.get("m2_us")
        if m2_now is None or m2_past is None:
            return False, ""
        if m2_now < m2_past:
            return True, (
                f"FRED M2 수축 구간 (as_of={point_now.as_of} m2_us={m2_now:.2f} vs "
                f"{point_past.as_of} m2_us={m2_past:.2f})"
            )
        return False, ""


__all__ = ["GlobalLiquidityFeatureEngine", "GlobalLiquidityFeature"]

