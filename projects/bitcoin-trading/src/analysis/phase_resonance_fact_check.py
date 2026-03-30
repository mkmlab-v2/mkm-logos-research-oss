#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
위상 공명 기반 팩트체크 모듈

GlobalKnowledgeVault의 위상 공명 기반 팩트체크를 매매 신호 검증에 적용
"""

import math
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Divine Centroid (Project Logos)
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}


class PhaseResonanceFactChecker:
    """
    위상 공명 기반 팩트체크
    
    매매 신호의 벡터가 Divine Centroid와 얼마나 공명하는지 검증
    """
    
    def __init__(self, divine_centroid: Dict[str, float] = None):
        """
        초기화
        
        Args:
            divine_centroid: Divine Centroid 벡터 (None이면 기본값 사용)
        """
        self.divine_centroid = divine_centroid or DIVINE_CENTROID
    
    def apply_phase_resonance_fact_check(
        self,
        vector_4d: Dict[str, float],
        threshold: float = 0.2  # 개선: 0.3 → 0.2로 강화 (더 엄격한 필터링)
    ) -> Dict[str, Any]:
        """
        위상 공명 기반 팩트체크 적용
        
        Args:
            vector_4d: 검증할 4D 벡터
            threshold: 환각 감지 임계값 (거리 > threshold이면 환각으로 판단)
        
        Returns:
            {
                "is_valid": bool,  # 유효한 신호인지
                "distance": float,  # Divine Centroid와의 거리
                "resonance_score": float,  # 공명 점수 (0.0 ~ 1.0)
                "hallucination_detected": bool,  # 환각 감지 여부
                "recommendation": str  # 권장 사항
            }
        """
        try:
            # Divine Centroid와의 거리 계산
            distance = self._calculate_distance(vector_4d, self.divine_centroid)
            
            # 공명 점수 계산 (거리가 가까울수록 높음)
            resonance_score = max(0.0, 1.0 - distance * 2.0)  # 거리 0.5 이상이면 0점
            
            # 환각 감지 (거리 > threshold)
            hallucination_detected = distance > threshold
            
            # 권장 사항
            if hallucination_detected:
                recommendation = "환각 감지: 신호 신뢰도 낮음, 거래 실행 비권장"
            elif distance > 0.2:
                recommendation = "주의: 벡터가 Divine Centroid에서 다소 벗어남"
            elif distance > 0.1:
                recommendation = "양호: 벡터가 Divine Centroid에 근접"
            else:
                recommendation = "우수: 벡터가 Divine Centroid와 높은 공명"
            
            return {
                "is_valid": not hallucination_detected,
                "distance": distance,
                "resonance_score": resonance_score,
                "hallucination_detected": hallucination_detected,
                "recommendation": recommendation
            }
        except Exception as e:
            logger.error(f"❌ 위상 공명 팩트체크 실패: {e}")
            return {
                "is_valid": False,
                "distance": 1.0,
                "resonance_score": 0.0,
                "hallucination_detected": True,
                "recommendation": f"팩트체크 오류: {e}"
            }
    
    def _calculate_distance(
        self,
        vector1: Dict[str, float],
        vector2: Dict[str, float]
    ) -> float:
        """
        두 벡터 간 유클리드 거리 계산
        
        Args:
            vector1: 첫 번째 벡터
            vector2: 두 번째 벡터
        
        Returns:
            유클리드 거리
        """
        s_diff = vector1.get("S", 0.25) - vector2.get("S", 0.25)
        l_diff = vector1.get("L", 0.25) - vector2.get("L", 0.25)
        k_diff = vector1.get("K", 0.25) - vector2.get("K", 0.25)
        m_diff = vector1.get("M", 0.25) - vector2.get("M", 0.25)
        
        return math.sqrt(s_diff**2 + l_diff**2 + k_diff**2 + m_diff**2)
    
    def validate_trading_signal(
        self,
        signal_data: Dict[str, Any],
        threshold: float = 0.2  # 개선: 0.3 → 0.2로 강화 (더 엄격한 필터링)
    ) -> Dict[str, Any]:
        """
        매매 신호 검증 (위상 공명 기반)
        
        Args:
            signal_data: 매매 신호 데이터 (sovereign_vector 또는 corrected_vector 포함)
            threshold: 환각 감지 임계값
        
        Returns:
            검증 결과
        """
        # 벡터 추출 (우선순위: corrected_vector > sovereign_vector)
        vector_4d = signal_data.get("corrected_vector") or signal_data.get("sovereign_vector")
        
        if not vector_4d:
            logger.warning("⚠️ 벡터 데이터가 없습니다. 팩트체크 스킵")
            return {
                "is_valid": True,  # 벡터가 없으면 기본적으로 통과
                "distance": None,
                "resonance_score": None,
                "hallucination_detected": False,
                "recommendation": "벡터 데이터 없음, 기본 검증 통과"
            }
        
        # 위상 공명 팩트체크 적용
        fact_check_result = self.apply_phase_resonance_fact_check(
            vector_4d=vector_4d,
            threshold=threshold
        )
        
        return fact_check_result

