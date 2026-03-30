#!/usr/bin/env python3
"""
HMM 기반 시장 국면 탐지 시스템

6개 상태 정의:
- State 1: Strong Bull (강력한 상승 추세)
- State 2: Strong Bear (강력한 하락 추세)
- State 3: Volatility Spike (변동성 폭발)
- State 4: Grind Up (완만한 상승)
- State 5: Grind Down (완만한 하락)
- State 6: Range Squeeze (횡보 및 수렴)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler

from .regime_feature_engine import RegimeFeatureEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    HMM 기반 시장 국면 탐지
    
    6개 상태:
    - State 1: Strong Bull
    - State 2: Strong Bear
    - State 3: Volatility Spike
    - State 4: Grind Up
    - State 5: Grind Down
    - State 6: Range Squeeze
    """
    
    REGIME_NAMES = {
        0: "strong_bull",
        1: "strong_bear",
        2: "volatility_spike",
        3: "grind_up",
        4: "grind_down",
        5: "range_squeeze"
    }
    
    def __init__(self, n_states: int = 6, n_iter: int = 100):
        """
        Args:
            n_states: 은닉 상태 개수 (기본값: 6)
            n_iter: HMM 학습 반복 횟수 (기본값: 100)
        """
        self.n_states = n_states
        self.n_iter = n_iter
        self.hmm_model = None
        self.feature_engine = RegimeFeatureEngine(n_components=4)
        self.fitted = False
    
    def fit(self, price_data: pd.DataFrame):
        """
        HMM 모델 학습
        
        Args:
            price_data: OHLCV 데이터프레임
        """
        logger.info(f"🔍 HMM 모델 학습 시작... (상태 수: {self.n_states})")
        
        # 1. 특징 추출
        features = self.feature_engine.extract_features(price_data)
        
        # 2. PCA 차원 축소
        features_pca, explained_variance = self.feature_engine.pca_reduce(features, fit=True)
        
        if explained_variance < 0.90:
            logger.warning(f"⚠️ PCA 설명력이 낮습니다: {explained_variance:.2%} (목표: 90% 이상)")
        
        # 3. HMM 학습
        self.hmm_model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=self.n_iter,
            random_state=42
        )
        
        self.hmm_model.fit(features_pca)
        self.fitted = True
        
        logger.info(f"✅ HMM 모델 학습 완료")
        logger.info(f"   학습 데이터: {len(features_pca)}개 샘플")
        logger.info(f"   PCA 설명력: {explained_variance:.2%}")
    
    def detect_regime(
        self,
        current_data: pd.DataFrame,
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        현재 국면 탐지
        
        Args:
            current_data: 현재 시장 데이터 (OHLCV)
            return_probabilities: 확률 분포 반환 여부
        
        Returns:
            국면 정보 딕셔너리
        """
        if not self.fitted:
            raise ValueError("HMM 모델이 학습되지 않았습니다. fit() 메서드를 먼저 실행하세요.")
        
        # 1. 특징 추출
        features = self.feature_engine.extract_features(current_data)
        
        # 2. PCA 변환 (학습된 모델 사용)
        features_pca, _ = self.feature_engine.pca_reduce(features, fit=False)
        
        # 3. 최근 데이터만 사용 (마지막 1개 샘플)
        if len(features_pca) > 1:
            features_pca = features_pca[-1:].reshape(1, -1)
        else:
            features_pca = features_pca.reshape(1, -1)
        
        # 4. Viterbi 알고리즘으로 최적 상태 추정
        state_sequence = self.hmm_model.predict(features_pca)
        dominant_state = int(state_sequence[0])
        dominant_regime = self.REGIME_NAMES[dominant_state]
        
        result = {
            "dominant_regime": dominant_regime,
            "dominant_state": dominant_state,
            "confidence": 1.0  # 기본값
        }
        
        # 5. 확률 분포 계산 (선택적)
        if return_probabilities:
            # 각 상태의 확률 계산
            log_probs = self.hmm_model.score_samples(features_pca)
            probs = np.exp(log_probs[0])  # 로그 확률을 확률로 변환
            
            # 정규화
            probs = probs / probs.sum()
            
            regime_probs = {
                self.REGIME_NAMES[i]: float(probs[i])
                for i in range(self.n_states)
            }
            
            result["probabilities"] = regime_probs
            result["confidence"] = float(probs[dominant_state])
        
        return result
    
    def get_regime_strategy_recommendation(self, regime: str) -> Dict[str, Any]:
        """
        국면별 전략 추천
        
        Args:
            regime: 국면 이름
        
        Returns:
            전략 추천 딕셔너리
        """
        recommendations = {
            "strong_bull": {
                "position_direction": "LONG",
                "position_size_multiplier": 1.2,  # 포지션 확대
                "preferred_theories": ["trend_following", "momentum"],
                "avoid_theories": ["mean_reversion"],
                "risk_level": "medium"
            },
            "strong_bear": {
                "position_direction": "SHORT",
                "position_size_multiplier": 0.8,  # 포지션 축소
                "preferred_theories": ["mean_reversion", "crisis_detection"],
                "avoid_theories": ["trend_following"],
                "risk_level": "high"
            },
            "volatility_spike": {
                "position_direction": "NEUTRAL",
                "position_size_multiplier": 0.5,  # 포지션 대폭 축소
                "preferred_theories": ["volatility_breakout"],
                "avoid_theories": ["trend_following", "mean_reversion"],
                "risk_level": "very_high"
            },
            "grind_up": {
                "position_direction": "LONG",
                "position_size_multiplier": 1.0,
                "preferred_theories": ["trend_following", "mean_reversion"],
                "avoid_theories": [],
                "risk_level": "low"
            },
            "grind_down": {
                "position_direction": "SHORT",
                "position_size_multiplier": 0.9,
                "preferred_theories": ["mean_reversion"],
                "avoid_theories": ["trend_following"],
                "risk_level": "medium"
            },
            "range_squeeze": {
                "position_direction": "NEUTRAL",
                "position_size_multiplier": 0.7,
                "preferred_theories": ["volatility_breakout", "mean_reversion"],
                "avoid_theories": ["trend_following"],
                "risk_level": "medium"
            }
        }
        
        return recommendations.get(regime, {
            "position_direction": "NEUTRAL",
            "position_size_multiplier": 1.0,
            "preferred_theories": [],
            "avoid_theories": [],
            "risk_level": "medium"
        })

