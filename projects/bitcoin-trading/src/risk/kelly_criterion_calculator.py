#!/usr/bin/env python3
"""
Kelly Criterion 기반 포지션 사이징

비대칭 켈리 공식:
f* = ((p × b) - (q × loss)) / (b × loss)

여기서:
- f*: 최적 포지션 비율 (자본 대비)
- p: 승률
- b: 익절 시 수익률
- q: 패율 (1-p)
- loss: 손절 시 손실률

MKM12 수학 헌법 v4.0 준수:
- 헌법 제6장 Kelly Criterion 제24-27공식
- Divine Centroid (0.25 평형) 신뢰도 보정 적용
"""
import numpy as np
import math
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MKM12 수학 헌법 v4.0 준수: Divine Centroid (Project Logos)
# 헌법 제5장 Divine Centroid 제20공식
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}


class KellyCriterionCalculator:
    """
    Kelly Criterion 기반 포지션 사이징
    
    MKM12 수학 헌법 v4.0 준수:
    - 헌법 제6장 Kelly Criterion 제24-27공식
    - Divine Centroid (0.25 평형) 신뢰도 보정 적용
    """
    
    def __init__(self, min_kelly: float = 0.0, max_kelly: float = 1.0):
        """
        Args:
            min_kelly: 최소 켈리 비율 (기본값: 0.0)
            max_kelly: 최대 켈리 비율 (기본값: 1.0, 100% 제한)
        """
        self.min_kelly = min_kelly
        self.max_kelly = max_kelly
    
    def calculate_full_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        풀 켈리 비율 계산
        
        Args:
            win_rate: 승률 (0.0-1.0)
            avg_win: 평균 수익률 (예: 0.10 for 10%)
            avg_loss: 평균 손실률 (예: 0.05 for 5%)
        
        Returns:
            최적 포지션 비율 (자본 대비, 0.0-1.0)
        """
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"⚠️ 승률이 범위를 벗어났습니다: {win_rate}")
            return 0.0
        
        if avg_win <= 0 or avg_loss <= 0:
            logger.warning(f"⚠️ 손익비가 유효하지 않습니다: win={avg_win}, loss={avg_loss}")
            return 0.0
        
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss  # 손익비
        
        # 비대칭 켈리 공식
        numerator = (p * avg_win) - (q * avg_loss)
        denominator = avg_win * avg_loss
        
        if denominator <= 0:
            logger.warning(f"⚠️ 분모가 0 이하입니다: {denominator}")
            return 0.0
        
        f_star = numerator / denominator
        
        # 음수 켈리 = 거래하지 않음
        if f_star < 0:
            logger.info(f"ℹ️ 켈리 비율이 음수입니다 ({f_star:.4f}), 거래하지 않습니다")
            return 0.0
        
        # 범위 제한
        f_star = max(self.min_kelly, min(f_star, self.max_kelly))
        
        logger.info(
            f"📊 Kelly Criterion 계산: "
            f"승률={p:.1%}, 익절={avg_win:.1%}, 손절={avg_loss:.1%}, "
            f"켈리 비율={f_star:.2%}"
        )
        
        return f_star
    
    def calculate_fractional_kelly(
        self,
        full_kelly: float,
        fraction: float = 0.25
    ) -> float:
        """
        부분 켈리 (Fractional Kelly)
        
        Args:
            full_kelly: 풀 켈리 비율
            fraction: 켈리 비율 (0.25 = Quarter-Kelly, 0.5 = Half-Kelly)
        
        Returns:
            부분 켈리 비율
        """
        fractional = full_kelly * fraction
        
        logger.info(
            f"📊 Fractional Kelly: "
            f"풀 켈리={full_kelly:.2%}, "
            f"비율={fraction:.0%}, "
            f"최종={fractional:.2%}"
        )
        
        return fractional
    
    def calculate_volatility_adjusted_kelly(
        self,
        kelly_ratio: float,
        current_volatility: float,
        target_volatility: float = 0.02
    ) -> float:
        """
        변동성 타겟팅 기반 켈리 조정
        
        Args:
            kelly_ratio: 켈리 비율
            current_volatility: 현재 시장 변동성 (ATR 기반)
            target_volatility: 목표 변동성 (기본값: 2%)
        
        Returns:
            변동성 조정된 켈리 비율
        """
        if current_volatility <= 0:
            logger.warning(f"⚠️ 변동성이 0 이하입니다: {current_volatility}")
            return kelly_ratio
        
        # 변동성이 높을수록 포지션 축소
        volatility_adjustment = target_volatility / current_volatility
        
        # 최대 2배, 최소 0.1배로 제한
        volatility_adjustment = max(0.1, min(volatility_adjustment, 2.0))
        
        adjusted_kelly = kelly_ratio * volatility_adjustment
        
        logger.info(
            f"📊 변동성 조정: "
            f"현재 변동성={current_volatility:.2%}, "
            f"목표 변동성={target_volatility:.2%}, "
            f"조정 배율={volatility_adjustment:.2f}, "
            f"조정된 켈리={adjusted_kelly:.2%}"
        )
        
        return adjusted_kelly
    
    def calculate_confidence_adjusted_kelly(
        self,
        kelly_ratio: float,
        signal_confidence: float
    ) -> float:
        """
        신뢰도 기반 켈리 조정
        
        Args:
            kelly_ratio: 켈리 비율
            signal_confidence: 신호 신뢰도 (0.0-1.0)
        
        Returns:
            신뢰도 조정된 켈리 비율
        """
        adjusted_kelly = kelly_ratio * signal_confidence
        
        logger.info(
            f"📊 신뢰도 조정: "
            f"신뢰도={signal_confidence:.1%}, "
            f"조정된 켈리={adjusted_kelly:.2%}"
        )
        
        return adjusted_kelly
    
    def calculate_optimal_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_volatility: float,
        signal_confidence: float,
        kelly_fraction: float = 0.25,
        target_volatility: float = 0.02,
        max_position_size: float = 0.30,
        vector_4d: Optional[Dict[str, float]] = None,
        lambda_constraint: Optional[float] = None  # 통일장 이론 업그레이드: λ 보정 추가
    ) -> Dict[str, float]:
        """
        최적 포지션 크기 종합 계산
        
        MKM12 수학 헌법 v4.0 준수:
        - 헌법 제6장 Kelly Criterion 제27공식: 신뢰도 조정 켈리
        - Divine Centroid (0.25 평형) 신뢰도 보정 적용
        
        Args:
            win_rate: 승률
            avg_win: 평균 수익률
            avg_loss: 평균 손실률
            current_volatility: 현재 변동성
            signal_confidence: 신호 신뢰도
            kelly_fraction: 켈리 비율 (기본값: 0.25 = Quarter-Kelly)
            target_volatility: 목표 변동성
            max_position_size: 최대 포지션 크기 (기본값: 30%)
            vector_4d: 4D 벡터 (Divine Centroid 보정용, 선택적)
        
        Returns:
            포지션 사이징 정보 딕셔너리
        """
        # 1. 풀 켈리 계산
        full_kelly = self.calculate_full_kelly(win_rate, avg_win, avg_loss)
        
        # 2. Fractional Kelly
        fractional_kelly = self.calculate_fractional_kelly(full_kelly, kelly_fraction)
        
        # 3. 변동성 조정
        volatility_adjusted = self.calculate_volatility_adjusted_kelly(
            fractional_kelly, current_volatility, target_volatility
        )
        
        # 4. 신뢰도 조정
        confidence_adjusted = self.calculate_confidence_adjusted_kelly(
            volatility_adjusted, signal_confidence
        )
        
        # 5. Divine Centroid 신뢰도 보정 (MKM12 수학 헌법 v4.0)
        # 헌법 제5장 Divine Centroid 제20공식: 거리 < 0.15일 때 신뢰도 +10% 보정
        divine_adjusted = confidence_adjusted
        if vector_4d:
            try:
                distance = self._calculate_divine_distance(vector_4d)
                if distance < 0.15:
                    # 거리 < 0.15일 때 신뢰도 +10% 보정
                    divine_bonus = 0.10
                    divine_adjusted = min(1.0, confidence_adjusted * (1.0 + divine_bonus))
                    logger.info(
                        f"📊 Divine Centroid 보정: "
                        f"거리={distance:.4f}, "
                        f"보정 전={confidence_adjusted:.2%}, "
                        f"보정 후={divine_adjusted:.2%}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Divine Centroid 보정 실패: {e}, 보정 없이 진행")
        
        # 5.5. 통일장 이론 λ 보정 (통일장 이론 업그레이드)
        # 불균형(λ)이 클수록 포지션 감소
        lambda_adjusted = divine_adjusted
        if lambda_constraint is not None:
            try:
                # λ 보정: 불균형이 클수록 포지션 감소
                # λ가 0.5 이상이면 포지션 0, λ가 0이면 보정 없음
                lambda_penalty = max(0.0, 1.0 - lambda_constraint * 2.0)  # λ가 0.5 이상이면 0
                lambda_adjusted = divine_adjusted * lambda_penalty
                logger.info(
                    f"🌌 통일장 이론 λ 보정: "
                    f"λ={lambda_constraint:.4f}, "
                    f"보정 전={divine_adjusted:.2%}, "
                    f"보정 후={lambda_adjusted:.2%}"
                )
            except Exception as e:
                logger.warning(f"⚠️ λ 보정 실패: {e}, 보정 없이 진행")
                lambda_adjusted = divine_adjusted
        else:
            lambda_adjusted = divine_adjusted
        
        # 6. 최대 포지션 크기 제한
        final_position_size = min(lambda_adjusted, max_position_size)
        
        result = {
            "full_kelly": full_kelly,
            "fractional_kelly": fractional_kelly,
            "volatility_adjusted": volatility_adjusted,
            "confidence_adjusted": confidence_adjusted,
            "divine_adjusted": divine_adjusted if vector_4d else confidence_adjusted,
            "lambda_adjusted": lambda_adjusted if lambda_constraint is not None else (divine_adjusted if vector_4d else confidence_adjusted),
            "final_position_size": final_position_size,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_reward_ratio": avg_win / avg_loss if avg_loss > 0 else 0.0,
            "lambda_constraint": lambda_constraint if lambda_constraint is not None else None
        }
        
        logger.info(
            f"✅ 최적 포지션 크기 계산 완료: "
            f"최종 포지션 크기={final_position_size:.2%}"
        )
        
        return result
    
    def _calculate_divine_distance(
        self,
        vector_4d: Dict[str, float]
    ) -> float:
        """
        Divine Centroid와의 거리 계산
        
        MKM12 수학 헌법 v4.0 준수:
        - 헌법 제5장 Divine Centroid 제21공식: 거리 계산
        
        Args:
            vector_4d: 4D 벡터
        
        Returns:
            Divine Centroid와의 유클리드 거리
        """
        s_diff = vector_4d.get("S", 0.25) - DIVINE_CENTROID["S"]
        l_diff = vector_4d.get("L", 0.25) - DIVINE_CENTROID["L"]
        k_diff = vector_4d.get("K", 0.25) - DIVINE_CENTROID["K"]
        m_diff = vector_4d.get("M", 0.25) - DIVINE_CENTROID["M"]
        
        return math.sqrt(s_diff**2 + l_diff**2 + k_diff**2 + m_diff**2)

