#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 이론 헌법 로더 (Theory Constitution Loader)

목적: 이론 헌법 문서를 파싱하고 적용하는 시스템
- 이론 헌법 문서 파싱
- 충돌 해결 규칙 적용
- 동적 가중치 조정
- 체질별 가중치 보정

작성일: 2026-01-23
"""

import sys
import os
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
import logging
import yaml
import json
import numpy as np

# 프로젝트 루트 경로 추가
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TheoryType import
try:
    from tools.core.theory_fusion_selector import TheoryType
    THEORY_TYPE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ TheoryType을 import할 수 없습니다. Enum으로 대체합니다.")
    from enum import Enum
    class TheoryType(Enum):
        CONTINUOUS_DYNAMICS = "continuous_dynamics"
        BAYESIAN_UPDATE = "bayesian_update"
        MARKOV_CHAIN = "markov_chain"
        HMM = "hmm"
        MCMC = "mcmc"
        BAYESIAN_NETWORK = "bayesian_network"
        REINFORCEMENT_LEARNING = "reinforcement_learning"
        HYBRID_FUSION = "hybrid_fusion"
        BAYESIAN_MARKOV = "bayesian_markov"
    THEORY_TYPE_AVAILABLE = False


class TheoryConstitutionLoader:
    """
    이론 헌법 로더
    
    핵심 기능:
    - 이론 헌법 문서 파싱
    - 충돌 해결 규칙 적용
    - 동적 가중치 조정
    - 체질별 가중치 보정
    """
    
    def __init__(self, constitution_file: Optional[Path] = None):
        """
        초기화
        
        Args:
            constitution_file: 이론 헌법 문서 경로 (선택적)
        """
        if constitution_file:
            self.constitution_file = Path(constitution_file)
        else:
            # 기본 경로: projects/bitcoin-trading/docs/Theory_Constitution.md
            self.constitution_file = WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "docs" / "Theory_Constitution.md"
        
        # 이론 헌법 데이터
        self.constitution_data: Dict[str, Any] = {}
        
        # Divine Centroid (Project Logos 0.25)
        self.divine_centroid = {
            "S": 0.249834,
            "L": 0.249714,
            "K": 0.250699,
            "M": 0.249754
        }
        
        # 기본 임계값
        self.default_thresholds = {
            "ipe_threshold": 0.15,  # IPE 임계값
            "divine_centroid_threshold": 0.2,  # Divine Centroid 거리 임계값
            "confidence_diff_threshold": 0.3  # 신뢰도 차이 임계값
        }
        
        # 이론 헌법 로드
        self.load_constitution()
    
    def load_constitution(self):
        """이론 헌법 문서 로드"""
        try:
            if not self.constitution_file.exists():
                logger.warning(f"⚠️ 이론 헌법 문서가 없습니다: {self.constitution_file}. 기본 규칙 사용.")
                self.constitution_data = self._get_default_constitution()
                return
            
            # Markdown 파일 파싱 (간단한 파싱)
            with open(self.constitution_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 기본 규칙 추출 (Markdown에서 코드 블록 파싱)
            self.constitution_data = self._parse_markdown_constitution(content)
            
            logger.info(f"✅ 이론 헌법 로드 완료: {self.constitution_file}")
            
        except Exception as e:
            logger.error(f"❌ 이론 헌법 로드 실패: {e}. 기본 규칙 사용.")
            self.constitution_data = self._get_default_constitution()
    
    def _parse_markdown_constitution(self, content: str) -> Dict[str, Any]:
        """
        Markdown 이론 헌법 문서 파싱
        
        Args:
            content: Markdown 내용
        
        Returns:
            파싱된 헌법 데이터
        """
        # 기본 규칙 구조
        constitution = {
            "rules": {
                "heatwave_veto": {
                    "enabled": True,
                    "ipe_threshold": 0.15,
                    "priority": 1  # 최우선
                },
                "divine_centroid_priority": {
                    "enabled": True,
                    "distance_threshold": 0.5,  # 🏛️ 아테나 v4.0 팩트 체크 수용: 0.2 → 0.5
                    "priority": 2
                },
                "confidence_diff_rule": {
                    "enabled": True,
                    "threshold": 0.3,
                    "priority": 3
                },
                "trend_vs_mean_reversion": {
                    "enabled": True,
                    "priority": 4
                }
            },
            "constitution_adjustments": {
                "SY": {  # 소양인
                    "REINFORCEMENT_LEARNING": +0.05,
                    "CONTINUOUS_DYNAMICS": -0.05
                },
                "TE": {  # 태음인
                    "MARKOV_CHAIN": +0.05,
                    "REINFORCEMENT_LEARNING": -0.05
                },
                "SE": {  # 소음인
                    "BAYESIAN_UPDATE": +0.05,
                    "MCMC": -0.05
                },
                "TY": {  # 태양인
                    "CONTINUOUS_DYNAMICS": +0.05,
                    "MARKOV_CHAIN": -0.05
                }
            }
        }
        
        return constitution
    
    def _get_default_constitution(self) -> Dict[str, Any]:
        """기본 이론 헌법 데이터"""
        return {
            "rules": {
                "heatwave_veto": {
                    "enabled": True,
                    "ipe_threshold": 0.15,
                    "priority": 1
                },
                "divine_centroid_priority": {
                    "enabled": True,
                    "distance_threshold": 0.5,  # 🏛️ 아테나 v4.0 팩트 체크 수용: 0.2 → 0.5
                    "priority": 2
                },
                "confidence_diff_rule": {
                    "enabled": True,
                    "threshold": 0.3,
                    "priority": 3
                },
                "trend_vs_mean_reversion": {
                    "enabled": True,
                    "priority": 4
                }
            },
            "constitution_adjustments": {
                "SY": {
                    "REINFORCEMENT_LEARNING": +0.05,
                    "CONTINUOUS_DYNAMICS": -0.05
                },
                "TE": {
                    "MARKOV_CHAIN": +0.05,
                    "REINFORCEMENT_LEARNING": -0.05
                },
                "SE": {
                    "BAYESIAN_UPDATE": +0.05,
                    "MCMC": -0.05
                },
                "TY": {
                    "CONTINUOUS_DYNAMICS": +0.05,
                    "MARKOV_CHAIN": -0.05
                }
            }
        }
    
    def apply_heatwave_veto(
        self,
        ipe_score: float,
        signal: str = "BUY",
        ipe_threshold: Optional[float] = None
    ) -> bool:
        """
        PMI-Nitro 거부권 적용 (The Heatwave Veto)
        
        Args:
            ipe_score: IPE 점수
            signal: 매매 신호 (BUY/SELL/HOLD)
            ipe_threshold: IPE 임계값 (선택적)
        
        Returns:
            True: 신호 차단, False: 신호 허용
        """
        if not self.constitution_data["rules"]["heatwave_veto"]["enabled"]:
            return False
        
        threshold = ipe_threshold or self.constitution_data["rules"]["heatwave_veto"]["ipe_threshold"]
        
        if ipe_score > threshold and signal == "BUY":
            logger.warning(
                f"🔥 PMI-Nitro 거부권: IPE={ipe_score:.3f} > {threshold}, "
                f"BUY 신호 차단"
            )
            return True  # 신호 차단
        
        return False  # 신호 허용
    
    def apply_divine_centroid_priority(
        self,
        vector_4d: Dict[str, float],
        threshold: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Logos 공명 우선권 적용 (Divine Centroid Priority)
        
        Args:
            vector_4d: 검증할 4D 벡터
            threshold: 거리 임계값 (선택적)
        
        Returns:
            (is_valid, distance) 튜플
        """
        if not self.constitution_data["rules"]["divine_centroid_priority"]["enabled"]:
            return True, 0.0
        
        threshold_value = threshold or self.constitution_data["rules"]["divine_centroid_priority"]["distance_threshold"]
        
        # 거리 계산
        distance = self._calculate_distance(vector_4d, self.divine_centroid)
        
        if distance > threshold_value:
            logger.warning(
                f"⚠️ Logos 공명 우선권: 거리={distance:.3f} > {threshold_value}, "
                f"환각으로 판단"
            )
            return False, distance  # 신호 무효
        
        return True, distance  # 신호 유효
    
    def _calculate_distance(
        self,
        vector_4d: Dict[str, float],
        divine_centroid: Dict[str, float]
    ) -> float:
        """
        Divine Centroid와의 거리 계산
        
        Args:
            vector_4d: 4D 벡터
            divine_centroid: Divine Centroid 벡터
        
        Returns:
            유클리드 거리
        """
        keys = ["S", "L", "K", "M"]
        diff = [
            vector_4d.get(key, 0.0) - divine_centroid.get(key, 0.0)
            for key in keys
        ]
        distance = np.sqrt(sum(d**2 for d in diff))
        return distance
    
    def resolve_confidence_conflict(
        self,
        theory_signals: Dict[TheoryType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        이론 간 신뢰도 차이 규칙 적용
        
        Args:
            theory_signals: 이론별 신호 딕셔너리
        
        Returns:
            최종 신호
        """
        if not self.constitution_data["rules"]["confidence_diff_rule"]["enabled"]:
            return self._weighted_fusion(theory_signals)
        
        threshold = self.constitution_data["rules"]["confidence_diff_rule"]["threshold"]
        
        # 이론별 신뢰도 추출
        confidences = {
            theory: signal.get('confidence', 0.5)
            for theory, signal in theory_signals.items()
        }
        
        if not confidences:
            return {"signal": "HOLD", "confidence": 0.0}
        
        # 최대/최소 신뢰도
        max_confidence = max(confidences.values())
        min_confidence = min(confidences.values())
        confidence_diff = max_confidence - min_confidence
        
        if confidence_diff >= threshold:
            # 높은 신뢰도 이론 우선
            best_theory = max(confidences, key=confidences.get)
            logger.info(
                f"✅ 신뢰도 차이 규칙: {best_theory.value} 우선 "
                f"(신뢰도 차이: {confidence_diff:.3f})"
            )
            return theory_signals[best_theory]
        
        # 가중치 기반 융합
        return self._weighted_fusion(theory_signals)
    
    def resolve_trend_vs_mean_reversion(
        self,
        trend_signal: Dict[str, Any],
        mean_reversion_signal: Dict[str, Any],
        ipe_score: float,
        ipe_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        추세 추종 vs 평균 회귀 충돌 해결
        
        Args:
            trend_signal: 추세 추종 신호
            mean_reversion_signal: 평균 회귀 신호
            ipe_score: IPE 점수
            ipe_threshold: IPE 임계값 (선택적)
        
        Returns:
            최종 신호
        """
        if not self.constitution_data["rules"]["trend_vs_mean_reversion"]["enabled"]:
            return trend_signal
        
        threshold = ipe_threshold or self.constitution_data["rules"]["heatwave_veto"]["ipe_threshold"]
        
        if ipe_score > threshold:
            # 화기운이 높으면 평균 회귀 우선
            logger.info(
                f"🔥 화기운 감지: 평균 회귀 이론 우선 (IPE={ipe_score:.3f})"
            )
            return mean_reversion_signal
        else:
            # 일반적인 경우: 추세 추종 우선
            return trend_signal
    
    def _weighted_fusion(
        self,
        theory_signals: Dict[TheoryType, Dict[str, Any]],
        weights: Optional[Dict[TheoryType, float]] = None
    ) -> Dict[str, Any]:
        """
        가중치 기반 융합 (Fallback)
        
        Args:
            theory_signals: 이론별 신호 딕셔너리
            weights: 이론별 가중치 (선택적)
        
        Returns:
            융합된 신호
        """
        if not theory_signals:
            return {"signal": "HOLD", "confidence": 0.0}
        
        # 가중치가 없으면 균등 가중치
        if weights is None:
            weights = {theory: 1.0 / len(theory_signals) for theory in theory_signals.keys()}
        
        # 신호별 가중 합계
        signal_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_confidence = 0.0
        
        for theory, signal_data in theory_signals.items():
            signal = signal_data.get("signal", "HOLD")
            confidence = signal_data.get("confidence", 0.5)
            weight = weights.get(theory, 0.0)
            
            if signal in signal_scores:
                signal_scores[signal] += weight * confidence
            
            total_confidence += weight * confidence
        
        # 최종 신호 결정
        final_signal = max(signal_scores, key=signal_scores.get)
        final_confidence = signal_scores[final_signal]
        
        return {
            "signal": final_signal,
            "confidence": final_confidence,
            "method": "weighted_fusion"
        }
    
    def apply_constitution_adjustment(
        self,
        domain: str,
        constitution: str,
        base_weights: Dict[TheoryType, float]
    ) -> Dict[TheoryType, float]:
        """
        체질별 가중치 보정 적용 (SLPT Rules)
        
        Args:
            domain: 도메인 (crypto_volatile)
            constitution: 체질 (SY, TE, SE, TY)
            base_weights: 기본 가중치
        
        Returns:
            보정된 가중치
        """
        if constitution not in self.constitution_data["constitution_adjustments"]:
            logger.warning(f"⚠️ 알 수 없는 체질: {constitution}. 가중치 보정 생략.")
            return base_weights
        
        adjusted_weights = base_weights.copy()
        adjustments = self.constitution_data["constitution_adjustments"][constitution]
        
        # 체질별 가중치 보정 적용
        for theory_name, adjustment in adjustments.items():
            try:
                # TheoryType으로 변환
                if THEORY_TYPE_AVAILABLE:
                    theory_type = TheoryType[theory_name]
                else:
                    # Enum 직접 사용
                    theory_type = TheoryType[theory_name]
                
                if theory_type in adjusted_weights:
                    adjusted_weights[theory_type] += adjustment
                    logger.debug(
                        f"📊 체질별 가중치 보정: {theory_type.value} "
                        f"{base_weights[theory_type]:.3f} → {adjusted_weights[theory_type]:.3f} "
                        f"(조정: {adjustment:+.3f})"
                    )
            except (KeyError, AttributeError) as e:
                logger.warning(f"⚠️ 이론 타입 변환 실패: {theory_name}, {e}")
        
        # 정규화 (합이 1.0이 되도록)
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {
                theory: weight / total
                for theory, weight in adjusted_weights.items()
            }
        else:
            logger.warning("⚠️ 가중치 합이 0입니다. 기본 가중치 사용.")
            return base_weights
        
        logger.info(
            f"✅ 체질별 가중치 보정 완료: {constitution} "
            f"(도메인: {domain})"
        )
        
        return adjusted_weights
    
    def resolve_conflicts(
        self,
        theory_signals: Dict[TheoryType, Dict[str, Any]],
        vector_4d: Optional[Dict[str, float]] = None,
        ipe_score: Optional[float] = None,
        weights: Optional[Dict[TheoryType, float]] = None
    ) -> Dict[str, Any]:
        """
        이론 간 충돌 해결 (통합 메서드)
        
        Args:
            theory_signals: 이론별 신호 딕셔너리
            vector_4d: 4D 벡터 (선택적, Divine Centroid 검증용)
            ipe_score: IPE 점수 (선택적, PMI-Nitro 거부권용)
            weights: 이론별 가중치 (선택적)
        
        Returns:
            최종 신호
        """
        if not theory_signals:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "no_signals"}
        
        # 1. PMI-Nitro 거부권 (최우선)
        if ipe_score is not None:
            # 모든 BUY 신호 확인
            buy_signals = [
                signal for signal in theory_signals.values()
                if signal.get("signal") == "BUY"
            ]
            
            if buy_signals and self.apply_heatwave_veto(ipe_score, "BUY"):
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "heatwave_veto",
                    "ipe_score": ipe_score
                }
        
        # 2. Logos 공명 우선권
        if vector_4d is not None:
            is_valid, distance = self.apply_divine_centroid_priority(vector_4d)
            if not is_valid:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "reason": "divine_centroid_priority",
                    "distance": distance
                }
        
        # 3. 이론 간 신뢰도 차이 규칙
        if len(theory_signals) > 1:
            result = self.resolve_confidence_conflict(theory_signals)
            if result.get("method") != "weighted_fusion":
                return result
        
        # 4. 가중치 기반 융합 (Fallback)
        return self._weighted_fusion(theory_signals, weights)


# === 사용 예시 ===

if __name__ == "__main__":
    # TheoryConstitutionLoader 초기화
    loader = TheoryConstitutionLoader()
    
    # 1. PMI-Nitro 거부권 테스트
    print("\n=== PMI-Nitro 거부권 테스트 ===")
    is_blocked = loader.apply_heatwave_veto(ipe_score=0.18, signal="BUY")
    print(f"IPE=0.18, BUY 신호 차단: {is_blocked}")
    
    # 2. Logos 공명 우선권 테스트
    print("\n=== Logos 공명 우선권 테스트 ===")
    vector_4d = {"S": 0.3, "L": 0.4, "K": 0.2, "M": 0.1}
    is_valid, distance = loader.apply_divine_centroid_priority(vector_4d)
    print(f"벡터 거리={distance:.3f}, 유효: {is_valid}")
    
    # 3. 체질별 가중치 보정 테스트
    print("\n=== 체질별 가중치 보정 테스트 ===")
    base_weights = {
        TheoryType.HMM: 0.25,
        TheoryType.CONTINUOUS_DYNAMICS: 0.15,
        TheoryType.REINFORCEMENT_LEARNING: 0.15,
        TheoryType.MARKOV_CHAIN: 0.20,
        TheoryType.MCMC: 0.15,
        TheoryType.BAYESIAN_UPDATE: 0.10
    }
    adjusted = loader.apply_constitution_adjustment(
        domain="crypto_volatile",
        constitution="SY",
        base_weights=base_weights
    )
    print("소양인(SY) 가중치 보정:")
    for theory, weight in adjusted.items():
        print(f"  {theory.value}: {weight:.3f}")
    
    print("\n✅ TheoryConstitutionLoader 테스트 완료!")

