#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Enhanced Risk Manager (강화된 리스크 관리)

실행 레이어 강화:
- 슬리피지 제어
- 동적 포지션 크기 조정
- 변동성 기반 리스크 관리
- 자금 관리 최적화

작성일: 2026-02-14
버전: v1.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class EnhancedRiskManager:
    """
    강화된 리스크 관리 시스템
    
    기능:
    - 슬리피지 제어
    - 동적 포지션 크기 조정 (변동성 기반)
    - 자금 관리 최적화
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        base_max_position_size: float = 0.15,  # 기본 최대 포지션 크기 (15%)
        max_slippage: float = 0.001,  # 최대 슬리피지 (0.1%)
        volatility_window: int = 20  # 변동성 계산 윈도우
    ):
        """
        Args:
            initial_capital: 초기 자본
            base_max_position_size: 기본 최대 포지션 크기
            max_slippage: 최대 슬리피지 허용치
            volatility_window: 변동성 계산 윈도우
        """
        self.initial_capital = initial_capital
        self.base_max_position_size = base_max_position_size
        self.max_slippage = max_slippage
        self.volatility_window = volatility_window
        
        # 변동성 추적
        self.price_history = []
        self.current_volatility = 0.0
        
        logger.info("✅ Enhanced Risk Manager 초기화 완료")
    
    def calculate_dynamic_position_size(
        self,
        current_price: float,
        confidence: float,
        volatility: Optional[float] = None
    ) -> float:
        """
        동적 포지션 크기 계산 (변동성 기반)
        
        Args:
            current_price: 현재 가격
            confidence: 신뢰도
            volatility: 변동성 (None이면 자동 계산)
        
        Returns:
            포지션 크기 비율 (0.0 ~ base_max_position_size)
        """
        try:
            # 변동성 계산
            if volatility is None:
                volatility = self.current_volatility
                if volatility == 0.0 and len(self.price_history) >= 2:
                    # 가격 히스토리에서 변동성 계산
                    prices = np.array(self.price_history[-self.volatility_window:])
                    returns = np.diff(prices) / prices[:-1]
                    volatility = np.std(returns) if len(returns) > 0 else 0.0
            
            # 변동성 기반 조정
            # 높은 변동성 → 작은 포지션
            # 낮은 변동성 → 큰 포지션
            volatility_factor = max(0.5, min(1.5, 1.0 / (1.0 + volatility * 10)))
            
            # 신뢰도 기반 조정
            confidence_factor = confidence  # 신뢰도 그대로 사용
            
            # 최종 포지션 크기
            position_size = self.base_max_position_size * volatility_factor * confidence_factor
            
            # 상한/하한 제한
            position_size = max(0.05, min(position_size, self.base_max_position_size))
            
            logger.debug(
                f"📊 동적 포지션 크기: {position_size:.2%} "
                f"(변동성: {volatility:.4f}, 신뢰도: {confidence:.2%})"
            )
            
            return position_size
            
        except Exception as e:
            logger.warning(f"⚠️ 동적 포지션 크기 계산 실패: {e}, 기본값 사용")
            return self.base_max_position_size * confidence
    
    def check_slippage(
        self,
        expected_price: float,
        actual_price: float
    ) -> Dict[str, Any]:
        """
        슬리피지 확인 및 제어
        
        Args:
            expected_price: 예상 가격
            actual_price: 실제 가격
        
        Returns:
            슬리피지 정보 및 허용 여부
        """
        try:
            if expected_price == 0:
                return {
                    "slippage": 0.0,
                    "slippage_ratio": 0.0,
                    "is_acceptable": True,
                    "message": "가격 정보 없음"
                }
            
            slippage = abs(actual_price - expected_price)
            slippage_ratio = slippage / expected_price
            
            is_acceptable = slippage_ratio <= self.max_slippage
            
            result = {
                "slippage": slippage,
                "slippage_ratio": slippage_ratio,
                "is_acceptable": is_acceptable,
                "message": "슬리피지 허용" if is_acceptable else f"슬리피지 초과: {slippage_ratio:.4%} > {self.max_slippage:.4%}"
            }
            
            if not is_acceptable:
                logger.warning(
                    f"⚠️ 슬리피지 초과: {slippage_ratio:.4%} > {self.max_slippage:.4%} "
                    f"(예상: {expected_price:.2f}, 실제: {actual_price:.2f})"
                )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 슬리피지 확인 실패: {e}")
            return {
                "slippage": 0.0,
                "slippage_ratio": 0.0,
                "is_acceptable": True,
                "message": f"슬리피지 확인 실패: {e}"
            }
    
    def update_price_history(self, price: float):
        """가격 히스토리 업데이트 (변동성 계산용)"""
        try:
            self.price_history.append(price)
            
            # 윈도우 크기 제한
            if len(self.price_history) > self.volatility_window * 2:
                self.price_history = self.price_history[-self.volatility_window:]
            
            # 변동성 업데이트
            if len(self.price_history) >= 2:
                prices = np.array(self.price_history[-self.volatility_window:])
                returns = np.diff(prices) / prices[:-1]
                self.current_volatility = np.std(returns) if len(returns) > 0 else 0.0
            
        except Exception as e:
            logger.debug(f"가격 히스토리 업데이트 실패: {e}")
    
    def calculate_optimal_capital_allocation(
        self,
        current_balance: float,
        confidence: float,
        volatility: Optional[float] = None
    ) -> Dict[str, float]:
        """
        최적 자금 배분 계산
        
        Args:
            current_balance: 현재 잔고
            confidence: 신뢰도
            volatility: 변동성
        
        Returns:
            자금 배분 정보
        """
        try:
            # 동적 포지션 크기 계산
            position_size_ratio = self.calculate_dynamic_position_size(
                current_price=0.0,  # 가격은 필요 없음
                confidence=confidence,
                volatility=volatility
            )
            
            # 포지션 크기
            position_size = current_balance * position_size_ratio
            
            # 현금 보유
            cash_reserve = current_balance - position_size
            
            # 리스크 자본 (손절 대비)
            risk_capital = position_size * 0.1  # 포지션의 10%를 리스크 자본으로
            
            return {
                "total_balance": current_balance,
                "position_size": position_size,
                "position_size_ratio": position_size_ratio,
                "cash_reserve": cash_reserve,
                "risk_capital": risk_capital,
                "volatility": volatility or self.current_volatility,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 자금 배분 계산 실패: {e}")
            return {
                "total_balance": current_balance,
                "position_size": current_balance * self.base_max_position_size,
                "position_size_ratio": self.base_max_position_size,
                "cash_reserve": current_balance * (1 - self.base_max_position_size),
                "risk_capital": 0.0,
                "volatility": 0.0,
                "confidence": confidence
            }
    
    def validate_trade_execution(
        self,
        signal: str,
        expected_price: float,
        actual_price: float,
        confidence: float,
        position_size: float,
        current_balance: float
    ) -> Dict[str, Any]:
        """
        거래 실행 검증 (종합)
        
        Args:
            signal: 매매 신호
            expected_price: 예상 가격
            actual_price: 실제 가격
            confidence: 신뢰도
            position_size: 포지션 크기
            current_balance: 현재 잔고
        
        Returns:
            검증 결과
        """
        try:
            # 1. 슬리피지 확인
            slippage_check = self.check_slippage(expected_price, actual_price)
            
            # 2. 포지션 크기 확인
            max_position = current_balance * self.base_max_position_size
            position_size_valid = position_size <= max_position
            
            # 3. 신뢰도 확인
            min_confidence = 0.5  # 최소 신뢰도
            confidence_valid = confidence >= min_confidence
            
            # 4. 종합 검증
            is_valid = (
                slippage_check["is_acceptable"] and
                position_size_valid and
                confidence_valid
            )
            
            result = {
                "is_valid": is_valid,
                "slippage_check": slippage_check,
                "position_size_valid": position_size_valid,
                "confidence_valid": confidence_valid,
                "issues": []
            }
            
            if not slippage_check["is_acceptable"]:
                result["issues"].append(f"슬리피지 초과: {slippage_check['slippage_ratio']:.4%}")
            if not position_size_valid:
                result["issues"].append(f"포지션 크기 초과: {position_size:.2f} > {max_position:.2f}")
            if not confidence_valid:
                result["issues"].append(f"신뢰도 부족: {confidence:.2%} < {min_confidence:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 거래 실행 검증 실패: {e}")
            return {
                "is_valid": False,
                "slippage_check": {"is_acceptable": False},
                "position_size_valid": False,
                "confidence_valid": False,
                "issues": [f"검증 실패: {e}"]
            }

