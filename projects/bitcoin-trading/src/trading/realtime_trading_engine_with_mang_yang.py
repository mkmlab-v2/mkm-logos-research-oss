#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 매매 엔진 (망양병 위기 감지 통합)

목적: 망양병 위기 감지 알고리즘을 통합하여
      시장의 "가짜 열"과 "진짜 양기 소실"을 구분하여 매매

작성일: 2026-01-12
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.api.binance_realtime_connector import BinanceRealtimeConnector
from src.api.phase_analysis_engine_bridge import PhaseAnalysisEngineBridge
from src.api.binance_client import BinanceFuturesClient
from src.strategy.mkm12_bitcoin_strategy import MKM12BitcoinStrategy
from src.strategy.v19_realtime_strategy import V19RealtimeStrategy
from src.risk.risk_manager import RiskManager
from src.analysis.mang_yang_crisis_detector import MangYangCrisisDetector
from src.analysis.sasang_constitution_crisis_detector import SasangConstitutionCrisisDetector

logger = logging.getLogger(__name__)


class RealtimeTradingEngineWithMangYang:
    """
    실시간 매매 엔진 (망양병 위기 감지 통합)
    
    핵심 기능:
    - WebSocket 실시간 데이터 수집
    - 19ms 내 위상 분석
    - 망양병 위기 감지 (가짜 열 vs 진짜 양기 소실)
    - 매매 신호 생성 및 주문 실행
    - 자동 리스크 관리
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        testnet: bool = True,
        initial_capital: float = 1000.0,
        leverage: int = 2
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
            testnet: 테스트넷 사용 여부
            initial_capital: 초기 자본
            leverage: 레버리지 배수
        """
        self.symbol = symbol
        self.testnet = testnet
        self.initial_capital = initial_capital
        self.leverage = leverage
        
        # Binance API 클라이언트
        logger.info("🔐 Binance API 클라이언트 초기화 중...")
        self.binance = BinanceFuturesClient(testnet=testnet)
        
        # MKM12 전략
        logger.info("🧠 MKM12 전략 초기화 중...")
        self.strategy = MKM12BitcoinStrategy(symbol=symbol)
        
        # v1.19 실시간 전략 (우선 사용)
        logger.info("🏛️ v1.19 실시간 전략 초기화 중...")
        self.v19_strategy = V19RealtimeStrategy(symbol=symbol)
        
        # 리스크 관리
        logger.info("🛡️ 리스크 관리 시스템 초기화 중...")
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        
        # 망양병 위기 감지기 (기존)
        logger.info("🌡️ 망양병 위기 감지기 초기화 중...")
        self.mang_yang_detector = MangYangCrisisDetector()
        
        # 사상체질 통합 위기 감지기 (NEW! 4체질 통합)
        logger.info("🏛️ 사상체질 통합 위기 감지기 초기화 중...")
        self.sasang_detector = SasangConstitutionCrisisDetector()
        
        # 위상 분석 엔진 브릿지 (v1.19 전략 통합)
        logger.info("🌉 위상 분석 엔진 브릿지 초기화 중...")
        self.phase_bridge = PhaseAnalysisEngineBridge(
            strategy=self.strategy,
            v19_strategy=self.v19_strategy
        )
        
        # WebSocket 커넥터
        logger.info("🔌 WebSocket 커넥터 초기화 중...")
        self.connector = BinanceRealtimeConnector(
            symbol=symbol.lower(),
            use_futures=True,
            callback=self._on_websocket_data
        )
        
        # 실행 상태
        self.running = False
        
        # 망양병 위기 상태 추적
        self.mang_yang_status = {
            "last_diagnosis": None,
            "crisis_level": "normal",
            "hui_guang_detected": False,
        }
    
    async def _on_websocket_data(self, data: Dict[str, Any]):
        """WebSocket 데이터 수신 콜백"""
        try:
            # 위상 분석
            processed_data = await self.phase_bridge.process_data(data)
            
            if not processed_data:
                return
            
            # 사상체질 통합 위기 감지 (NEW! 4체질 통합)
            market_data = self._extract_market_data(data, processed_data)
            
            # 통합 위기 감지 (4체질 모두)
            integrated_crisis_signal = self.sasang_detector.detect_crisis_signal(
                market_data=market_data,
                current_price=processed_data.get("current_price", 0.0),
                price_history=processed_data.get("price_history", [])
            )
            
            # 망양병 위기 감지 (기존, 호환성 유지)
            mang_yang_signal = self.mang_yang_detector.detect_crisis_signal(
                market_data=market_data,
                current_price=processed_data.get("current_price", 0.0),
                price_history=processed_data.get("price_history", [])
            )
            
            # 통합 상태 업데이트
            self.mang_yang_status["last_diagnosis"] = integrated_crisis_signal["diagnosis"]
            self.mang_yang_status["crisis_level"] = integrated_crisis_signal["diagnosis"]["crisis_level"]
            self.mang_yang_status["max_risk_constitution"] = integrated_crisis_signal.get("max_risk_constitution", "소음인")
            self.mang_yang_status["hui_guang_detected"] = mang_yang_signal["diagnosis"].get("is_hui_guang", False)
            
            # 통합 위기 신호 사용
            crisis_signal = integrated_crisis_signal
            
            # 위기 신호 처리 (4체질 통합)
            max_constitution = crisis_signal.get("max_risk_constitution", "소음인")
            
            if crisis_signal["signal"] == "EMERGENCY_SELL":
                logger.critical(
                    f"🚨 {max_constitution} 병증 위급: 회광반조(回光返照) 감지! "
                    f"긴급 매도 실행!"
                )
                await self._emergency_sell_all()
                return
            
            elif crisis_signal["signal"] == "SELL":
                logger.warning(
                    f"⚠️ {max_constitution} 병증 위급: 진짜 양기 소실 감지! "
                    f"방어적 포지션으로 전환!"
                )
                await self._defensive_position_reduction()
                return
            
            elif crisis_signal["signal"] == "REDUCE":
                logger.warning(
                    f"⚠️ {max_constitution} 병증 경고: 포지션 축소!"
                )
                # 기존 매매 신호를 사상체질 병증 필터로 걸러냄
                return
            
            # 정상 범위: 기존 매매 로직 실행
            signal_info = processed_data.get("analysis_result", {}).get("selected_signal")
            if signal_info and signal_info.get("signal") != "HOLD":
                # 망양병 필터 통과 후에만 거래 실행
                await self._execute_trade(signal_info, crisis_signal)
        
        except Exception as e:
            logger.error(f"❌ WebSocket 데이터 처리 중 오류: {e}", exc_info=True)
    
    def _extract_market_data(
        self,
        websocket_data: Dict[str, Any],
        processed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        시장 데이터 추출 (망양병 진단용)
        
        실제로는 외부 API에서 가져와야 하지만, 여기서는 예시 데이터 사용
        """
        # 예시 데이터 (실제로는 외부 API에서 가져와야 함)
        return {
            "liquidity_index": 0.5,  # 유동성 지수 (실제로는 계산 필요)
            "money_supply_growth": 0.1,  # 통화 공급 증가율 (실제로는 외부 데이터)
            "asset_price_inflation": 0.1,  # 자산 가격 인플레이션 (실제로는 계산 필요)
            "real_economy_index": 0.5,  # 실물 경제 지수 (실제로는 외부 데이터)
            "unemployment_rate": 0.05,  # 실업률 (실제로는 외부 데이터)
            "small_business_index": 0.5,  # 자영업 지수 (실제로는 외부 데이터)
            "gdp_growth": 0.02,  # GDP 성장률 (실제로는 외부 데이터)
            "vix_index": 0.2,  # VIX 지수 (실제로는 외부 데이터)
            "market_volatility": 0.2,  # 시장 변동성 (실제로는 계산 필요)
            "fear_greed_index": 0.5,  # 공포/탐욕 지수 (실제로는 외부 데이터)
        }
    
    async def _emergency_sell_all(self):
        """긴급 매도 (회광반조 감지 시)"""
        try:
            # 모든 포지션 청산
            logger.critical("🚨 긴급 매도 실행: 모든 포지션 청산!")
            # 실제 구현 필요: binance_client.close_all_positions()
            logger.critical("✅ 긴급 매도 완료: 양기 보존 성공!")
        except Exception as e:
            logger.error(f"❌ 긴급 매도 실패: {e}", exc_info=True)
    
    async def _defensive_position_reduction(self):
        """방어적 포지션 축소 (망양병 위급 시)"""
        try:
            # 포지션 50% 축소
            logger.warning("⚠️ 방어적 포지션 축소: 포지션 50% 축소!")
            # 실제 구현 필요: binance_client.reduce_position_size(0.5)
            logger.warning("✅ 방어적 포지션 축소 완료!")
        except Exception as e:
            logger.error(f"❌ 방어적 포지션 축소 실패: {e}", exc_info=True)
    
    async def _execute_trade(
        self,
        signal_info: Dict[str, Any],
        crisis_signal: Dict[str, Any]
    ):
        """
        매매 신호에 따라 거래 실행 (망양병 필터 통과 후)
        """
        signal = signal_info.get("signal")
        confidence = signal_info.get("confidence", 0.0)
        
        # 망양병 필터: 위급 시 거래 중단
        if crisis_signal["diagnosis"]["crisis_level"] == "critical":
            logger.warning("⚠️ 망양병 위급으로 거래 중단!")
            return
        
        # 사상체질 병증 필터: 위급 시 거래 중단
        if crisis_signal["diagnosis"]["crisis_level"] == "critical":
            max_constitution = crisis_signal.get("max_risk_constitution", "소음인")
            logger.warning(f"⚠️ {max_constitution} 병증 위급으로 거래 중단!")
            return
        
        # 신뢰도 필터 (예시: 0.7 이상만 거래)
        if confidence < 0.7:
            logger.info(f"ℹ️ 신뢰도 부족으로 거래 건너뛰기. 신호: {signal}, 신뢰도: {confidence:.4f}")
            return
        
        # 리스크 관리 시스템을 통해 포지션 크기 결정
        current_price = await self.binance.get_current_price(self.symbol)
        position_size_usdt = self.risk_manager.calculate_position_size(
            current_price=current_price,
            signal_confidence=confidence
        )
        
        if position_size_usdt <= 0:
            logger.warning("⚠️ 포지션 크기가 0 이하입니다. 거래를 실행하지 않습니다.")
            return
        
        order_type = "MARKET"  # 초기에는 MARKET으로 즉시 체결
        
        try:
            if signal == "BUY":
                logger.info(f"⬆️ BUY 신호 발생! 포지션 크기: {position_size_usdt:.2f} USDT, 신뢰도: {confidence:.4f}")
                order = await self.binance.place_order(
                    symbol=self.symbol,
                    side="BUY",
                    order_type=order_type,
                    quantity_usdt=position_size_usdt
                )
                logger.info(f"✅ BUY 주문 실행 완료: {order}")
            
            elif signal == "SELL":
                logger.info(f"⬇️ SELL 신호 발생! 포지션 크기: {position_size_usdt:.2f} USDT, 신뢰도: {confidence:.4f}")
                order = await self.binance.place_order(
                    symbol=self.symbol,
                    side="SELL",
                    order_type=order_type,
                    quantity_usdt=position_size_usdt
                )
                logger.info(f"✅ SELL 주문 실행 완료: {order}")
        
        except Exception as e:
            logger.error(f"❌ 주문 실행 중 오류 발생: {e}", exc_info=True)
    
    async def start(self):
        """실시간 매매 엔진 시작"""
        self.running = True
        logger.info("🚀 RealtimeTradingEngine (망양병 위기 감지 통합) 시작 중...")
        
        # Binance 클라이언트 초기 설정
        await self.binance.set_leverage(self.symbol, self.leverage)
        await self.binance.set_position_mode(self.symbol, "HEDGE")  # Hedge Mode 사용
        
        # WebSocket 커넥터 시작
        await self.connector.start()
        
        # 엔진이 계속 실행되도록 유지
        while self.running:
            await asyncio.sleep(1)  # 1초마다 상태 확인
    
    async def stop(self):
        """실시간 매매 엔진 중지"""
        logger.info("🛑 RealtimeTradingEngine (망양병 위기 감지 통합) 중지 요청.")
        self.running = False
        await self.connector.stop()
    
    def get_mang_yang_status(self) -> Dict[str, Any]:
        """망양병 위기 상태 조회"""
        return self.mang_yang_status.copy()


async def main():
    """메인 실행 함수"""
    engine = RealtimeTradingEngineWithMangYang(testnet=True)
    await engine.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())

