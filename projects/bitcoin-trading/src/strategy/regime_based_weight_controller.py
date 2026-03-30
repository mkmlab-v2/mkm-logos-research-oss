#!/usr/bin/env python3
"""
국면 기반 TheoryFusion 가중치 조정

시장 국면에 따라 TheoryFusion의 9개 이론 가중치를 동적으로 조정
"""
import numpy as np
from typing import Dict, Optional, Any
import logging

from ..analysis.market_regime_detector import MarketRegimeDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegimeBasedWeightController:
    """
    시장 국면 기반 TheoryFusion 가중치 조정
    
    국면별 최적 이론 가중치 매트릭스를 사용하여
    실시간으로 TheoryFusion 가중치를 동적 조정
    """
    
    # TheoryFusion 9개 이론 목록 (예시)
    THEORY_NAMES = [
        "trend_following",
        "mean_reversion",
        "momentum",
        "volatility_breakout",
        "pattern_recognition",
        "crisis_detection",
        "divine_centroid",
        "phase_resonance",
        "quaternion_analysis"
    ]
    
    def __init__(self):
        """국면 기반 가중치 컨트롤러 초기화"""
        self.regime_detector = MarketRegimeDetector()
        
        # 국면별 최적 이론 가중치 매트릭스
        # 각 국면에서 어떤 이론이 효과적인지 정의
        self.regime_weight_matrix = {
            "strong_bull": {
                "trend_following": 0.30,
                "momentum": 0.25,
                "volatility_breakout": 0.15,
                "pattern_recognition": 0.10,
                "mean_reversion": 0.05,
                "crisis_detection": 0.05,
                "divine_centroid": 0.05,
                "phase_resonance": 0.03,
                "quaternion_analysis": 0.02
            },
            "strong_bear": {
                "mean_reversion": 0.30,
                "crisis_detection": 0.25,
                "trend_following": 0.10,
                "momentum": 0.10,
                "volatility_breakout": 0.10,
                "pattern_recognition": 0.05,
                "divine_centroid": 0.05,
                "phase_resonance": 0.03,
                "quaternion_analysis": 0.02
            },
            "volatility_spike": {
                "volatility_breakout": 0.40,
                "crisis_detection": 0.25,
                "trend_following": 0.10,
                "momentum": 0.10,
                "mean_reversion": 0.05,
                "pattern_recognition": 0.05,
                "divine_centroid": 0.03,
                "phase_resonance": 0.01,
                "quaternion_analysis": 0.01
            },
            "grind_up": {
                "trend_following": 0.25,
                "mean_reversion": 0.20,
                "momentum": 0.20,
                "pattern_recognition": 0.15,
                "volatility_breakout": 0.10,
                "divine_centroid": 0.05,
                "crisis_detection": 0.03,
                "phase_resonance": 0.01,
                "quaternion_analysis": 0.01
            },
            "grind_down": {
                "mean_reversion": 0.30,
                "trend_following": 0.20,
                "momentum": 0.15,
                "pattern_recognition": 0.15,
                "volatility_breakout": 0.10,
                "crisis_detection": 0.05,
                "divine_centroid": 0.03,
                "phase_resonance": 0.01,
                "quaternion_analysis": 0.01
            },
            "range_squeeze": {
                "volatility_breakout": 0.35,
                "mean_reversion": 0.25,
                "pattern_recognition": 0.20,
                "trend_following": 0.10,
                "momentum": 0.05,
                "divine_centroid": 0.03,
                "crisis_detection": 0.01,
                "phase_resonance": 0.01,
                "quaternion_analysis": 0.00
            }
        }
    
    def adjust_weights(
        self,
        current_regime: Dict[str, Any],
        base_weights: Dict[str, float],
        regime_confidence: float = None
    ) -> Dict[str, float]:
        """
        국면에 따라 가중치 동적 조정
        
        Args:
            current_regime: 현재 국면 정보 (detect_regime() 결과)
            base_weights: 기본 이론 가중치 (TheoryFusion 기본값)
            regime_confidence: 국면 확신도 (None이면 current_regime에서 추출)
        
        Returns:
            조정된 가중치 딕셔너리
        """
        # 국면 확신도 추출
        if regime_confidence is None:
            regime_confidence = current_regime.get("confidence", 0.5)
        
        # 가장 높은 확률의 국면 선택
        if "probabilities" in current_regime:
            probabilities = current_regime["probabilities"]
            dominant_regime = max(probabilities.items(), key=lambda x: x[1])[0]
            regime_confidence = probabilities[dominant_regime]
        else:
            dominant_regime = current_regime.get("dominant_regime", "unknown")
        
        # 국면별 최적 가중치 가져오기
        regime_weights = self.regime_weight_matrix.get(
            dominant_regime,
            {theory: 1.0 / len(self.THEORY_NAMES) for theory in self.THEORY_NAMES}  # 균등 가중치
        )
        
        # 기본 가중치와 국면 가중치 혼합
        adjusted_weights = {}
        for theory in self.THEORY_NAMES:
            base_weight = base_weights.get(theory, 1.0 / len(self.THEORY_NAMES))
            regime_weight = regime_weights.get(theory, base_weight)
            
            # 가중 평균 (국면 확신도에 따라)
            # 확신도가 높을수록 국면 가중치를 더 많이 반영
            adjusted_weights[theory] = (
                base_weight * (1 - regime_confidence) +
                regime_weight * regime_confidence
            )
        
        # 정규화 (합이 1이 되도록)
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {k: v / total for k, v in adjusted_weights.items()}
        else:
            # 합이 0이면 균등 가중치
            adjusted_weights = {theory: 1.0 / len(self.THEORY_NAMES) for theory in self.THEORY_NAMES}
        
        logger.info(
            f"📊 국면 기반 가중치 조정: "
            f"국면={dominant_regime}, "
            f"확신도={regime_confidence:.1%}, "
            f"최대 가중치 이론={max(adjusted_weights.items(), key=lambda x: x[1])[0]}"
        )
        
        return adjusted_weights
    
    def get_regime_strategy_preferences(
        self,
        current_regime: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        국면별 전략 선호도 반환
        
        Args:
            current_regime: 현재 국면 정보
        
        Returns:
            전략 선호도 정보
        """
        if "probabilities" in current_regime:
            probabilities = current_regime["probabilities"]
            dominant_regime = max(probabilities.items(), key=lambda x: x[1])[0]
        else:
            dominant_regime = current_regime.get("dominant_regime", "unknown")
        
        regime_weights = self.regime_weight_matrix.get(dominant_regime, {})
        
        # 선호 이론 (가중치 상위 3개)
        sorted_theories = sorted(
            regime_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # 회피 이론 (가중치 하위 3개)
        avoided_theories = sorted(
            regime_weights.items(),
            key=lambda x: x[1],
            reverse=False
        )[:3]
        
        return {
            "dominant_regime": dominant_regime,
            "preferred_theories": [t[0] for t in sorted_theories],
            "avoided_theories": [t[0] for t in avoided_theories],
            "weight_distribution": regime_weights
        }

