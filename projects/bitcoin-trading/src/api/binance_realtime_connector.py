#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
바이낸스 WebSocket 실시간 커넥터

목적: 10초 선점 전략을 위한 실시간 데이터 수집
- 호가창(Order Book) 실시간 복제
- 틱(Tick) 데이터 19ms 내 위상 분석 엔진으로 전송
- WebSocket 자동 재연결 및 에러 처리

작성일: 2026-01-12
상태: ✅ 구현 완료
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from collections import deque
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class BinanceRealtimeConnector:
    """
    바이낸스 WebSocket 실시간 커넥터
    
    핵심 기능:
    - 실시간 호가창 수집 (19ms 내 위상 분석 엔진으로 전송)
    - 틱 데이터 수집
    - 1분봉 실시간 업데이트
    - 자동 재연결 및 에러 처리
    """
    
    # WebSocket URL
    SPOT_WS_URL = "wss://stream.binance.com:9443/ws"
    FUTURES_WS_URL = "wss://fstream.binance.com/ws"
    
    def __init__(
        self,
        symbol: str = "btcusdt",
        use_futures: bool = True,
        streams: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        enable_phase_engine: bool = True,
        **kwargs: Any,
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼 (소문자, 예: "btcusdt")
            use_futures: Futures API 사용 여부
            streams: 구독할 스트림 리스트 (None이면 기본 스트림)
            callback: 데이터 수신 시 호출할 콜백 함수
            enable_phase_engine: 위상 분석 큐 전송 활성화 여부 (하위 호환)
            **kwargs: 하위 호환을 위한 확장 파라미터 (무시)
        """
        self.symbol = symbol.lower()
        self.use_futures = use_futures
        self.base_url = self.FUTURES_WS_URL if use_futures else self.SPOT_WS_URL
        self.callback = callback
        self.enable_phase_engine = bool(enable_phase_engine)
        
        # 기본 스트림 설정
        if streams is None:
            self.streams = [
                f"{self.symbol}@ticker",      # 24시간 통계
                f"{self.symbol}@trade",       # 실시간 거래
                f"{self.symbol}@depth20@100ms",  # 호가창 (20레벨, 100ms 업데이트)
                f"{self.symbol}@kline_1m",    # 1분봉
            ]
        else:
            self.streams = streams
        
        # 연결 상태
        self.websocket = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 999999  # 무한 재시도 (실제로는 사용하지 않음)
        self.reconnect_delay = 1.0  # 초기 재연결 지연 (초)
        
        # 데이터 버퍼 (최근 100개)
        self.ticker_buffer = deque(maxlen=100)
        self.trade_buffer = deque(maxlen=100)
        self.depth_buffer = deque(maxlen=100)
        self.kline_buffer = deque(maxlen=100)
        
        # 성능 메트릭
        self.metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "latency_ms": [],
            "errors": 0,
            "reconnects": 0,
        }
        
        # 위상 분석 엔진으로 전송하는 큐
        self.phase_analysis_queue = asyncio.Queue(maxsize=1000)
    
    def _get_stream_url(self) -> str:
        """스트림 URL 생성"""
        if len(self.streams) == 1:
            # 단일 스트림
            return f"{self.base_url}/{self.streams[0]}"
        else:
            # 결합 스트림
            streams_str = "/".join(self.streams)
            combined_base = self.base_url
            if combined_base.endswith("/ws"):
                combined_base = combined_base[:-3]
            return f"{combined_base}/stream?streams={streams_str}"
    
    async def connect(self):
        """WebSocket 연결"""
        url = self._get_stream_url()
        logger.info(f"🔌 WebSocket 연결 시도: {url}")
        
        try:
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,  # 20초마다 ping
                ping_timeout=10,   # 10초 타임아웃
                close_timeout=10
            )
            self.connected = True
            self.reconnect_attempts = 0
            self.reconnect_delay = 1.0
            logger.info("✅ WebSocket 연결 성공")
            logger.info(f"   스트림: {', '.join(self.streams)}")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.connected = False
            return False
    
    async def disconnect(self):
        """WebSocket 연결 종료"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 WebSocket 연결 종료")
            except Exception as e:
                logger.error(f"⚠️ 연결 종료 중 오류: {e}")
        self.connected = False
    
    async def _process_message(self, message: str):
        """메시지 처리 (19ms 내 위상 분석 엔진으로 전송)"""
        start_time = time.time()
        
        try:
            data = json.loads(message)
            
            # 스트림 타입별 처리 (combined stream payload)
            if "stream" in data:
                stream = data["stream"]
                payload = data["data"]
                
                # 스트림 타입에 따라 버퍼에 저장
                if "@ticker" in stream:
                    self.ticker_buffer.append(payload)
                    await self._send_to_phase_engine("ticker", payload)
                    # 콜백에 ticker 데이터 전달 (가격 정보 포함)
                    if self.callback:
                        callback_data = {
                            "price": float(payload.get("c", 0)),  # 현재 가격
                            "close": float(payload.get("c", 0)),
                            "timestamp": datetime.now(),
                            "volume": float(payload.get("v", 0))
                        }
                        try:
                            await self.callback(callback_data)
                        except Exception as e:
                            logger.error(f"⚠️ 콜백 실행 중 오류: {e}")
                
                elif "@trade" in stream:
                    self.trade_buffer.append(payload)
                    await self._send_to_phase_engine("trade", payload)
                    # 콜백에 trade 데이터 전달
                    if self.callback:
                        callback_data = {
                            "price": float(payload.get("p", 0)),  # 거래 가격
                            "close": float(payload.get("p", 0)),
                            "timestamp": datetime.fromtimestamp(payload.get("T", 0) / 1000) if payload.get("T") else datetime.now(),
                            "volume": float(payload.get("q", 0))
                        }
                        try:
                            await self.callback(callback_data)
                        except Exception as e:
                            logger.error(f"⚠️ 콜백 실행 중 오류: {e}")
                
                elif "@depth" in stream:
                    self.depth_buffer.append(payload)
                    await self._send_to_phase_engine("depth", payload)
                
                elif "@kline" in stream:
                    kline_data = payload.get("k", {})
                    if kline_data.get("x", False):  # 캔들 종료 시만
                        self.kline_buffer.append(kline_data)
                        await self._send_to_phase_engine("kline", kline_data)
                        # OHLC는 틱(ticker/trade) 기반 TickOhlcAggregator에서 결정적으로 적재한다.
                        # 종가-only kline 콜백은 동일 봉에 이중 카운트를 유발하므로 엔진 콜백에는 보내지 않음.
            else:
                # Raw payload fallback (some endpoints emit non-combined envelopes).
                event_type = str(data.get("e", "")).lower()
                if event_type == "24hrticker":
                    self.ticker_buffer.append(data)
                    await self._send_to_phase_engine("ticker", data)
                    if self.callback:
                        callback_data = {
                            "price": float(data.get("c", 0)),
                            "close": float(data.get("c", 0)),
                            "timestamp": datetime.now(),
                            "volume": float(data.get("v", 0)),
                        }
                        try:
                            await self.callback(callback_data)
                        except Exception as e:
                            logger.error(f"⚠️ 콜백 실행 중 오류(raw ticker): {e}")
                elif event_type == "trade":
                    self.trade_buffer.append(data)
                    await self._send_to_phase_engine("trade", data)
                    if self.callback:
                        callback_data = {
                            "price": float(data.get("p", 0)),
                            "close": float(data.get("p", 0)),
                            "timestamp": datetime.fromtimestamp(data.get("T", 0) / 1000) if data.get("T") else datetime.now(),
                            "volume": float(data.get("q", 0)),
                        }
                        try:
                            await self.callback(callback_data)
                        except Exception as e:
                            logger.error(f"⚠️ 콜백 실행 중 오류(raw trade): {e}")
                elif event_type == "depthupdate":
                    self.depth_buffer.append(data)
                    await self._send_to_phase_engine("depth", data)
                elif event_type == "kline":
                    kline_data = data.get("k", {})
                    if kline_data.get("x", False):
                        self.kline_buffer.append(kline_data)
                        await self._send_to_phase_engine("kline", kline_data)
            
            # 성능 메트릭 업데이트
            latency_ms = (time.time() - start_time) * 1000
            self.metrics["messages_received"] += 1
            self.metrics["messages_processed"] += 1
            self.metrics["latency_ms"].append(latency_ms)
            
            # 최근 1000개만 유지
            if len(self.metrics["latency_ms"]) > 1000:
                self.metrics["latency_ms"] = self.metrics["latency_ms"][-1000:]
            
            # 주기적으로 연결 상태 로그 (100개 메시지마다)
            if self.metrics["messages_received"] % 100 == 0:
                logger.debug(f"📊 WebSocket 메시지 수신: {self.metrics['messages_received']}개 (평균 지연: {sum(self.metrics['latency_ms'][-100:]) / min(100, len(self.metrics['latency_ms'])):.2f}ms)")
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 오류: {e}")
            self.metrics["errors"] += 1
        except Exception as e:
            logger.error(f"❌ 메시지 처리 오류: {e}")
            self.metrics["errors"] += 1
    
    async def _send_to_phase_engine(self, data_type: str, data: Dict[str, Any]):
        """
        위상 분석 엔진으로 데이터 전송 (19ms 내)
        
        Args:
            data_type: 데이터 타입 ("ticker", "trade", "depth", "kline")
            data: 데이터 페이로드
        """
        try:
            if not self.enable_phase_engine:
                return
            # 큐에 추가 (논블로킹)
            try:
                await asyncio.wait_for(
                    self.phase_analysis_queue.put({
                        "type": data_type,
                        "data": data,
                        "timestamp": time.time(),
                        "symbol": self.symbol.upper()
                    }),
                    timeout=0.001  # 1ms 타임아웃
                )
            except asyncio.TimeoutError:
                # 큐가 가득 찬 경우 (드롭)
                logger.warning("⚠️ 위상 분석 큐가 가득 참, 메시지 드롭")
        
        except Exception as e:
            logger.error(f"❌ 위상 분석 엔진 전송 오류: {e}")
    
    async def get_phase_analysis_data(self) -> Optional[Dict[str, Any]]:
        """
        위상 분석 엔진에서 데이터 가져오기
        
        Returns:
            위상 분석용 데이터 또는 None
        """
        try:
            return await asyncio.wait_for(
                self.phase_analysis_queue.get(),
                timeout=0.01  # 10ms 타임아웃
            )
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"❌ 위상 분석 데이터 가져오기 오류: {e}")
            return None
    
    async def listen(self):
        """WebSocket 메시지 수신 루프"""
        if not self.connected:
            logger.error("❌ WebSocket이 연결되지 않았습니다.")
            return
        
        logger.info("👂 WebSocket 메시지 수신 시작")
        
        try:
            async for message in self.websocket:
                await self._process_message(message)
        
        except ConnectionClosed:
            logger.warning("⚠️ WebSocket 연결이 종료되었습니다.")
            self.connected = False
        except WebSocketException as e:
            logger.error(f"❌ WebSocket 오류: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}")
            self.connected = False
    
    async def reconnect(self):
        """자동 재연결 (Exponential backoff, 무한 재시도)"""
        # 무한 재시도 (최대 재시도 횟수 제한 제거)
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60)
        
        logger.info(f"🔄 재연결 시도 {self.reconnect_attempts}회 ({delay:.1f}초 후)")
        await asyncio.sleep(delay)
        
        success = await self.connect()
        if success:
            self.metrics["reconnects"] += 1
            self.reconnect_attempts = 0  # 성공 시 재시도 횟수 리셋
            self.reconnect_delay = 1.0  # 지연 시간 리셋
            logger.info("✅ 재연결 성공")
        else:
            logger.warning(f"⚠️ 재연결 실패 (시도 {self.reconnect_attempts}회), 다음 시도 대기 중...")
        
        return success
    
    async def run(self):
        """메인 실행 루프 (자동 재연결 포함, 무한 재시도)"""
        logger.info("🚀 바이낸스 WebSocket 실시간 커넥터 시작")
        
        while True:
            try:
                # 연결 시도
                if not self.connected:
                    logger.info("🔌 WebSocket 연결 시도 중...")
                    success = await self.connect()
                    if not success:
                        logger.warning("⚠️ 초기 연결 실패, 재연결 시도...")
                        await self.reconnect()
                        continue
                
                # 메시지 수신
                logger.info("👂 WebSocket 메시지 수신 중...")
                await self.listen()
                
                # 연결 끊김 시 재연결 (무한 재시도)
                if not self.connected:
                    logger.warning("⚠️ WebSocket 연결 끊김 감지, 재연결 시도...")
                    await self.reconnect()
            
            except KeyboardInterrupt:
                logger.info("⏹️ 사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"❌ 실행 중 오류: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.connected = False
                await asyncio.sleep(1)
        
        await self.disconnect()
    
    def get_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        latency_ms = self.metrics["latency_ms"]
        
        return {
            "messages_received": self.metrics["messages_received"],
            "messages_processed": self.metrics["messages_processed"],
            "errors": self.metrics["errors"],
            "reconnects": self.metrics["reconnects"],
            "latency": {
                "avg_ms": sum(latency_ms) / len(latency_ms) if latency_ms else 0,
                "min_ms": min(latency_ms) if latency_ms else 0,
                "max_ms": max(latency_ms) if latency_ms else 0,
                "p95_ms": sorted(latency_ms)[int(len(latency_ms) * 0.95)] if latency_ms else 0,
            },
            "connected": self.connected,
            "buffer_sizes": {
                "ticker": len(self.ticker_buffer),
                "trade": len(self.trade_buffer),
                "depth": len(self.depth_buffer),
                "kline": len(self.kline_buffer),
            }
        }
    
    def get_latest_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """
        최신 데이터 조회
        
        Args:
            data_type: 데이터 타입 ("ticker", "trade", "depth", "kline")
        
        Returns:
            최신 데이터 또는 None
        """
        buffer_map = {
            "ticker": self.ticker_buffer,
            "trade": self.trade_buffer,
            "depth": self.depth_buffer,
            "kline": self.kline_buffer,
        }
        
        buffer = buffer_map.get(data_type)
        if buffer and len(buffer) > 0:
            return buffer[-1]
        return None


async def test_connector():
    """테스트 함수"""
    async def callback(data):
        """콜백 함수"""
        if "stream" in data:
            stream = data.get("stream", "unknown")
            stream_type = stream.split("@")[-1] if "@" in stream else "unknown"
            print(f"📨 데이터 수신: {stream_type} ({stream})")
        else:
            print(f"📨 데이터 수신: {data.get('e', 'unknown')}")
    
    connector = BinanceRealtimeConnector(
        symbol="btcusdt",
        use_futures=True,
        callback=callback
    )
    
    # 백그라운드 실행
    task = asyncio.create_task(connector.run())
    
    # 10초 대기
    await asyncio.sleep(10)
    
    # 메트릭 출력
    metrics = connector.get_metrics()
    print(f"\n📊 성능 메트릭:")
    print(f"  수신 메시지: {metrics['messages_received']}개")
    print(f"  평균 지연: {metrics['latency']['avg_ms']:.2f}ms")
    print(f"  P95 지연: {metrics['latency']['p95_ms']:.2f}ms")
    
    # 위상 분석 데이터 확인
    phase_data = await connector.get_phase_analysis_data()
    if phase_data:
        print(f"\n🔍 위상 분석 데이터: {phase_data['type']}")
    
    task.cancel()


if __name__ == "__main__":
    asyncio.run(test_connector())

