#!/usr/bin/env python3
"""
계층적 국면 분류 시스템

매크로/스윙/마이크로 3단계 계층적 국면 분류:
- 매크로: 8일 이상의 장기 추세 (포트폴리오 롱/숏 노출 결정)
- 스윙: 2일 이상의 중기 추세 (전략별 자산 배분 조정)
- 마이크로: 3~9시간 단위의 단기 변동 (진입/청산 타이밍)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging

from .market_regime_detector import MarketRegimeDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HierarchicalRegimeClassifier:
    """
    계층적 국면 분류 (매크로/스윙/마이크로)
    
    상위 국면의 맥락 안에서 하위 국면을 해석하여
    단기적인 노이즈에 의한 휩소 손실을 줄임
    """
    
    def __init__(self):
        """계층적 국면 분류기 초기화"""
        # 매크로 국면 탐지기 (8일 이상)
        self.macro_detector = MarketRegimeDetector(n_states=6, n_iter=100)
        
        # 스윙 국면 탐지기 (2일 이상)
        self.swing_detector = MarketRegimeDetector(n_states=6, n_iter=100)
        
        # 마이크로 국면 탐지기 (3~9시간)
        self.micro_detector = MarketRegimeDetector(n_states=6, n_iter=100)
        
        self.fitted = False
    
    def fit(
        self,
        price_data: pd.DataFrame,
        macro_period: str = "8D",
        swing_period: str = "2D",
        micro_period: str = "3H"
    ):
        """
        모든 시간대 국면 탐지기 학습
        
        Args:
            price_data: OHLCV 데이터프레임
            macro_period: 매크로 기간 (기본값: "8D")
            swing_period: 스윙 기간 (기본값: "2D")
            micro_period: 마이크로 기간 (기본값: "3H")
        """
        logger.info("🚀 계층적 국면 분류기 학습 시작...")
        
        # 1. 매크로 국면 학습 (8일 이상)
        logger.info(f"📊 매크로 국면 학습 중... (기간: {macro_period})")
        macro_data = price_data.resample(macro_period).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(macro_data) >= 20:  # 최소 데이터 필요
            self.macro_detector.fit(macro_data)
            logger.info(f"✅ 매크로 국면 학습 완료: {len(macro_data)}개 샘플")
        else:
            logger.warning(f"⚠️ 매크로 국면 데이터 부족: {len(macro_data)}개 (최소 20개 필요)")
        
        # 2. 스윙 국면 학습 (2일 이상)
        logger.info(f"📊 스윙 국면 학습 중... (기간: {swing_period})")
        swing_data = price_data.resample(swing_period).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(swing_data) >= 20:
            self.swing_detector.fit(swing_data)
            logger.info(f"✅ 스윙 국면 학습 완료: {len(swing_data)}개 샘플")
        else:
            logger.warning(f"⚠️ 스윙 국면 데이터 부족: {len(swing_data)}개 (최소 20개 필요)")
        
        # 3. 마이크로 국면 학습 (3~9시간)
        logger.info(f"📊 마이크로 국면 학습 중... (기간: {micro_period})")
        micro_data = price_data.resample(micro_period).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(micro_data) >= 20:
            self.micro_detector.fit(micro_data)
            logger.info(f"✅ 마이크로 국면 학습 완료: {len(micro_data)}개 샘플")
        else:
            logger.warning(f"⚠️ 마이크로 국면 데이터 부족: {len(micro_data)}개 (최소 20개 필요)")
        
        self.fitted = True
        logger.info("✅ 계층적 국면 분류기 학습 완료")
    
    def classify_all_timeframes(
        self,
        price_data: pd.DataFrame,
        macro_period: str = "8D",
        swing_period: str = "2D",
        micro_period: str = "3H"
    ) -> Dict[str, Dict[str, Any]]:
        """
        모든 시간대 국면 분류
        
        Args:
            price_data: 현재 시장 데이터
            macro_period: 매크로 기간
            swing_period: 스윙 기간
            micro_period: 마이크로 기간
        
        Returns:
            모든 시간대 국면 정보 딕셔너리
        """
        if not self.fitted:
            raise ValueError("계층적 국면 분류기가 학습되지 않았습니다. fit() 메서드를 먼저 실행하세요.")
        
        results = {}
        
        # 1. 매크로 국면 분류
        try:
            macro_data = price_data.resample(macro_period).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(macro_data) >= 10:
                macro_regime = self.macro_detector.detect_regime(macro_data)
                results["macro"] = macro_regime
            else:
                results["macro"] = {
                    "dominant_regime": "unknown",
                    "confidence": 0.0,
                    "probabilities": {}
                }
        except Exception as e:
            logger.warning(f"⚠️ 매크로 국면 분류 실패: {e}")
            results["macro"] = {
                "dominant_regime": "unknown",
                "confidence": 0.0,
                "probabilities": {}
            }
        
        # 2. 스윙 국면 분류
        try:
            swing_data = price_data.resample(swing_period).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(swing_data) >= 10:
                swing_regime = self.swing_detector.detect_regime(swing_data)
                results["swing"] = swing_regime
            else:
                results["swing"] = {
                    "dominant_regime": "unknown",
                    "confidence": 0.0,
                    "probabilities": {}
                }
        except Exception as e:
            logger.warning(f"⚠️ 스윙 국면 분류 실패: {e}")
            results["swing"] = {
                "dominant_regime": "unknown",
                "confidence": 0.0,
                "probabilities": {}
            }
        
        # 3. 마이크로 국면 분류
        try:
            micro_data = price_data.resample(micro_period).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(micro_data) >= 10:
                micro_regime = self.micro_detector.detect_regime(micro_data)
                results["micro"] = micro_regime
            else:
                results["micro"] = {
                    "dominant_regime": "unknown",
                    "confidence": 0.0,
                    "probabilities": {}
                }
        except Exception as e:
            logger.warning(f"⚠️ 마이크로 국면 분류 실패: {e}")
            results["micro"] = {
                "dominant_regime": "unknown",
                "confidence": 0.0,
                "probabilities": {}
            }
        
        return results
    
    def get_hierarchical_recommendation(
        self,
        regime_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        계층적 국면 기반 종합 추천
        
        상위 국면의 맥락 안에서 하위 국면을 해석하여
        최종 전략 추천 생성
        
        Args:
            regime_results: classify_all_timeframes() 결과
        
        Returns:
            종합 전략 추천 딕셔너리
        """
        macro = regime_results.get("macro", {})
        swing = regime_results.get("swing", {})
        micro = regime_results.get("micro", {})
        
        # 매크로 국면: 전체 포트폴리오 롱/숏 노출 결정
        macro_regime = macro.get("dominant_regime", "unknown")
        macro_confidence = macro.get("confidence", 0.0)
        
        # 스윙 국면: 전략별 자산 배분 조정
        swing_regime = swing.get("dominant_regime", "unknown")
        swing_confidence = swing.get("confidence", 0.0)
        
        # 마이크로 국면: 구체적인 진입/청산 타이밍
        micro_regime = micro.get("dominant_regime", "unknown")
        micro_confidence = micro.get("confidence", 0.0)
        
        # 매크로 국면 기반 포트폴리오 노출 결정
        if macro_regime == "strong_bull":
            portfolio_exposure = "LONG"
            exposure_multiplier = 1.2
        elif macro_regime == "strong_bear":
            portfolio_exposure = "SHORT"
            exposure_multiplier = 0.8
        elif macro_regime == "volatility_spike":
            portfolio_exposure = "NEUTRAL"
            exposure_multiplier = 0.5
        else:
            portfolio_exposure = "NEUTRAL"
            exposure_multiplier = 1.0
        
        # 스윙 국면 기반 전략 배분
        swing_recommendation = self.swing_detector.get_regime_strategy_recommendation(swing_regime)
        
        # 마이크로 국면 기반 진입/청산 타이밍
        micro_recommendation = self.micro_detector.get_regime_strategy_recommendation(micro_regime)
        
        # 계층적 충돌 해결
        # 매크로와 마이크로가 충돌하면 매크로 우선 (보수적 접근)
        if portfolio_exposure == "LONG" and micro_regime == "strong_bear":
            logger.warning("⚠️ 계층적 충돌 감지: 매크로=LONG, 마이크로=BEAR → 보수적 접근")
            exposure_multiplier *= 0.7  # 포지션 축소
        
        # 종합 추천
        recommendation = {
            "portfolio_exposure": portfolio_exposure,
            "exposure_multiplier": exposure_multiplier,
            "macro_regime": macro_regime,
            "macro_confidence": macro_confidence,
            "swing_regime": swing_regime,
            "swing_confidence": swing_confidence,
            "swing_recommendation": swing_recommendation,
            "micro_regime": micro_regime,
            "micro_confidence": micro_confidence,
            "micro_recommendation": micro_recommendation,
            "overall_confidence": (macro_confidence + swing_confidence + micro_confidence) / 3.0
        }
        
        logger.info(
            f"📊 계층적 국면 추천: "
            f"매크로={macro_regime} ({macro_confidence:.1%}), "
            f"스윙={swing_regime} ({swing_confidence:.1%}), "
            f"마이크로={micro_regime} ({micro_confidence:.1%}), "
            f"포트폴리오 노출={portfolio_exposure}"
        )
        
        return recommendation

