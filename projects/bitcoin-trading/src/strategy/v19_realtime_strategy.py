#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.19 실시간 전략 (WebSocket 통합)

목적: v1.19 백테스트 전략을 실시간 WebSocket 데이터에 적용
- 필터 임계값 균형 조정 (v1.17과 v1.18의 중간값)
- 고전 지혜 필터 통합
- 19ms 내 위상 분석 및 매매 신호 생성

작성일: 2026-01-12
"""

import asyncio
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

# Divine Centroid (Project Logos)
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}


class V19RealtimeStrategy:
    """
    v1.19 실시간 전략
    
    v1.19 백테스트 전략의 핵심 파라미터를 실시간 WebSocket 데이터에 적용
    """
    
    def __init__(self, symbol: str = "BTCUSDT"):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
        """
        self.symbol = symbol
        
        # v1.19 필터 임계값 (균형 조정)
        self.entropy_threshold = 0.37  # v1.17: 0.35, v1.18: 0.40의 중간
        self.min_confidence_for_trade = 0.08  # v1.17: 0.09, v1.18: 0.07의 중간
        self.min_confidence_for_entry = 0.09  # v1.17: 0.10, v1.18: 0.08의 중간
        
        # 고전 지혜 필터 설정
        self.use_classical_wisdom = True
        self.myeongri_lambda_threshold = 0.55  # v1.17: 0.6, v1.18: 0.5의 중간
        self.logos_distance_threshold = 0.07  # v1.17: 0.06, v1.18: 0.08의 중간
        
        # 고전 지혜 완화 계수 (v1.19 감소)
        self.classical_wisdom_entropy_relaxation = 0.05  # v1.18: 0.08 → v1.19: 0.05
        self.both_classical_wisdom_entropy_relaxation = 0.10  # v1.18: 0.15 → v1.19: 0.10
        self.both_classical_wisdom_confidence_relaxation = 0.005  # v1.18: 0.01 → v1.19: 0.005
        
        # 가격 데이터 버퍼
        self.price_buffer = deque(maxlen=100)
        self.volume_buffer = deque(maxlen=100)
        
        # 위상 분석 결과 버퍼
        self.phase_results = deque(maxlen=50)
    
    def calculate_phase_entropy(
        self,
        vector_4d: Dict[str, float],
        price_data: Optional[List[float]] = None,
        volume_data: Optional[List[float]] = None
    ) -> float:
        """
        위상 엔트로피 계산 (v1.19 방식)
        
        Args:
            vector_4d: 4D 위상 벡터
            price_data: 가격 데이터 (선택적)
            volume_data: 거래량 데이터 (선택적)
        
        Returns:
            위상 엔트로피 값
        """
        # Divine Centroid와의 거리 계산
        distance = np.sqrt(
            sum((vector_4d[k] - DIVINE_CENTROID[k]) ** 2 for k in ["S", "L", "K", "M"])
        )
        
        # 벡터 거리 스케일링 (v1.13 방식)
        scaled_distance = min(1.0, distance * 10.0)
        
        # 변동성 엔트로피 (가격 데이터가 있을 때)
        volatility_entropy = 0.0
        if price_data and len(price_data) >= 2:
            price_changes = [abs(price_data[i] - price_data[i-1]) / price_data[i-1] 
                           for i in range(1, len(price_data))]
            if price_changes:
                volatility_entropy = min(1.0, np.std(price_changes) * 100)
        
        # 거래량 엔트로피 (거래량 데이터가 있을 때)
        volume_entropy = 0.0
        if volume_data and len(volume_data) >= 2:
            volume_changes = [abs(volume_data[i] - volume_data[i-1]) / (volume_data[i-1] + 1e-10)
                            for i in range(1, len(volume_data))]
            if volume_changes:
                volume_entropy = min(1.0, np.std(volume_changes) * 100)
        
        # 모멘텀 엔트로피 (가격 데이터가 있을 때)
        momentum_entropy = 0.0
        if price_data and len(price_data) >= 3:
            momentum = [(price_data[i] - price_data[i-2]) / price_data[i-2]
                       for i in range(2, len(price_data))]
            if momentum:
                momentum_entropy = min(1.0, abs(np.mean(momentum)) * 10)
        
        # 총 엔트로피 계산 (v1.13 가중치)
        total_entropy = (
            scaled_distance * 0.5 +  # 벡터 응축도 (50%)
            volatility_entropy * 0.167 +  # 변동성 (16.7%)
            volume_entropy * 0.167 +  # 거래량 (16.7%)
            momentum_entropy * 0.167  # 모멘텀 (16.7%)
        )
        
        return min(1.0, total_entropy)
    
    async def check_classical_wisdom(
        self,
        vector_4d: Dict[str, float],
        lambda_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        고전 지혜 필터 확인 (v1.19)
        
        Args:
            vector_4d: 4D 위상 벡터
            lambda_value: 명리 λ 값 (선택적)
        
        Returns:
            고전 지혜 필터 결과
        """
        myeongri_approved = False
        logos_approved = False
        
        # 명리 λ 확인
        if lambda_value is not None:
            if lambda_value > self.myeongri_lambda_threshold:
                myeongri_approved = True
        
        # 로고스 거리 확인
        distance = np.sqrt(
            sum((vector_4d[k] - DIVINE_CENTROID[k]) ** 2 for k in ["S", "L", "K", "M"])
        )
        if distance < self.logos_distance_threshold:
            logos_approved = True
        
        both_approved = myeongri_approved and logos_approved
        
        return {
            "myeongri_approved": myeongri_approved,
            "logos_approved": logos_approved,
            "both_approved": both_approved,
            "lambda_value": lambda_value,
            "logos_distance": distance,
        }
    
    async def analyze_realtime_signal(
        self,
        vector_4d: Dict[str, float],
        price_data: Optional[List[float]] = None,
        volume_data: Optional[List[float]] = None,
        lambda_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        실시간 매매 신호 분석 (v1.19 전략)
        
        Args:
            vector_4d: 4D 위상 벡터
            price_data: 가격 데이터 (선택적)
            volume_data: 거래량 데이터 (선택적)
            lambda_value: 명리 λ 값 (선택적)
        
        Returns:
            매매 신호 분석 결과
        """
        start_time = time.time()
        
        # 1. 위상 엔트로피 계산
        phase_entropy = self.calculate_phase_entropy(vector_4d, price_data, volume_data)
        
        # 2. 고전 지혜 필터 확인
        classical_wisdom_result = await self.check_classical_wisdom(vector_4d, lambda_value)
        classical_wisdom_approved = (
            classical_wisdom_result["myeongri_approved"] or
            classical_wisdom_result["logos_approved"]
        )
        
        # 3. 필터 임계값 조정 (고전 지혜 완화)
        adjusted_entropy_threshold = self.entropy_threshold
        adjusted_min_confidence = self.min_confidence_for_trade
        
        if classical_wisdom_result["both_approved"]:
            # 둘 다 찬성: 더 완화
            adjusted_entropy_threshold = (
                self.entropy_threshold + self.both_classical_wisdom_entropy_relaxation
            )
            adjusted_min_confidence = max(
                0.05,
                self.min_confidence_for_trade - self.both_classical_wisdom_confidence_relaxation
            )
        elif classical_wisdom_approved:
            # 하나 찬성: 약간 완화
            adjusted_entropy_threshold = (
                self.entropy_threshold + self.classical_wisdom_entropy_relaxation
            )
        
        # 4. 엔트로피 필터 적용
        if phase_entropy > adjusted_entropy_threshold:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": f"엔트로피 필터: {phase_entropy:.3f} > {adjusted_entropy_threshold:.3f}",
                "phase_entropy": phase_entropy,
                "classical_wisdom": classical_wisdom_result,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # 5. 신호 생성 (간단한 예시)
        # 실제로는 MKM12 전략의 복잡한 로직 사용
        if vector_4d["S"] > 0.3:
            signal = "LONG"
            confidence = min((vector_4d["S"] - 0.25) * 2, 1.0)
        elif vector_4d["S"] < 0.2:
            signal = "SHORT"
            confidence = min((0.25 - vector_4d["S"]) * 2, 1.0)
        else:
            signal = "HOLD"
            confidence = 0.5
        
        # 6. 신뢰도 필터 적용
        if signal != "HOLD" and confidence < adjusted_min_confidence:
            return {
                "signal": "HOLD",
                "confidence": confidence,
                "reason": f"신뢰도 부족: {confidence:.3f} < {adjusted_min_confidence:.3f}",
                "phase_entropy": phase_entropy,
                "classical_wisdom": classical_wisdom_result,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # 7. 진입 신뢰도 기준 확인
        if signal != "HOLD" and confidence < self.min_confidence_for_entry:
            return {
                "signal": "HOLD",
                "confidence": confidence,
                "reason": f"진입 기준 미달: {confidence:.3f} < {self.min_confidence_for_entry:.3f}",
                "phase_entropy": phase_entropy,
                "classical_wisdom": classical_wisdom_result,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # 8. 결과 저장
        result = {
            "signal": signal,
            "confidence": confidence,
            "vector_4d": vector_4d,
            "phase_entropy": phase_entropy,
            "classical_wisdom": classical_wisdom_result,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "timestamp": time.time(),
        }
        
        self.phase_results.append(result)
        
        return result
    
    def get_latest_signal(self) -> Optional[Dict[str, Any]]:
        """최신 매매 신호 조회"""
        if self.phase_results:
            return self.phase_results[-1]
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        if not self.phase_results:
            return {
                "total_signals": 0,
                "long_signals": 0,
                "short_signals": 0,
                "hold_signals": 0,
                "avg_confidence": 0.0,
                "avg_processing_time_ms": 0.0,
            }
        
        signals = [r["signal"] for r in self.phase_results]
        
        return {
            "total_signals": len(self.phase_results),
            "long_signals": signals.count("LONG"),
            "short_signals": signals.count("SHORT"),
            "hold_signals": signals.count("HOLD"),
            "avg_confidence": np.mean([r["confidence"] for r in self.phase_results]),
            "avg_processing_time_ms": np.mean([r["processing_time_ms"] for r in self.phase_results]),
        }

