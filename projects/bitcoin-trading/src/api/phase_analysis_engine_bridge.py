#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
위상 분석 엔진 브릿지

목적: 바이낸스 WebSocket 데이터를 위상 분석 엔진으로 전송
- 19ms 내 데이터 전송 보장
- 4D 위상 공간(S-L-K-M) 변환
- 실시간 위상 분석 및 매매 신호 생성

작성일: 2026-01-12
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from collections import deque
import numpy as np

# 예언서 전략 브릿지 import (안전하게)
try:
    from src.strategy.prophecy_strategy_bridge import ProphecyStrategyBridge
    PROPHECY_BRIDGE_AVAILABLE = True
except ImportError as e:
    PROPHECY_BRIDGE_AVAILABLE = False
    logging.warning(f"⚠️ ProphecyStrategyBridge import 실패: {e}")

logger = logging.getLogger(__name__)


class PhaseAnalysisEngineBridge:
    """
    위상 분석 엔진 브릿지
    
    바이낸스 WebSocket 데이터를 위상 분석 엔진으로 전송하고
    매매 신호를 생성하는 브릿지 역할
    
    예언서 전략 통합:
    - 심판/회복 벡터를 매매 신호의 보조 지표로 활용
    - 엔트로피 임계 상태 감지 시 매매 신호 조정 또는 차단
    """
    
    def __init__(self, strategy=None, v19_strategy=None, enable_prophecy=True):
        """
        초기화
        
        Args:
            strategy: MKM12BitcoinStrategy 인스턴스 (선택적)
            v19_strategy: V19RealtimeStrategy 인스턴스 (선택적, v1.19 전략)
            enable_prophecy: 예언서 전략 활성화 여부 (기본값: True)
        """
        self.strategy = strategy
        self.v19_strategy = v19_strategy
        self.enable_prophecy = enable_prophecy
        
        # 예언서 전략 브릿지 초기화
        self.prophecy_bridge = None
        if enable_prophecy and PROPHECY_BRIDGE_AVAILABLE:
            try:
                self.prophecy_bridge = ProphecyStrategyBridge()
                logger.info("✅ ProphecyStrategyBridge 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ ProphecyStrategyBridge 초기화 실패: {e}")
                self.prophecy_bridge = None
        
        # 데이터 큐
        self.data_queue = asyncio.Queue(maxsize=1000)
        
        # 위상 분석 결과
        self.phase_analysis_results = deque(maxlen=100)
        
        # 성능 메트릭
        self.metrics = {
            "data_received": 0,
            "data_processed": 0,
            "signals_generated": 0,
            "signals_adjusted_by_prophecy": 0,  # 예언서 전략으로 조정된 신호 수
            "avg_processing_time_ms": 0,
        }
        
        # 처리 루프 실행 중 여부
        self.running = False
    
    async def receive_data(self, data: Dict[str, Any]):
        """
        바이낸스 WebSocket 데이터 수신
        
        Args:
            data: WebSocket 데이터 (type, data, timestamp, symbol)
        """
        try:
            await asyncio.wait_for(
                self.data_queue.put(data),
                timeout=0.001  # 1ms 타임아웃
            )
            self.metrics["data_received"] += 1
        except asyncio.TimeoutError:
            logger.warning("⚠️ 데이터 큐가 가득 참, 메시지 드롭")
        except Exception as e:
            logger.error(f"❌ 데이터 수신 오류: {e}")
    
    async def process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        데이터를 위상 분석 엔진으로 전송 및 처리
        
        Args:
            data: WebSocket 데이터
        
        Returns:
            위상 분석 결과 또는 None
        """
        start_time = time.time()
        
        try:
            data_type = data.get("type")
            payload = data.get("data", {})
            timestamp = data.get("timestamp", time.time())
            symbol = data.get("symbol", "BTCUSDT")
            
            # 데이터 타입별 처리
            if data_type == "depth":
                # 호가창 데이터 → 4D 위상 공간 변환
                phase_vector = self._depth_to_phase_vector(payload)
                # 가격/거래량 데이터 추출
                price_data = [float(bid[0]) for bid in payload.get("bids", [])[:10]]
                volume_data = [float(bid[1]) for bid in payload.get("bids", [])[:10]]
                analysis_result = await self._analyze_phase(
                    phase_vector, timestamp, price_data, volume_data
                )
                
            elif data_type == "trade":
                # 거래 데이터 → 4D 위상 공간 변환
                phase_vector = self._trade_to_phase_vector(payload)
                price_data = [float(payload.get("p", 0))]
                volume_data = [float(payload.get("q", 0))]
                analysis_result = await self._analyze_phase(
                    phase_vector, timestamp, price_data, volume_data
                )
                
            elif data_type == "ticker":
                # 틱커 데이터 → 4D 위상 공간 변환
                phase_vector = self._ticker_to_phase_vector(payload)
                price_data = [float(payload.get("c", 0))]  # 현재 가격
                volume_data = [float(payload.get("v", 0))]  # 24시간 거래량
                analysis_result = await self._analyze_phase(
                    phase_vector, timestamp, price_data, volume_data
                )
                
            elif data_type == "kline":
                # 캔들 데이터 → 4D 위상 공간 변환
                phase_vector = self._kline_to_phase_vector(payload)
                price_data = [
                    float(payload.get("o", 0)),  # 시가
                    float(payload.get("h", 0)),  # 고가
                    float(payload.get("l", 0)),  # 저가
                    float(payload.get("c", 0)),  # 종가
                ]
                volume_data = [float(payload.get("v", 0))]  # 거래량
                analysis_result = await self._analyze_phase(
                    phase_vector, timestamp, price_data, volume_data
                )
            
            else:
                return None
            
            # 예언서 전략으로 매매 신호 조정 (신규 추가)
            if analysis_result and self.prophecy_bridge:
                try:
                    # 시장 데이터 준비
                    market_data = {
                        "price": price_data[0] if price_data else 0.0,
                        "volume": sum(volume_data) if volume_data else 0.0,
                        "volatility": self._calculate_volatility(price_data) if price_data else 0.0,
                        "price_change_24h": 0.0  # 실제로는 24시간 전 가격과 비교 필요
                    }
                    
                    # 예언서 전략 분석
                    prophecy_analysis = self.prophecy_bridge.analyze_market_data(market_data)
                    
                    # 매매 신호 조정
                    if prophecy_analysis.get("available", False):
                        original_signal = {
                            "signal": analysis_result.get("signal", "HOLD"),
                            "confidence": analysis_result.get("confidence", 0.0)
                        }
                        
                        adjusted_signal = self.prophecy_bridge.adjust_trading_signal(
                            original_signal,
                            prophecy_analysis
                        )
                        
                        # 조정된 신호로 업데이트
                        if adjusted_signal.get("prophecy_adjustment", False):
                            analysis_result["signal"] = adjusted_signal["signal"]
                            analysis_result["confidence"] = adjusted_signal["confidence"]
                            analysis_result["prophecy_adjustment"] = True
                            analysis_result["prophecy_reason"] = adjusted_signal.get("reason", "")
                            self.metrics["signals_adjusted_by_prophecy"] += 1
                            
                            logger.info(
                                f"🏛️ 예언서 전략 신호 조정: {original_signal['signal']} → {adjusted_signal['signal']} "
                                f"(이유: {adjusted_signal.get('reason', 'N/A')})"
                            )
                        
                        # 예언서 분석 결과 추가
                        analysis_result["prophecy_analysis"] = {
                            "entropy_max_detected": prophecy_analysis.get("entropy_max_detected", False),
                            "recovery_detected": prophecy_analysis.get("recovery_detected", False),
                            "harmonic_info": prophecy_analysis.get("harmonic_info")
                        }
                
                except Exception as e:
                    logger.warning(f"⚠️ 예언서 전략 적용 오류: {e}")
                    # 오류가 발생해도 원본 신호는 유지
            
            # 결과 저장
            if analysis_result:
                self.phase_analysis_results.append(analysis_result)
                self.metrics["data_processed"] += 1
                
                # 매매 신호 생성
                if analysis_result.get("signal") in ["LONG", "SHORT"]:
                    self.metrics["signals_generated"] += 1
                    logger.info(
                        f"📊 매매 신호 생성: {analysis_result['signal']} "
                        f"(신뢰도: {analysis_result.get('confidence', 0):.2%})"
                    )
            
            # 성능 메트릭 업데이트
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_avg_processing_time(processing_time_ms)
            
            return analysis_result
        
        except Exception as e:
            logger.error(f"❌ 데이터 처리 오류: {e}")
            return None
    
    def _depth_to_phase_vector(self, depth_data: Dict[str, Any]) -> Dict[str, float]:
        """
        호가창 데이터를 4D 위상 벡터로 변환
        
        Args:
            depth_data: 호가창 데이터
        
        Returns:
            4D 위상 벡터 (S, L, K, M)
        """
        bids = depth_data.get("bids", [])
        asks = depth_data.get("asks", [])
        
        if not bids or not asks:
            return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
        
        # 매수/매도 호가 분석
        bid_volume = sum(float(qty) for _, qty in bids[:10])
        ask_volume = sum(float(qty) for _, qty in asks[:10])
        total_volume = bid_volume + ask_volume
        
        if total_volume == 0:
            return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
        
        # 4D 위상 벡터 계산
        # S (Spirit): 매수 압력 (bid_volume 비율)
        S = bid_volume / total_volume
        
        # L (Logic): 호가창 깊이 (매수/매도 균형)
        depth_ratio = len(bids) / (len(bids) + len(asks)) if (len(bids) + len(asks)) > 0 else 0.5
        L = depth_ratio
        
        # K (Knowledge): 가격 변동성 (스프레드 기반)
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        spread = (best_ask - best_bid) / best_bid
        K = min(spread * 100, 1.0)  # 정규화
        
        # M (Material): 거래량 강도
        M = min(total_volume / 1000, 1.0)  # 정규화
        
        # 정규화 (합이 1.0이 되도록)
        total = S + L + K + M
        if total > 0:
            return {
                "S": S / total,
                "L": L / total,
                "K": K / total,
                "M": M / total
            }
        
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    def _trade_to_phase_vector(self, trade_data: Dict[str, Any]) -> Dict[str, float]:
        """
        거래 데이터를 4D 위상 벡터로 변환
        
        Args:
            trade_data: 거래 데이터
        
        Returns:
            4D 위상 벡터 (S, L, K, M)
        """
        # 거래 데이터는 간단한 변환
        # 실제로는 여러 거래를 누적하여 분석
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    def _ticker_to_phase_vector(self, ticker_data: Dict[str, Any]) -> Dict[str, float]:
        """
        틱커 데이터를 4D 위상 벡터로 변환
        
        Args:
            ticker_data: 틱커 데이터
        
        Returns:
            4D 위상 벡터 (S, L, K, M)
        """
        price_change = float(ticker_data.get("P", 0))  # 24시간 가격 변동률
        volume = float(ticker_data.get("v", 0))  # 24시간 거래량
        
        # 4D 위상 벡터 계산
        S = 0.5 + (price_change / 100) if price_change > 0 else 0.5 - abs(price_change / 100)
        S = max(0.0, min(1.0, S))  # 0~1 범위로 제한
        
        L = 0.5  # 기본값
        K = min(volume / 1000000, 1.0)  # 정규화
        M = 0.5  # 기본값
        
        # 정규화
        total = S + L + K + M
        if total > 0:
            return {
                "S": S / total,
                "L": L / total,
                "K": K / total,
                "M": M / total
            }
        
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    def _kline_to_phase_vector(self, kline_data: Dict[str, Any]) -> Dict[str, float]:
        """
        캔들 데이터를 4D 위상 벡터로 변환
        
        Args:
            kline_data: 캔들 데이터
        
        Returns:
            4D 위상 벡터 (S, L, K, M)
        """
        open_price = float(kline_data.get("o", 0))
        close_price = float(kline_data.get("c", 0))
        high_price = float(kline_data.get("h", 0))
        low_price = float(kline_data.get("l", 0))
        volume = float(kline_data.get("v", 0))
        
        if open_price == 0:
            return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
        
        # 4D 위상 벡터 계산
        price_change = (close_price - open_price) / open_price
        
        # S (Spirit): 가격 변동 방향
        S = 0.5 + price_change * 10
        S = max(0.0, min(1.0, S))
        
        # L (Logic): 캔들 패턴 (상승/하락 강도)
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        L = body / total_range if total_range > 0 else 0.5
        
        # K (Knowledge): 변동성
        volatility = (high_price - low_price) / open_price
        K = min(volatility * 100, 1.0)
        
        # M (Material): 거래량
        M = min(volume / 1000, 1.0)
        
        # 정규화
        total = S + L + K + M
        if total > 0:
            return {
                "S": S / total,
                "L": L / total,
                "K": K / total,
                "M": M / total
            }
        
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    
    async def _analyze_phase(
        self,
        phase_vector: Dict[str, float],
        timestamp: float,
        price_data: Optional[List[float]] = None,
        volume_data: Optional[List[float]] = None,
        lambda_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        위상 분석 수행 (v1.19 전략 우선)
        
        Args:
            phase_vector: 4D 위상 벡터
            timestamp: 타임스탬프
            price_data: 가격 데이터 (선택적)
            volume_data: 거래량 데이터 (선택적)
            lambda_value: 명리 λ 값 (선택적)
        
        Returns:
            위상 분석 결과
        """
        # v1.19 전략 우선 사용
        if self.v19_strategy:
            try:
                result = await self.v19_strategy.analyze_realtime_signal(
                    vector_4d=phase_vector,
                    price_data=price_data,
                    volume_data=volume_data,
                    lambda_value=lambda_value
                )
                result["timestamp"] = timestamp
                return result
            except Exception as e:
                logger.error(f"❌ v1.19 전략 분석 오류: {e}")
        
        # Fallback: MKM12 전략
        if self.strategy:
            try:
                # MKM12 전략으로 분석
                # (실제로는 strategy.analyze_market() 호출)
                # 여기서는 간단한 예시만 제공
                
                # Divine Centroid와의 거리 계산
                divine_centroid = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
                distance = np.sqrt(
                    sum((phase_vector[k] - divine_centroid[k]) ** 2 for k in ["S", "L", "K", "M"])
                )
                
                # 신호 생성 (간단한 예시)
                if distance > 0.1:
                    if phase_vector["S"] > 0.3:
                        signal = "LONG"
                        confidence = min(distance * 2, 1.0)
                    elif phase_vector["S"] < 0.2:
                        signal = "SHORT"
                        confidence = min(distance * 2, 1.0)
                    else:
                        signal = "HOLD"
                        confidence = 0.5
                else:
                    signal = "HOLD"
                    confidence = 0.5
                
                return {
                    "vector_4d": phase_vector,
                    "timestamp": timestamp,
                    "signal": signal,
                    "confidence": confidence,
                    "distance_to_centroid": distance,
                }
            except Exception as e:
                logger.error(f"❌ MKM12 전략 분석 오류: {e}")
        
        # 기본 분석 (전략이 없을 때)
        return {
            "vector_4d": phase_vector,
            "timestamp": timestamp,
            "signal": "HOLD",
            "confidence": 0.5,
        }
    
    def _calculate_volatility(self, price_data: Optional[List[float]]) -> float:
        """
        변동성 계산
        
        Args:
            price_data: 가격 데이터 리스트
            
        Returns:
            변동성 (0.0 ~ 1.0)
        """
        if not price_data or len(price_data) < 2:
            return 0.0
        
        try:
            prices = np.array(price_data)
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) if len(returns) > 0 else 0.0
            return float(min(abs(volatility) * 100, 1.0))  # 정규화
        except Exception:
            return 0.0
    
    def _update_avg_processing_time(self, processing_time_ms: float):
        """평균 처리 시간 업데이트"""
        current_avg = self.metrics["avg_processing_time_ms"]
        count = self.metrics["data_processed"]
        
        if count == 0:
            self.metrics["avg_processing_time_ms"] = processing_time_ms
        else:
            # 이동 평균
            self.metrics["avg_processing_time_ms"] = (
                (current_avg * (count - 1) + processing_time_ms) / count
            )
    
    async def process_loop(self):
        """데이터 처리 루프"""
        self.running = True
        logger.info("🔄 위상 분석 엔진 브릿지 처리 루프 시작")
        
        while self.running:
            try:
                # 데이터 가져오기 (논블로킹)
                try:
                    data = await asyncio.wait_for(
                        self.data_queue.get(),
                        timeout=0.1  # 100ms 타임아웃
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 데이터 처리
                await self.process_data(data)
            
            except Exception as e:
                logger.error(f"❌ 처리 루프 오류: {e}")
                await asyncio.sleep(0.1)
    
    def stop(self):
        """처리 루프 중지"""
        self.running = False
        logger.info("⏹️ 위상 분석 엔진 브릿지 처리 루프 중지")
    
    def get_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        return self.metrics.copy()
    
    def get_latest_signal(self) -> Optional[Dict[str, Any]]:
        """최신 매매 신호 조회"""
        for result in reversed(self.phase_analysis_results):
            if result.get("signal") in ["LONG", "SHORT"]:
                return result
        return None

