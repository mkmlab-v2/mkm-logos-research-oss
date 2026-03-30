#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주역 64괘 실체적 통합 모듈 (I-Ching 64 Hexagram Integrator)

목적: 주역 64괘를 MKM12 동역학 예측 모델에 실체적으로 통합
원리: 4D 벡터(S-L-K-M)를 64괘로 변환하고, 괘 변화를 동역학 방정식에 반영

작성일: 2026-02-12
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
import numpy as np
import logging

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

# 주역 위상 전이 모듈 import
try:
    from scripts.iching_phase_shift import (
        Vector4D, Trigram, Hexagram, PhaseShift,
        vector_to_trigram, trigrams_to_hexagram, detect_phase_shift
    )
    ICHING_AVAILABLE = True
except ImportError:
    ICHING_AVAILABLE = False
    logging.warning("⚠️ 주역 위상 전이 모듈을 import할 수 없습니다.")

logger = logging.getLogger(__name__)


class IChing64HexagramIntegrator:
    """
    주역 64괘 실체적 통합 클래스
    
    기능:
    1. 4D 벡터(S-L-K-M)를 64괘로 변환
    2. 괘 변화를 동역학 방정식에 반영
    3. 예측 결과를 괘 기반으로 검증 및 보정
    """
    
    def __init__(
        self,
        equilibrium_point: float = 0.25,
        hexagram_weight: float = 0.3  # 괘 기반 보정 가중치 (30%)
    ):
        """
        Args:
            equilibrium_point: 균형점 (기본값: 0.25)
            hexagram_weight: 괘 기반 보정 가중치 (기본값: 0.3)
        """
        self.equilibrium_point = equilibrium_point
        self.hexagram_weight = hexagram_weight
        
        if not ICHING_AVAILABLE:
            logger.warning("⚠️ 주역 위상 전이 모듈이 없어 제한된 기능만 사용 가능합니다.")
    
    def vector_to_hexagram(
        self,
        vector_4d: Dict[str, float]
    ) -> Optional[Hexagram]:
        """
        4D 벡터(S-L-K-M)를 주역 64괘로 변환
        
        원리:
        - S, L, K, M을 각각 fire, wood, metal, water로 매핑
        - 각 차원이 0.25보다 크면 양(1), 작으면 음(0)
        - 상괘와 하괘를 조합하여 64괘 생성
        
        Args:
            vector_4d: 4D 벡터 {S, L, K, M}
        
        Returns:
            주역 64괘 (Hexagram) 또는 None
        """
        if not ICHING_AVAILABLE:
            return None
        
        try:
            # S-L-K-M을 fire-wood-metal-water로 매핑
            vector = Vector4D(
                fire=vector_4d.get("S", self.equilibrium_point),
                wood=vector_4d.get("L", self.equilibrium_point),
                metal=vector_4d.get("K", self.equilibrium_point),
                water=vector_4d.get("M", self.equilibrium_point)
            )
            
            # 상괘와 하괘 생성
            # 상괘: S(Spirit) + L(Life) 조합
            upper_vector = Vector4D(
                fire=vector_4d.get("S", self.equilibrium_point),
                wood=vector_4d.get("L", self.equilibrium_point),
                metal=self.equilibrium_point,
                water=self.equilibrium_point
            )
            upper_trigram = vector_to_trigram(upper_vector)
            
            # 하괘: K(Karma) + M(Matter) 조합
            lower_vector = Vector4D(
                fire=self.equilibrium_point,
                wood=self.equilibrium_point,
                metal=vector_4d.get("K", self.equilibrium_point),
                water=vector_4d.get("M", self.equilibrium_point)
            )
            lower_trigram = vector_to_trigram(lower_vector)
            
            # 64괘 생성
            hexagram = trigrams_to_hexagram(upper_trigram, lower_trigram)
            
            return hexagram
        
        except Exception as e:
            logger.error(f"❌ 4D 벡터를 주역 괘로 변환 실패: {e}")
            return None
    
    def hexagram_to_vector_correction(
        self,
        current_hexagram: Hexagram,
        predicted_hexagram: Hexagram,
        predicted_vector: Dict[str, float]
    ) -> Dict[str, float]:
        """
        괘 변화를 기반으로 예측 벡터 보정
        
        원리:
        - 괘 변화가 있으면 위상 전이로 해석
        - 위상 전이 방향에 따라 벡터 보정
        - 괘 특성에 따라 보정 강도 조정
        
        Args:
            current_hexagram: 현재 괘
            predicted_hexagram: 예측 괘
            predicted_vector: 예측된 4D 벡터
        
        Returns:
            보정된 4D 벡터
        """
        corrected_vector = predicted_vector.copy()
        
        # 괘 변화 확인
        if current_hexagram.number == predicted_hexagram.number:
            # 괘 변화 없음 → 보정 없음
            return corrected_vector
        
        # 괘 변화 계산
        hexagram_change = predicted_hexagram.number - current_hexagram.number
        
        # 위상 전이 방향 결정
        if hexagram_change > 0:
            # 상승 전이 → S, L 차원 증가
            correction_factor = min(abs(hexagram_change) / 64.0, 0.2)  # 최대 20% 보정
            corrected_vector["S"] = predicted_vector.get("S", self.equilibrium_point) * (1.0 + correction_factor * self.hexagram_weight)
            corrected_vector["L"] = predicted_vector.get("L", self.equilibrium_point) * (1.0 + correction_factor * self.hexagram_weight)
        elif hexagram_change < 0:
            # 하락 전이 → K, M 차원 증가
            correction_factor = min(abs(hexagram_change) / 64.0, 0.2)  # 최대 20% 보정
            corrected_vector["K"] = predicted_vector.get("K", self.equilibrium_point) * (1.0 + correction_factor * self.hexagram_weight)
            corrected_vector["M"] = predicted_vector.get("M", self.equilibrium_point) * (1.0 + correction_factor * self.hexagram_weight)
        
        # 정규화
        total = sum(corrected_vector.values())
        if total > 0:
            corrected_vector = {k: v / total for k, v in corrected_vector.items()}
        
        return corrected_vector
    
    def integrate_hexagram_into_dynamics(
        self,
        current_state: Dict[str, float],
        predicted_state: Dict[str, float],
        f_sasang: Dict[str, float]
    ) -> Dict[str, float]:
        """
        주역 괘를 동역학 방정식에 통합
        
        원리:
        - 현재 상태와 예측 상태를 괘로 변환
        - 괘 변화를 F_사상에 반영
        - 괘 특성에 따라 동역학 계수 조정
        
        Args:
            current_state: 현재 4D 벡터 {S, L, K, M}
            predicted_state: 예측된 4D 벡터 {S, L, K, M}
            f_sasang: F_사상 계산 결과 {S, L, K, M}
        
        Returns:
            괘 통합이 반영된 F_사상 결과
        """
        if not ICHING_AVAILABLE:
            return f_sasang
        
        try:
            # 현재 상태와 예측 상태를 괘로 변환
            current_hexagram = self.vector_to_hexagram(current_state)
            predicted_hexagram = self.vector_to_hexagram(predicted_state)
            
            if not current_hexagram or not predicted_hexagram:
                return f_sasang
            
            # 괘 변화 확인
            if current_hexagram.number == predicted_hexagram.number:
                # 괘 변화 없음 → F_사상 유지
                return f_sasang
            
            # 괘 변화 계산
            hexagram_change = predicted_hexagram.number - current_hexagram.number
            change_magnitude = abs(hexagram_change) / 64.0  # 0-1 정규화
            
            # 괘 변화를 F_사상에 반영
            adjusted_f_sasang = f_sasang.copy()
            
            if hexagram_change > 0:
                # 상승 전이 → S, L 차원 동역학 강화
                adjustment = change_magnitude * self.hexagram_weight
                adjusted_f_sasang["S"] = f_sasang.get("S", 0.0) * (1.0 + adjustment)
                adjusted_f_sasang["L"] = f_sasang.get("L", 0.0) * (1.0 + adjustment)
            elif hexagram_change < 0:
                # 하락 전이 → K, M 차원 동역학 강화
                adjustment = change_magnitude * self.hexagram_weight
                adjusted_f_sasang["K"] = f_sasang.get("K", 0.0) * (1.0 + adjustment)
                adjusted_f_sasang["M"] = f_sasang.get("M", 0.0) * (1.0 + adjustment)
            
            return adjusted_f_sasang
        
        except Exception as e:
            logger.error(f"❌ 주역 괘를 동역학 방정식에 통합 실패: {e}")
            return f_sasang
    
    def validate_prediction_with_hexagram(
        self,
        current_state: Dict[str, float],
        predicted_state: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        주역 괘를 사용하여 예측 결과 검증
        
        원리:
        - 현재 상태와 예측 상태를 괘로 변환
        - 괘 변화의 논리적 일관성 검증
        - 괘 특성에 따른 예측 신뢰도 조정
        
        Args:
            current_state: 현재 4D 벡터 {S, L, K, M}
            predicted_state: 예측된 4D 벡터 {S, L, K, M}
        
        Returns:
            검증 결과:
            {
                "is_valid": bool,  # 예측이 논리적으로 유효한가?
                "hexagram_transition": Dict[str, Any],  # 괘 변화 정보
                "confidence_adjustment": float,  # 신뢰도 조정값 (-0.2 ~ +0.2)
                "reasoning": str  # 검증 근거
            }
        """
        if not ICHING_AVAILABLE:
            return {
                "is_valid": True,
                "hexagram_transition": None,
                "confidence_adjustment": 0.0,
                "reasoning": "주역 모듈 없음 - 검증 스킵"
            }
        
        try:
            # 현재 상태와 예측 상태를 괘로 변환
            current_hexagram = self.vector_to_hexagram(current_state)
            predicted_hexagram = self.vector_to_hexagram(predicted_state)
            
            if not current_hexagram or not predicted_hexagram:
                return {
                    "is_valid": True,
                    "hexagram_transition": None,
                    "confidence_adjustment": 0.0,
                    "reasoning": "괘 변환 실패 - 검증 스킵"
                }
            
            # 괘 변화 확인
            hexagram_change = predicted_hexagram.number - current_hexagram.number
            change_magnitude = abs(hexagram_change)
            
            # 논리적 일관성 검증
            # 1. 극단적 변화는 비정상적 (64괘 중 32개 이상 변화)
            if change_magnitude > 32:
                return {
                    "is_valid": False,
                    "hexagram_transition": {
                        "from": current_hexagram.number,
                        "to": predicted_hexagram.number,
                        "change": hexagram_change
                    },
                    "confidence_adjustment": -0.2,  # 신뢰도 20% 감소
                    "reasoning": f"극단적 괘 변화 감지 (변화량: {change_magnitude})"
                }
            
            # 2. 정상적인 괘 변화 (1-10개 변화)
            if 1 <= change_magnitude <= 10:
                return {
                    "is_valid": True,
                    "hexagram_transition": {
                        "from": current_hexagram.number,
                        "to": predicted_hexagram.number,
                        "change": hexagram_change
                    },
                    "confidence_adjustment": +0.1,  # 신뢰도 10% 증가
                    "reasoning": f"정상적인 괘 변화 (변화량: {change_magnitude})"
                }
            
            # 3. 중간 변화 (11-32개 변화)
            return {
                "is_valid": True,
                "hexagram_transition": {
                    "from": current_hexagram.number,
                    "to": predicted_hexagram.number,
                    "change": hexagram_change
                },
                "confidence_adjustment": 0.0,  # 신뢰도 유지
                "reasoning": f"중간 괘 변화 (변화량: {change_magnitude})"
            }
        
        except Exception as e:
            logger.error(f"❌ 주역 괘 기반 예측 검증 실패: {e}")
            return {
                "is_valid": True,
                "hexagram_transition": None,
                "confidence_adjustment": 0.0,
                "reasoning": f"검증 오류: {e}"
            }

