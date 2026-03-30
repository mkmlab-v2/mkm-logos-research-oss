#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 감정적 역추세 필터 (Sentiment Reversal Filter)

목적: 사원수 회전각 기반 대중 심리 과열 상태 판별
전략: "Sell the News" 패턴 감지

작성일: 2026-01-11
상태: ✅ 구현 중
"""

import math
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SentimentReversalFilter:
    """
    감정적 역추세 필터
    
    기능:
    1. 사원수 회전각 계산 (4D 벡터 회전)
    2. 대중 심리 과열 상태 판별
    3. "Sell the News" 패턴 감지
    4. 역추세 위험 신호 생성
    """
    
    def __init__(
        self,
        angular_velocity_threshold: float = 0.5,  # 각속도 임계값
        sentiment_overheat_threshold: float = 0.8,  # 심리 과열 임계값
        reversal_risk_threshold: float = 0.7  # 역추세 위험 임계값
    ):
        """
        초기화
        
        Args:
            angular_velocity_threshold: 각속도 임계값
            sentiment_overheat_threshold: 심리 과열 임계값
            reversal_risk_threshold: 역추세 위험 임계값
        """
        self.angular_velocity_threshold = angular_velocity_threshold
        self.sentiment_overheat_threshold = sentiment_overheat_threshold
        self.reversal_risk_threshold = reversal_risk_threshold
        
        # 벡터 히스토리 (각속도 계산용)
        self.vector_history: List[Dict[str, float]] = []
        self.max_history = 10
    
    def calculate_angular_velocity(
        self,
        current_vector: Dict[str, float],
        previous_vector: Optional[Dict[str, float]] = None
    ) -> float:
        """
        사원수 회전각 계산 (각속도)
        
        Args:
            current_vector: 현재 4D 벡터
            previous_vector: 이전 4D 벡터
        
        Returns:
            각속도 (rad/s)
        """
        if previous_vector is None:
            return 0.0
        
        # 4D 벡터를 numpy 배열로 변환
        try:
            import numpy as np
            
            v1 = np.array([
                previous_vector.get("S", 0.25),
                previous_vector.get("L", 0.25),
                previous_vector.get("K", 0.25),
                previous_vector.get("M", 0.25)
            ])
            
            v2 = np.array([
                current_vector.get("S", 0.25),
                current_vector.get("L", 0.25),
                current_vector.get("K", 0.25),
                current_vector.get("M", 0.25)
            ])
            
            # 정규화
            v1_norm = v1 / (np.linalg.norm(v1) + 1e-10)
            v2_norm = v2 / (np.linalg.norm(v2) + 1e-10)
            
            # 내적 (코사인 각도)
            dot_product = np.dot(v1_norm, v2_norm)
            dot_product = np.clip(dot_product, -1.0, 1.0)
            
            # 각도 (라디안)
            angle = math.acos(dot_product)
            
            # 각속도 (라디안/초, 시간 간격 1초 가정)
            angular_velocity = angle / 1.0
            
            return float(angular_velocity)
        except Exception as e:
            logger.warning(f"⚠️ 각속도 계산 실패: {e}")
            return 0.0
    
    def calculate_sentiment_overheat(
        self,
        vector_4d: Dict[str, float]
    ) -> float:
        """
        심리 과열 상태 계산
        
        Args:
            vector_4d: 4D 벡터
        
        Returns:
            심리 과열 점수 (0.0 ~ 1.0)
        """
        # S(Spirit) 차원이 높을수록 심리 과열
        # M(Material) 차원이 높을수록 물질적 탐욕
        s_value = vector_4d.get("S", 0.25)
        m_value = vector_4d.get("M", 0.25)
        
        # 심리 과열 점수 = (S + M) / 2
        sentiment_score = (s_value + m_value) / 2.0
        
        return min(1.0, max(0.0, sentiment_score))
    
    def detect_reversal_pattern(
        self,
        vector_4d: Dict[str, float],
        angular_velocity: float,
        sentiment_overheat: float
    ) -> Dict[str, Any]:
        """
        역추세 패턴 감지
        
        Args:
            vector_4d: 4D 벡터
            angular_velocity: 각속도
            sentiment_overheat: 심리 과열 점수
        
        Returns:
            역추세 패턴 분석 결과
        """
        # 1. 각속도가 높고 심리 과열 → 회전 둔화 가능성 (역추세 전조)
        if angular_velocity > self.angular_velocity_threshold and sentiment_overheat > self.sentiment_overheat_threshold:
            return {
                "reversal_risk": True,
                "risk_score": min(1.0, (angular_velocity + sentiment_overheat) / 2.0),
                "pattern": "high_angular_velocity_with_overheat",
                "message": "각속도 높음 + 심리 과열 → 역추세 위험"
            }
        
        # 2. 각속도가 낮고 심리 과열 → 정체 가능성 (역추세 전조)
        if angular_velocity < 0.1 and sentiment_overheat > self.sentiment_overheat_threshold:
            return {
                "reversal_risk": True,
                "risk_score": sentiment_overheat,
                "pattern": "low_angular_velocity_with_overheat",
                "message": "각속도 낮음 + 심리 과열 → 정체 및 역추세 위험"
            }
        
        # 3. 정상 상태
        return {
            "reversal_risk": False,
            "risk_score": 0.0,
            "pattern": "normal",
            "message": "역추세 위험 없음"
        }
    
    def check_reversal_risk(
        self,
        vector_4d: Dict[str, float],
        price_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        역추세 위험 체크 (전체 프로세스)
        
        Args:
            vector_4d: 4D 벡터
            price_data: 가격 데이터 (선택적)
        
        Returns:
            역추세 위험 검증 결과
        """
        # 1. 벡터 히스토리 업데이트
        self.vector_history.append(vector_4d.copy())
        if len(self.vector_history) > self.max_history:
            self.vector_history.pop(0)
        
        # 2. 각속도 계산
        angular_velocity = 0.0
        if len(self.vector_history) >= 2:
            previous_vector = self.vector_history[-2]
            current_vector = self.vector_history[-1]
            angular_velocity = self.calculate_angular_velocity(current_vector, previous_vector)
        
        # 3. 심리 과열 상태 계산
        sentiment_overheat = self.calculate_sentiment_overheat(vector_4d)
        
        # 4. 역추세 패턴 감지
        reversal_pattern = self.detect_reversal_pattern(
            vector_4d,
            angular_velocity,
            sentiment_overheat
        )
        
        # 5. 승인 여부 결정
        reversal_risk = reversal_pattern.get("reversal_risk", False)
        risk_score = reversal_pattern.get("risk_score", 0.0)
        
        approved = not reversal_risk or risk_score < self.reversal_risk_threshold
        
        return {
            "approved": approved,
            "reason": "역추세 위험 없음" if approved else "역추세 위험 감지",
            "angular_velocity": angular_velocity,
            "sentiment_overheat": sentiment_overheat,
            "reversal_pattern": reversal_pattern,
            "risk_score": risk_score
        }

