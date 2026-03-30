#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 24시간 비트코인 자동매매 데몬

안티그래비티 기반 24시간 무중단 자동매매 시스템

핵심 기능:
1. 무중단 실행 (자동 재시작)
2. 에러 핸들링 및 복구
3. 상태 모니터링 및 알림
4. 로깅 및 리포트

작성일: 2026-02-06
"""

import asyncio
import logging
import signal
import sys
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import traceback

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.integration.realtime_trading_with_monitoring import RealtimeTradingWithMonitoring
from src.monitoring.alert_manager import AlertManager
from src.config.config_loader import load_config

# 로깅 설정
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"trading_daemon_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BitcoinTradingDaemon:
    """
    24시간 비트코인 자동매매 데몬
    
    무중단 실행, 자동 복구, 상태 모니터링
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        testnet: bool = True,
        initial_capital: float = 1000.0,
        leverage: int = 2,
        enable_trading: bool = False,  # 기본값: 모니터링만
        max_restart_attempts: int = 10,
        restart_delay: int = 60  # 초
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
            testnet: 테스트넷 사용 여부
            initial_capital: 초기 자본
            leverage: 레버리지 배수
            enable_trading: 거래 활성화 여부
            max_restart_attempts: 최대 재시작 시도 횟수
            restart_delay: 재시작 지연 시간 (초)
        """
        self.symbol = symbol
        self.testnet = testnet
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.enable_trading = enable_trading
        self.max_restart_attempts = max_restart_attempts
        self.restart_delay = restart_delay
        
        # 상태 관리
        self.running = False
        self.engine: Optional[RealtimeTradingWithMonitoring] = None
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None
        self.start_time = datetime.now()
        
        # 통계
        self.total_runtime = 0.0
        self.error_count = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # 상태 파일 경로
        self.status_file = PROJECT_ROOT / "memory" / "trading_daemon_status.json"
        self.status_file.parent.mkdir(exist_ok=True, parents=True)
        self.heartbeat_file = PROJECT_ROOT / "memory" / "trading_daemon_heartbeat.txt"
        self.stop_file = PROJECT_ROOT / "memory" / "STOP.txt"
        self.trader_state_file = PROJECT_ROOT / "logs" / "trading_state.json"
        
        # Alert Manager 초기화 (중요 이벤트 알림용)
        try:
            self.alert_manager = AlertManager()
            logger.info("✅ Alert Manager 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ Alert Manager 초기화 실패: {e}")
            self.alert_manager = None
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ 비트코인 자동매매 데몬 초기화 완료")

    def _touch_heartbeat(self):
        """Heartbeat 갱신 (watchdog 감시용)"""
        try:
            now = datetime.now().isoformat()
            self.heartbeat_file.parent.mkdir(exist_ok=True, parents=True)
            self.heartbeat_file.write_text(now, encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️ Heartbeat 갱신 실패: {e}")

    def _is_kill_switch_on(self) -> bool:
        """운영자 Kill Switch 파일 감지"""
        try:
            return self.stop_file.exists()
        except Exception:
            return False
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (Graceful shutdown)"""
        logger.info(f"📡 시그널 수신: {signum}")
        logger.info("🛑 Graceful shutdown 시작...")
        self.running = False
    
    def _save_status(self):
        """상태 저장"""
        try:
            # Keep daemon counters aligned with live trader state when available.
            self._sync_trade_counters_from_trader_state()
            exchange_snapshot = self._build_exchange_trade_snapshot()
            status = {
                "running": self.running,
                "restart_count": self.restart_count,
                "last_restart_time": self.last_restart_time.isoformat() if self.last_restart_time else None,
                "start_time": self.start_time.isoformat(),
                "total_runtime_hours": self.total_runtime / 3600,
                "error_count": self.error_count,
                "successful_trades": self.successful_trades,
                "failed_trades": self.failed_trades,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "symbol": self.symbol,
                "testnet": self.testnet,
                "enable_trading": self.enable_trading,
                "exchange_snapshot_24h": exchange_snapshot,
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 상태 저장 실패: {e}")

    def _build_exchange_trade_snapshot(self) -> Dict[str, Any]:
        """Build lightweight 24h fills snapshot from exchange API."""
        snapshot: Dict[str, Any] = {
            "available": False,
            "fills_count": None,
            "realized_pnl": None,
            "commission": None,
            "funding_fee": None,
            "net": None,
        }
        try:
            if not self.engine or not getattr(self.engine, "binance", None):
                return snapshot
            client = getattr(self.engine.binance, "client", None)
            if not client:
                return snapshot
            now_ms = int(time.time() * 1000)
            start_ms = now_ms - 24 * 60 * 60 * 1000
            trades = client.futures_account_trades(
                symbol=self.symbol,
                startTime=start_ms,
                endTime=now_ms,
                limit=1000,
            )
            income = client.futures_income_history(
                symbol=self.symbol,
                startTime=start_ms,
                endTime=now_ms,
                limit=200,
            )
            realized = 0.0
            commission = 0.0
            funding = 0.0
            if isinstance(income, list):
                for row in income:
                    t = row.get("incomeType")
                    v = float(row.get("income") or 0.0)
                    if t == "REALIZED_PNL":
                        realized += v
                    elif t == "COMMISSION":
                        commission += v
                    elif t == "FUNDING_FEE":
                        funding += v
            snapshot = {
                "available": True,
                "fills_count": len(trades) if isinstance(trades, list) else None,
                "realized_pnl": round(realized, 8),
                "commission": round(commission, 8),
                "funding_fee": round(funding, 8),
                "net": round(realized + commission + funding, 8),
            }
            return snapshot
        except Exception:
            return snapshot

    def _sync_trade_counters_from_trader_state(self):
        """
        Sync daemon counters from trader runtime state file.
        This prevents persistent mismatch where exchange has fills
        but daemon `successful_trades` remains 0.
        """
        try:
            if not self.trader_state_file.exists():
                return
            with open(self.trader_state_file, "r", encoding="utf-8") as f:
                ts = json.load(f)
            if not isinstance(ts, dict):
                return

            # Ignore stale snapshots from old runs.
            ts_raw = ts.get("timestamp")
            if ts_raw:
                try:
                    ts_dt = datetime.fromisoformat(str(ts_raw))
                    if ts_dt < self.start_time - timedelta(minutes=5):
                        return
                except Exception:
                    pass

            tc = ts.get("trades_count")
            if isinstance(tc, int) and tc >= 0:
                self.successful_trades = tc

            cb = ts.get("circuit_breaker_state")
            if isinstance(cb, dict):
                fc = cb.get("failure_count")
                if isinstance(fc, int) and fc >= 0:
                    self.failed_trades = fc

            # Fallback: when local trader state is stale/missing, derive fills from exchange API (24h).
            if self.successful_trades == 0 and self.engine and getattr(self.engine, "binance", None):
                client = getattr(self.engine.binance, "client", None)
                if client:
                    now_ms = int(time.time() * 1000)
                    start_ms = now_ms - 24 * 60 * 60 * 1000
                    trades = client.futures_account_trades(
                        symbol=self.symbol,
                        startTime=start_ms,
                        endTime=now_ms,
                        limit=1000,
                    )
                    if isinstance(trades, list):
                        self.successful_trades = len(trades)
        except Exception as e:
            logger.debug(f"trader state sync skipped: {e}")
    
    def _load_status(self) -> Dict[str, Any]:
        """상태 로드"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ 상태 로드 실패: {e}")
        return {}
    
    async def _create_engine(self) -> RealtimeTradingWithMonitoring:
        """거래 엔진 생성"""
        logger.info("🔧 거래 엔진 생성 중...")
        engine = RealtimeTradingWithMonitoring(
            symbol=self.symbol,
            testnet=self.testnet,
            initial_capital=self.initial_capital,
            leverage=self.leverage,
            enable_monitoring=True,
            enable_trading=self.enable_trading
        )
        logger.info("✅ 거래 엔진 생성 완료")
        return engine
    
    async def _run_engine(self):
        """거래 엔진 실행"""
        try:
            self.engine = await self._create_engine()
            # ----- 🏛️ AlertManager 주입 (Report 계층 완성) -----
            if getattr(self, "alert_manager", None) is not None:
                self.engine.alert_manager = self.alert_manager
                logger.info("✅ AlertManager 엔진 주입 완료 (방어 모드 알림용)")
            await self.engine.run()
        except KeyboardInterrupt:
            logger.info("⏹️ 사용자에 의해 중단됨")
            raise
        except Exception as e:
            logger.error(f"❌ 거래 엔진 오류: {e}")
            logger.error(traceback.format_exc())
            self.error_count += 1
            raise
    
    async def _monitor_health(self):
        """헬스 체크 모니터링"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 60초마다 체크 (헬스체크 간격 동기화)
                
                if self.engine:
                    status = self.engine.get_status()
                    
                    # 상태 로깅
                    logger.info(
                        f"📊 헬스 체크: "
                        f"실행 중={status.get('running', False)}, "
                        f"가격 히스토리={status.get('price_history_size', 0)}, "
                        f"거래 활성화={status.get('trading_enabled', False)}"
                    )
                    
                    # 리스크 가디언 상태 확인
                    if 'risk_guardian' in status:
                        rg_status = status['risk_guardian']
                        if rg_status.get('trading_paused', False):
                            logger.warning(
                                f"⚠️ 리스크 가디언: 거래 중단됨 "
                                f"(재개: {rg_status.get('pause_until', 'N/A')})"
                            )
                    
                    # 압축 브릿지 상태 확인
                    if 'compression_bridge' in status:
                        cb_status = status['compression_bridge']
                        logger.info(
                            f"📊 압축 브릿지: "
                            f"압축 횟수={cb_status.get('compression_count', 0)}, "
                            f"평균 노이즈 필터링={cb_status.get('avg_noise_filtered', 0):.1%}"
                        )
                
                # 상태 저장
                self._save_status()
                self._touch_heartbeat()
                
            except Exception as e:
                logger.error(f"❌ 헬스 체크 오류: {e}")
    
    async def run(self):
        """메인 실행 루프 (무중단)"""
        logger.info("="*80)
        logger.info("🚀 24시간 비트코인 자동매매 데몬 시작")
        logger.info("="*80)
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   테스트넷: {self.testnet}")
        logger.info(f"   초기 자본: {self.initial_capital} USDT")
        logger.info(f"   레버리지: {self.leverage}배")
        logger.info(f"   거래: {'활성화' if self.enable_trading else '비활성화 (모니터링만)'}")
        logger.info(f"   최대 재시작 시도: {self.max_restart_attempts}회")
        logger.info("="*80)
        
        self.running = True
        self.start_time = datetime.now()
        self._touch_heartbeat()

        if self._is_kill_switch_on():
            logger.warning(f"🛑 Kill Switch 감지됨: {self.stop_file}")
            self.running = False
            self._save_status()
            return
        
        # 🚀 실전 매매 시작 텔레그램 알림 전송
        if self.alert_manager:
            mode_text = "실전 거래소" if not self.testnet else "테스트넷"
            trading_text = "활성화" if self.enable_trading else "비활성화 (모니터링만)"
            start_message = f"""
🚀 *실전 매매 시스템 시작*

*모드:* {mode_text}
*거래:* {trading_text}
*심볼:* {self.symbol}
*초기 자본:* ${self.initial_capital:,.2f}
*레버리지:* {self.leverage}배

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            asyncio.create_task(
                self.alert_manager.alert_system_status(
                    status="STARTED",
                    message=start_message.strip()
                )
            )
        
        # 이전 상태 로드
        prev_status = self._load_status()
        if prev_status:
            logger.info(f"📋 이전 상태: 재시작 {prev_status.get('restart_count', 0)}회")
        
        # 헬스 체크 태스크 시작
        health_task = asyncio.create_task(self._monitor_health())
        
        # 메인 루프
        while self.running:
            try:
                if self._is_kill_switch_on():
                    logger.warning(f"🛑 Kill Switch 감지됨: {self.stop_file}")
                    break

                # 재시작 횟수 확인
                if self.restart_count >= self.max_restart_attempts:
                    logger.error(f"❌ 최대 재시작 시도 횟수({self.max_restart_attempts}) 초과. 종료합니다.")
                    break
                
                # 거래 엔진 실행
                self._touch_heartbeat()
                await self._run_engine()
                
                # 정상 종료
                logger.info("✅ 거래 엔진 정상 종료")
                break
                
            except KeyboardInterrupt:
                logger.info("⏹️ 사용자에 의해 중단됨")
                break
                
            except Exception as e:
                self.error_count += 1
                self.restart_count += 1
                self.last_restart_time = datetime.now()
                
                logger.error(f"❌ 오류 발생 (재시작 {self.restart_count}/{self.max_restart_attempts}): {e}")
                logger.error(traceback.format_exc())
                
                # 중요 이벤트 알림 (재시작)
                if self.alert_manager:
                    await self.alert_manager.alert_critical_event(
                        event_type="DAEMON_RESTART",
                        message=f"거래 엔진 오류로 인해 재시작합니다. ({self.restart_count}/{self.max_restart_attempts})",
                        details={
                            "restart_count": self.restart_count,
                            "max_restart_attempts": self.max_restart_attempts,
                            "error_count": self.error_count,
                            "error": str(e),
                            "restart_delay": self.restart_delay
                        },
                        severity="HIGH" if self.restart_count < self.max_restart_attempts else "CRITICAL"
                    )
                
                if self.restart_count < self.max_restart_attempts:
                    logger.info(f"⏳ {self.restart_delay}초 후 재시작...")
                    await asyncio.sleep(self.restart_delay)
                    
                    # 엔진 정리
                    if self.engine:
                        try:
                            self.engine.running = False
                        except:
                            pass
                        self.engine = None
                else:
                    logger.error("❌ 최대 재시작 시도 횟수 초과. 종료합니다.")
                    # CRITICAL 알림
                    if self.alert_manager:
                        await self.alert_manager.alert_critical_event(
                            event_type="DAEMON_MAX_RESTARTS",
                            message="최대 재시작 시도 횟수를 초과했습니다. 데몬이 종료됩니다.",
                            details={
                                "restart_count": self.restart_count,
                                "max_restart_attempts": self.max_restart_attempts,
                                "error_count": self.error_count,
                                "total_runtime_hours": self.total_runtime / 3600
                            },
                            severity="CRITICAL"
                        )
                    break
        
        # 헬스 체크 태스크 종료
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        
        # 최종 상태 저장
        self.total_runtime = (datetime.now() - self.start_time).total_seconds()
        self._save_status()
        
        logger.info("="*80)
        logger.info("✅ 24시간 비트코인 자동매매 데몬 종료")
        logger.info(f"   총 실행 시간: {self.total_runtime / 3600:.2f}시간")
        logger.info(f"   재시작 횟수: {self.restart_count}회")
        logger.info(f"   오류 횟수: {self.error_count}회")
        logger.info("="*80)
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        status = {
            "running": self.running,
            "restart_count": self.restart_count,
            "last_restart_time": self.last_restart_time.isoformat() if self.last_restart_time else None,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.running else 0,
            "error_count": self.error_count,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "symbol": self.symbol,
            "testnet": self.testnet,
            "enable_trading": self.enable_trading,
            "heartbeat_file": str(self.heartbeat_file),
            "stop_file": str(self.stop_file)
        }
        
        if self.engine:
            try:
                engine_status = self.engine.get_status()
                status["engine"] = engine_status
            except:
                pass
        
        return status


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="24시간 비트코인 자동매매 데몬")
    parser.add_argument("--symbol", default=None, help="거래 심볼")
    parser.add_argument("--testnet", dest="testnet", action="store_true", default=None, help="테스트넷 사용")
    parser.add_argument("--no-testnet", dest="testnet", action="store_false", help="실전 거래소 사용")
    parser.add_argument("--initial-capital", type=float, default=None, help="초기 자본")
    parser.add_argument("--leverage", type=int, default=None, help="레버리지 배수")
    parser.add_argument("--enable-trading", action="store_true", default=None, help="거래 활성화 (실주문)")
    parser.add_argument("--disable-trading", dest="enable_trading", action="store_false", help="거래 비활성화 (모니터링만)")
    parser.add_argument("--max-restart", type=int, default=None, help="최대 재시작 시도 횟수")
    parser.add_argument("--restart-delay", type=int, default=None, help="재시작 지연 시간 (초)")
    
    args = parser.parse_args()

    config_path = PROJECT_ROOT / "config" / "trading_config.yaml"
    config = load_config(config_path)
    risk_cfg = config.get("risk_management", {}) if isinstance(config, dict) else {}

    symbol = args.symbol if args.symbol is not None else config.get("symbol", "BTCUSDT")
    testnet = args.testnet if args.testnet is not None else config.get("testnet", True)
    initial_capital = (
        args.initial_capital if args.initial_capital is not None
        else config.get("initial_capital", risk_cfg.get("initial_capital", 1000.0))
    )
    leverage = args.leverage if args.leverage is not None else config.get("leverage", 2)
    enable_trading = (
        args.enable_trading if args.enable_trading is not None
        else config.get("enable_live_trading", False)
    )
    max_restart = args.max_restart if args.max_restart is not None else 10
    restart_delay = args.restart_delay if args.restart_delay is not None else 60
    
    daemon = BitcoinTradingDaemon(
        symbol=symbol,
        testnet=testnet,
        initial_capital=initial_capital,
        leverage=leverage,
        enable_trading=enable_trading,
        max_restart_attempts=max_restart,
        restart_delay=restart_delay
    )
    
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())

