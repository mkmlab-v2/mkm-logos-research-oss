#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 매매 엔진 (WebSocket 통합)

목적: 바이낸스 WebSocket 실시간 데이터를 받아서
      19ms 내 위상 분석 → 매매 신호 생성 → 주문 실행

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

logger = logging.getLogger(__name__)


class RealtimeTradingEngine:
    """
    실시간 매매 엔진
    
    핵심 기능:
    - WebSocket 실시간 데이터 수집
    - 19ms 내 위상 분석
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
        
        # 위상 분석 엔진 브릿지 (v1.19 전략 + 예언서 전략 통합)
        logger.info("🌉 위상 분석 엔진 브릿지 초기화 중...")
        self.phase_bridge = PhaseAnalysisEngineBridge(
            strategy=self.strategy,
            v19_strategy=self.v19_strategy,
            enable_prophecy=True  # 예언서 전략 활성화
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
    
    async def _on_websocket_data(self, data: Dict[str, Any]):
        """WebSocket 데이터 수신 콜백"""
        try:
            # 위상 분석 엔진 브릿지로 전송
            await self.phase_bridge.receive_data(data)
        except Exception as e:
            logger.error(f"❌ WebSocket 데이터 처리 오류: {e}")
    
    async def _process_trading_signals(self):
        """매매 신호 처리 루프"""
        logger.info("📊 매매 신호 처리 루프 시작")
        
        while self.running:
            try:
                # 위상 분석 결과 확인
                signal = self.phase_bridge.get_latest_signal()
                
                if signal and signal.get("signal") in ["LONG", "SHORT"]:
                    confidence = signal.get("confidence", 0.0)
                    
                    # 신뢰도 검증 (최소 0.7 이상)
                    if confidence >= 0.7:
                        await self._execute_trade(signal)
                
                # 100ms마다 체크
                await asyncio.sleep(0.1)
            
            except Exception as e:
                logger.error(f"❌ 매매 신호 처리 오류: {e}")
                await asyncio.sleep(0.1)
    
    async def _execute_trade(self, signal: Dict[str, Any]):
        """매매 실행"""
        try:
            signal_type = signal.get("signal")
            confidence = signal.get("confidence", 0.0)
            
            logger.info(
                f"📈 매매 신호 수신: {signal_type} "
                f"(신뢰도: {confidence:.2%})"
            )
            
            # 리스크 검증
            if not self.risk_manager.can_trade():
                logger.warning("⚠️ 리스크 관리 시스템이 거래를 차단했습니다.")
                return
            
            # 주문 실행
            if signal_type == "LONG":
                order = self.binance.open_long_position(
                    symbol=self.symbol,
                    leverage=self.leverage,
                    confidence=confidence
                )
            elif signal_type == "SHORT":
                order = self.binance.open_short_position(
                    symbol=self.symbol,
                    leverage=self.leverage,
                    confidence=confidence
                )
            else:
                return
            
            if order:
                logger.info(f"✅ 주문 실행 완료: {signal_type}")
                # 리스크 관리 업데이트
                self.risk_manager.record_trade(order)
            else:
                logger.error(f"❌ 주문 실행 실패: {signal_type}")
        
        except Exception as e:
            logger.error(f"❌ 매매 실행 오류: {e}")
    
    async def run(self):
        """메인 실행 루프"""
        logger.info("🚀 실시간 매매 엔진 시작")
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   테스트넷: {self.testnet}")
        logger.info(f"   초기 자본: {self.initial_capital} USDT")
        logger.info(f"   레버리지: {self.leverage}배")
        
        self.running = True
        
        # 위상 분석 엔진 브릿지 처리 루프 시작
        phase_task = asyncio.create_task(self.phase_bridge.process_loop())
        
        # 매매 신호 처리 루프 시작
        signal_task = asyncio.create_task(self._process_trading_signals())
        
        # WebSocket 커넥터 실행
        try:
            await self.connector.run()
        except KeyboardInterrupt:
            logger.info("⏹️ 사용자에 의해 중단됨")
        finally:
            self.running = False
            self.phase_bridge.stop()
            phase_task.cancel()
            signal_task.cancel()
            
            # 정리
            await self.connector.disconnect()
            logger.info("✅ 실시간 매매 엔진 종료")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 조회"""
        connector_metrics = self.connector.get_metrics()
        phase_metrics = self.phase_bridge.get_metrics()
        
        return {
            "running": self.running,
            "connector": connector_metrics,
            "phase_analysis": phase_metrics,
            "risk_manager": {
                "daily_pnl": self.risk_manager.daily_pnl,
                "can_trade": self.risk_manager.can_trade(),
            }
        }


async def main():
    """테스트 실행"""
    engine = RealtimeTradingEngine(
        symbol="BTCUSDT",
        testnet=True,
        initial_capital=1000.0,
        leverage=2
    )
    
    await engine.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())

