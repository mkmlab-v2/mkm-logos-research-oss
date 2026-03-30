#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📈 압축-트레이딩 브릿지

압축 엔진과 트레이딩 시스템을 연결하는 브릿지 모듈

핵심 기능:
1. 시장 데이터 압축 (노이즈 제거)
2. 압축 벡터에서 트레이딩 신호 추출
3. 신호 강도 및 신뢰도 계산

작성일: 2026-02-06
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from tools.core.unified_compression_api import get_unified_compression_api
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False
    logger.warning("⚠️ 압축 API를 사용할 수 없습니다. 압축 기능이 비활성화됩니다.")


class CompressionTradingBridge:
    """
    압축-트레이딩 브릿지 클래스
    
    시장 데이터를 압축하여 노이즈를 제거하고, 
    압축된 벡터에서 트레이딩 신호를 추출합니다.
    """
    
    def __init__(self, enable_compression: bool = True):
        """
        초기화
        
        Args:
            enable_compression: 압축 기능 활성화 여부
        """
        self.enable_compression = enable_compression and COMPRESSION_AVAILABLE
        
        if self.enable_compression:
            try:
                self.compression_api = get_unified_compression_api()
                logger.info("✅ 압축-트레이딩 브릿지 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 압축 API 초기화 실패: {e}")
                self.enable_compression = False
        else:
            self.compression_api = None
            logger.info("ℹ️ 압축 기능 비활성화됨")
        
        # 통계
        self.compression_count = 0
        self.total_noise_filtered = 0.0
        self.total_processing_time = 0.0
    
    def _market_data_to_string(self, price_data: pd.DataFrame) -> str:
        """
        시장 데이터를 압축 엔진 입력용 문자열로 변환
        
        Args:
            price_data: 가격 데이터 DataFrame
            
        Returns:
            시장 데이터 문자열
        """
        lines = []
        for idx, row in price_data.iterrows():
            line = (
                f"T:{idx} "
                f"O:{row.get('open', 0):.2f} "
                f"H:{row.get('high', 0):.2f} "
                f"L:{row.get('low', 0):.2f} "
                f"C:{row.get('close', 0):.2f} "
                f"V:{row.get('volume', 0):.0f}"
            )
            lines.append(line)
        
        return "\n".join(lines)
    
    async def compress_market_data(
        self,
        price_data: pd.DataFrame,
        compression_mode: str = "max_compression"
    ) -> Dict[str, Any]:
        """
        시장 데이터 압축 (노이즈 제거)
        
        Args:
            price_data: 가격 데이터 DataFrame
            compression_mode: 압축 모드 ("max_compression", "hybrid", "perfect_restoration")
            
        Returns:
            압축 결과 딕셔너리
        """
        if not self.enable_compression or not self.compression_api:
            # 압축 비활성화 시 기본값 반환
            return {
                "compressed": False,
                "compressed_vector": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
                "noise_level": 0.25,
                "signal_strength": 0.25,
                "noise_filtered": 0.0,
                "compression_ratio": 1.0
            }
        
        try:
            import time
            start_time = time.perf_counter()
            
            # 시장 데이터를 문자열로 변환
            market_data_str = self._market_data_to_string(price_data)
            
            # 압축 실행
            compression_result = await self.compression_api.compress(
                text=market_data_str,
                compression_mode=compression_mode,
                domain="trading",
                min_length=100  # 트레이딩 데이터는 짧아도 압축
            )
            
            processing_time = (time.perf_counter() - start_time) * 1000  # ms
            
            # 압축 결과에서 4D 벡터 추출
            compressed_data = compression_result.compressed_data
            
            # 4D 벡터 추출 (압축 데이터에서)
            compressed_vector = {
                "S": compressed_data.get("vector_4d", {}).get("S", 0.25),
                "L": compressed_data.get("vector_4d", {}).get("L", 0.25),
                "K": compressed_data.get("vector_4d", {}).get("K", 0.25),
                "M": compressed_data.get("vector_4d", {}).get("M", 0.25)
            }
            
            # 메트릭 추출
            metrics = compression_result.metrics
            compression_ratio = metrics.get("compression_ratio", 0.99)
            
            # 노이즈 레벨 (S 차원 = 소음)
            noise_level = compressed_vector.get("S", 0.25)
            
            # 신호 강도 (L 차원 = 논리/알파)
            signal_strength = compressed_vector.get("L", 0.25)
            
            # 필터링된 노이즈 비율
            noise_filtered = 1.0 - noise_level
            
            # 통계 업데이트
            self.compression_count += 1
            self.total_noise_filtered += noise_filtered
            self.total_processing_time += processing_time
            
            logger.debug(
                f"📊 압축 완료: "
                f"노이즈 필터링={noise_filtered:.1%}, "
                f"신호 강도={signal_strength:.3f}, "
                f"처리 시간={processing_time:.1f}ms"
            )
            
            return {
                "compressed": True,
                "compressed_vector": compressed_vector,
                "noise_level": noise_level,
                "signal_strength": signal_strength,
                "information_level": compressed_vector.get("K", 0.25),
                "market_pressure": compressed_vector.get("M", 0.25),
                "noise_filtered": noise_filtered,
                "compression_ratio": compression_ratio,
                "processing_time_ms": processing_time,
                "original_size": len(market_data_str.encode('utf-8')),
                "compressed_size": len(market_data_str.encode('utf-8')) * compression_ratio
            }
        
        except Exception as e:
            logger.error(f"❌ 압축 실패: {e}")
            # 실패 시 기본값 반환
            return {
                "compressed": False,
                "compressed_vector": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
                "noise_level": 0.25,
                "signal_strength": 0.25,
                "noise_filtered": 0.0,
                "compression_ratio": 1.0,
                "error": str(e)
            }
    
    def extract_trading_signal_from_compression(
        self,
        compressed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        압축된 데이터에서 트레이딩 신호 추출
        
        Args:
            compressed_data: 압축 결과 딕셔너리
            
        Returns:
            트레이딩 신호 딕셔너리
        """
        if not compressed_data.get("compressed", False):
            # 압축되지 않은 경우 기본 신호
            return {
                "signal": "HOLD",
                "confidence": 0.5,
                "signal_strength": 0.25,
                "noise_filtered": 0.0
            }
        
        compressed_vector = compressed_data["compressed_vector"]
        signal_strength = compressed_data["signal_strength"]
        noise_level = compressed_data["noise_level"]
        market_pressure = compressed_data["market_pressure"]
        information_level = compressed_data["information_level"]
        
        # 신호 추출 로직
        # L(논리)이 높고 S(소음)가 낮으면 강한 신호
        signal_ratio = signal_strength / (noise_level + 0.01)  # 0으로 나누기 방지
        
        # 매수/매도/보유 결정
        if signal_ratio > 1.5 and market_pressure > 0.3:
            signal = "BUY"
            confidence = min(1.0, signal_ratio / 2.0)
        elif signal_ratio < 0.7 and market_pressure < 0.2:
            signal = "SELL"
            confidence = min(1.0, (1.0 - signal_ratio) / 2.0)
        else:
            signal = "HOLD"
            confidence = 0.5
        
        # 신뢰도 보정 (정보량과 노이즈 필터링 비율 고려)
        noise_filtered = compressed_data["noise_filtered"]
        confidence_boost = noise_filtered * 0.2  # 노이즈 필터링이 많을수록 신뢰도 증가
        confidence = min(1.0, confidence + confidence_boost)
        
        return {
            "signal": signal,
            "confidence": confidence,
            "signal_strength": signal_strength,
            "noise_filtered": noise_filtered,
            "compressed_vector": compressed_vector,
            "signal_ratio": signal_ratio
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        통계 정보 반환
        
        Returns:
            통계 딕셔너리
        """
        avg_noise_filtered = (
            self.total_noise_filtered / self.compression_count
            if self.compression_count > 0
            else 0.0
        )
        
        avg_processing_time = (
            self.total_processing_time / self.compression_count
            if self.compression_count > 0
            else 0.0
        )
        
        return {
            "compression_enabled": self.enable_compression,
            "compression_count": self.compression_count,
            "avg_noise_filtered": avg_noise_filtered,
            "avg_processing_time_ms": avg_processing_time,
            "total_processing_time_ms": self.total_processing_time
        }

