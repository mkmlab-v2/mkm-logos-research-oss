#!/usr/bin/env python3
"""
주역 위상 전이 필터 (I-Ching Phase Transition Filter)

원리: 극즉반(極則反) - 극에 달하면 반전한다
효과: 4D 벡터가 0.25 균형점을 돌파하거나 극단값에 도달했을 때, 
      주역의 '변효(Change)' 원리를 적용하여 매수/매도 신호를 최종 승인

구현:
- 극값 감지 (0.25 ± threshold 범위 밖)
- 극즉반 원리 적용 (반전 예측)
- 주역 괘 변화 분석 (있는 경우)
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import logging

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IChingPhaseFilter:
    """
    주역 위상 전이 필터
    
    원리: 극즉반(極則反) - 극에 달하면 반전한다
    효과: 예측된 결과가 시장의 임계점(0.25 균형점)에 도달했는지 판정하여
          매수/매도 타이밍을 최종 확정
    """
    
    def __init__(
        self,
        equilibrium_point: float = 0.25,
        threshold: float = 0.1,  # 0.25 ± 0.1 범위 밖이면 극값
        reversal_strength: float = 0.3  # 반전 강도 (30%)
    ):
        """
        Args:
            equilibrium_point: 균형점 (기본값: 0.25)
            threshold: 극값 임계값 (기본값: 0.1)
            reversal_strength: 반전 강도 (기본값: 0.3 = 30%)
        """
        self.equilibrium_point = equilibrium_point
        self.threshold = threshold
        self.reversal_strength = reversal_strength
    
    def apply_phase_transition(
        self,
        predicted_state: Dict[str, float],
        current_state: Dict[str, float],
        hexagram: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        주역 위상 전이 필터 적용
        
        원리: 극즉반(極則反)
        - 예측된 벡터가 극값에 도달했는지 감지
        - 극값이면 반전 예측 적용
        - 주역 괘 변화 분석 (있는 경우)
        
        Args:
            predicted_state: 예측된 4D 벡터 (S, L, K, M)
            current_state: 현재 4D 벡터 (S, L, K, M)
            hexagram: 주역 괘 (선택적)
        
        Returns:
            필터링된 예측 결과:
            {
                "filtered_state": Dict[str, float],  # 필터링된 벡터
                "reversal_detected": bool,  # 반전 감지 여부
                "reversal_strength": float,  # 반전 강도
                "hexagram_analysis": Dict[str, Any],  # 주역 괘 분석 (있는 경우)
                "signal_adjustment": str  # 신호 조정 ("BUY", "SELL", "HOLD")
            }
        """
        try:
            # 1. 극값 감지
            reversal_detected, reversal_strength = self._detect_extreme_value(
                predicted_state
            )
            
            # 2. 극즉반 원리 적용
            if reversal_detected:
                filtered_state = self._apply_reversal(
                    predicted_state,
                    reversal_strength
                )
            else:
                filtered_state = predicted_state.copy()
            
            # 3. 주역 괘 변화 분석 (있는 경우)
            hexagram_analysis = None
            if hexagram:
                hexagram_analysis = self._analyze_hexagram_transition(
                    current_state,
                    filtered_state,
                    hexagram
                )
            
            # 4. 신호 조정 결정
            signal_adjustment = self._determine_signal_adjustment(
                current_state,
                filtered_state,
                reversal_detected
            )
            
            return {
                "filtered_state": filtered_state,
                "reversal_detected": reversal_detected,
                "reversal_strength": reversal_strength,
                "hexagram_analysis": hexagram_analysis,
                "signal_adjustment": signal_adjustment
            }
        
        except Exception as e:
            logger.error(f"❌ 주역 위상 전이 필터 적용 실패: {e}")
            return {
                "filtered_state": predicted_state.copy(),
                "reversal_detected": False,
                "reversal_strength": 0.0,
                "hexagram_analysis": None,
                "signal_adjustment": "HOLD"
            }
    
    def _detect_extreme_value(
        self,
        vector_4d: Dict[str, float]
    ) -> Tuple[bool, float]:
        """
        극값 감지
        
        원리: 0.25 균형점으로부터의 편차가 threshold를 초과하면 극값으로 판단
        
        Args:
            vector_4d: 4D 벡터
        
        Returns:
            (극값 감지 여부, 반전 강도)
        """
        # 편차 계산
        deviation = {
            key: abs(vector_4d.get(key, self.equilibrium_point) - self.equilibrium_point)
            for key in ["S", "L", "K", "M"]
        }
        
        max_deviation = max(deviation.values())
        
        # 극값 감지 (threshold 초과)
        if max_deviation > self.threshold:
            # 반전 강도 계산 (편차가 클수록 강함)
            reversal_strength = min(max_deviation / self.threshold, 1.0)
            return True, reversal_strength
        
        return False, 0.0
    
    def _apply_reversal(
        self,
        vector_4d: Dict[str, float],
        reversal_strength: float
    ) -> Dict[str, float]:
        """
        극즉반 원리 적용
        
        원리: 극값이면 반대편으로 보정 (극즉반)
        효과: 예측된 극값을 균형점으로 회귀시키는 방향으로 조정
        
        Args:
            vector_4d: 예측된 4D 벡터
            reversal_strength: 반전 강도
        
        Returns:
            반전 보정된 벡터
        """
        corrected_vector = {}
        
        for key in ["S", "L", "K", "M"]:
            current = vector_4d.get(key, self.equilibrium_point)
            deviation = current - self.equilibrium_point
            
            # 극값이면 반대편으로 보정 (극즉반 원리)
            if abs(deviation) > self.threshold:
                # 반전 강도에 따라 보정
                correction = -deviation * self.reversal_strength * reversal_strength
                corrected_vector[key] = self.equilibrium_point + correction
            else:
                corrected_vector[key] = current
        
        # 정규화
        total = sum(corrected_vector.values())
        if total > 0:
            corrected_vector = {k: v / total for k, v in corrected_vector.items()}
        
        return corrected_vector
    
    def _analyze_hexagram_transition(
        self,
        current_state: Dict[str, float],
        predicted_state: Dict[str, float],
        hexagram: str
    ) -> Dict[str, Any]:
        """
        주역 괘 변화 분석
        
        원리: 주역 괘 변화를 통해 위상 전이 예측
        효과: 괘 변화가 있으면 위상 전이 신호로 해석
        
        Args:
            current_state: 현재 4D 벡터
            predicted_state: 예측된 4D 벡터
            hexagram: 주역 괘
        
        Returns:
            주역 괘 분석 결과
        """
        # 간단한 버전: 괘 이름만 반환
        # 향후 실제 괘 변화 분석 로직 추가 가능
        
        return {
            "hexagram": hexagram,
            "transition_detected": True,  # 향후 실제 분석 로직 추가
            "transition_direction": "neutral"  # 향후 실제 분석 로직 추가
        }
    
    def _determine_signal_adjustment(
        self,
        current_state: Dict[str, float],
        filtered_state: Dict[str, float],
        reversal_detected: bool
    ) -> str:
        """
        신호 조정 결정
        
        원리: 극값 감지 및 반전 여부에 따라 매수/매도 신호 조정
        
        Args:
            current_state: 현재 4D 벡터
            filtered_state: 필터링된 4D 벡터
            reversal_detected: 반전 감지 여부
        
        Returns:
            신호 조정 ("BUY", "SELL", "HOLD")
        """
        if not reversal_detected:
            return "HOLD"
        
        # S 차원 변화 분석 (Spirit = 상승 압력)
        current_S = current_state.get("S", self.equilibrium_point)
        filtered_S = filtered_state.get("S", self.equilibrium_point)
        
        S_change = filtered_S - current_S
        
        # 극값에서 반전이 감지되었고, S가 감소하면 매도 신호
        if S_change < -0.05:  # 5% 이상 감소
            return "SELL"
        # 극값에서 반전이 감지되었고, S가 증가하면 매수 신호
        elif S_change > 0.05:  # 5% 이상 증가
            return "BUY"
        else:
            return "HOLD"

