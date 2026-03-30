#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.3, L:0.6, K:0.7, M:0.4}
# Balance: 82
# Purpose: TimeXer-Exog 스타일 시계열 + 외생 변수 예측 모델의 스켈레톤. 학습/예측 인터페이스를 정의하고, 초기에는 단순 베이스라인만 제공한다.
# Keywords: timexer, exogenous, time series, model, skeleton

"""
TimeXer-Exog Model Skeleton

역할:
- 가격 시계열 + 글로벌 유동성/매크로 피처(외생 변수)를 함께 사용하는 예측 모델의
  인터페이스를 정의한다.
- 현재 단계에서는 "스켈레톤 + 단순 베이스라인"만 제공하며, 실제 TimeXer-Exog 아키텍처
  구현 및 GPU 학습 로직은 후속 Phase에서 확장한다.

주의:
- 이 모듈은 어떤 포지션/주문도 직접 실행하지 않는다.
- CryptoNitroLiveStrategy 등에서 선택적으로 불러 사용 가능하도록 설계한다.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TimeXerExogConfig:
    """
    TimeXer-Exog 모델 설정 값.

    - input_window: 입력으로 사용할 과거 시점 개수 (예: 64일)
    - forecast_horizon: 예측할 미래 시점 (예: 1일 앞)
    - target_col: 예측 대상 컬럼명 (예: 'future_return', 'direction')
    - exogenous_cols: 외생 변수(매크로/유동성) 컬럼명 리스트
    - direction_labels: 방향 분류 태그 (예: ['DOWN', 'HOLD', 'UP'])
    """

    input_window: int = 64
    forecast_horizon: int = 1
    target_col: str = "future_return"
    exogenous_cols: Tuple[str, ...] = ()
    direction_labels: Tuple[str, ...] = ("DOWN", "HOLD", "UP")


class TimeXerExogModel:
    """
    TimeXer-Exog 스타일 모델 스켈레톤.

    현재 단계:
    - fit() / predict() 인터페이스만 정의
    - predict()는 매우 단순한 베이스라인(최근 수익률 기준)만 사용
    - 이후 Phase에서 PyTorch/TimeXer 아키텍처를 이 클래스 안에 탑재할 예정
    """

    def __init__(self, config: Optional[TimeXerExogConfig] = None) -> None:
        self.config = config or TimeXerExogConfig()
        self._is_trained: bool = False
        # 베이스라인 통계를 저장 (예: 평균/표준편차 등)
        self._baseline_stats: Dict[str, Any] = {}

        logger.info("TimeXerExogModel 초기화 완료: %s", asdict(self.config))

    @property
    def is_trained(self) -> bool:
        """
        모델이 학습 상태인지 여부.

        현재 구현에서는 베이스라인 통계가 존재할 때 True로 간주한다.
        """

        return self._is_trained

    def fit(self, df: pd.DataFrame) -> None:
        """
        간단한 베이스라인 학습.

        설계:
        - target_col(예: 미래 수익률)에 대한 평균/표준편차 등을 계산해 저장한다.
        - TimeXer-Exog 아키텍처 구현 시 이 메서드를 실제 학습 로직으로 교체한다.
        """

        cfg = self.config
        if cfg.target_col not in df.columns:
            logger.warning(
                "TimeXerExogModel.fit: target_col=%s 이 데이터프레임에 없습니다. 베이스라인 학습 스킵.",
                cfg.target_col,
            )
            self._baseline_stats = {}
            self._is_trained = False
            return

        target = pd.to_numeric(df[cfg.target_col], errors="coerce").dropna()
        if target.empty:
            logger.warning("TimeXerExogModel.fit: target_col=%s 유효 값이 없습니다.", cfg.target_col)
            self._baseline_stats = {}
            self._is_trained = False
            return

        mean = float(target.mean())
        std = float(target.std(ddof=0)) if len(target) > 1 else 0.0
        self._baseline_stats = {"mean": mean, "std": std}
        self._is_trained = True

        logger.info(
            "TimeXerExogModel 베이스라인 학습 완료: target_mean=%.6f, target_std=%.6f, rows=%d",
            mean,
            std,
            len(target),
        )

    def _direction_from_return(self, r: float) -> str:
        """
        미래 수익률을 방향 레이블로 변환하는 간단한 규칙.

        - r > +th → 'UP'
        - r < -th → 'DOWN'
        - 사이 → 'HOLD'
        """

        labels = self.config.direction_labels
        if len(labels) != 3:
            # 방어적: 예상과 다른 설정이면 HOLD만 반환
            return "HOLD"

        # 임계값은 베이스라인 표준편차의 배수로 계산, 최소 0.001
        std = float(self._baseline_stats.get("std", 0.0) or 0.0)
        threshold = max(0.001, std * 0.5)

        if r > threshold:
            return labels[2]  # 'UP'
        if r < -threshold:
            return labels[0]  # 'DOWN'
        return labels[1]  # 'HOLD'

    def predict_one(
        self,
        window_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        단일 윈도우에 대한 예측.

        현재 구현:
        - window_df의 마지막 행과 첫 행의 close를 사용해 단순 수익률을 계산.
        - _direction_from_return()으로 방향 레이블을 생성.
        - confidence는 |r|의 크기를 기반으로 0.0~1.0 구간으로 정규화한 값으로 제공.
        """

        if window_df.empty:
            return {"signal": "HOLD", "confidence": 0.0}

        # close 컬럼이 없으면 HOLD
        if "close" not in window_df.columns:
            return {"signal": "HOLD", "confidence": 0.0}

        w = window_df["close"].astype(float)
        start_price = float(w.iloc[0])
        end_price = float(w.iloc[-1])
        if start_price <= 0.0:
            return {"signal": "HOLD", "confidence": 0.0}

        r = (end_price - start_price) / start_price
        direction = self._direction_from_return(r)

        # confidence: 수익률 절댓값을 0~1로 스케일 (기본적으로 5% 이상이면 1.0 근처)
        confidence = min(1.0, float(abs(r) / 0.05))

        return {
            "signal": direction,
            "confidence": confidence,
            "window_return": r,
        }

    def predict_sequence(
        self,
        df: pd.DataFrame,
        price_col: str = "close",
    ) -> List[Dict[str, Any]]:
        """
        전체 시계열에 대해 슬라이딩 윈도우 방식으로 예측.

        Args:
            df: 시간 순으로 정렬된 가격/피처 DataFrame.
            price_col: 종가 컬럼명 (기본 'close').

        Returns:
            각 시점별 예측 결과 리스트 (마지막 window 기준).
        """

        cfg = self.config
        if df.empty:
            return []

        if price_col not in df.columns:
            logger.warning("TimeXerExogModel.predict_sequence: price_col=%s 이 없습니다.", price_col)
            return []

        results: List[Dict[str, Any]] = []
        n = len(df)
        win = cfg.input_window
        if n < win:
            # 윈도우보다 짧으면 전체를 하나의 윈도우로 보고 예측
            res = self.predict_one(df)
            results.append(res)
            return results

        for end_idx in range(win, n + 1):
            window = df.iloc[end_idx - win : end_idx]
            res = self.predict_one(window)
            results.append(res)

        return results


__all__ = ["TimeXerExogConfig", "TimeXerExogModel"]

