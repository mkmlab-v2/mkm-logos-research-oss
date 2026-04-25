#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 실전 거래 엔진 + 통합 모니터링 시스템

목적: RealtimeTradingEngine + UnifiedTradingMonitor 융합
- 실시간 WebSocket 데이터 수신
- 통합 모니터링 분석
- 거래 신호 생성 및 실행

OHLC / 데이터 (운영 팩트):
- 통합 분석용 캔들은 ``TickOhlcAggregator``(틱→고정 간격 봉)로만 구성; 랜덤 OHLC 없음.
- ``OHLC_BAR_INTERVAL_SEC``(기본 60), ``OHLC_MIN_COMPLETED_BARS``(기본 48) 환경변수로 조정.

Prophecy / 주문 경계 (운영 팩트):
- ProphecyStack은 레짐·보조 신호 경로에 사용될 수 있음.
- 비테스트넷(testnet=False)에서 ProphecyStack이 살아 있으면 주문 실행 전에
  PROPHECY_FUSION_ALLOW_MAINNET=1 가 없으면 _execute_trade 로 가지 않음(차단).
- DISABLE_PROPHECY_STACK=1 이면 ProphecyStack 초기화를 건너뜀.

작성일: 2026-02-05
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np

from src.api.binance_realtime_connector import BinanceRealtimeConnector
from src.api.binance_client import BinanceFuturesClient, get_last_binance_credential_meta
from src.risk.risk_manager import RiskManager
from src.risk.risk_guardian import RiskGuardian
from src.integration.unified_trading_monitor import UnifiedTradingMonitor
from src.integration.compression_trading_bridge import CompressionTradingBridge
from src.market.tick_ohlc_aggregator import TickOhlcAggregator
try:
    from scripts.core.mkm12_singular_core import CoreInput, compute_core_score
except ModuleNotFoundError:
    workspace_root = Path(__file__).resolve().parents[4]
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))
    from scripts.core.mkm12_singular_core import CoreInput, compute_core_score

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Phase 1 방어망: 최소 신뢰도 (손절/익절·반대신호 청산과 동일 기준)
MIN_CONFIDENCE = 0.52


def _env_flag_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _block_live_orders_for_prophecy_fusion(prophecy_stack: Any, testnet: bool) -> bool:
    """Non-testnet + active ProphecyStack without operator override → block _execute_trade."""
    if prophecy_stack is None:
        return False
    if testnet:
        return False
    return not _env_flag_true("PROPHECY_FUSION_ALLOW_MAINNET")


class RealtimeTradingWithMonitoring:
    """
    실전 거래 엔진 + 통합 모니터링 시스템
    
    핵심 기능:
    1. WebSocket 실시간 데이터 수집
    2. 통합 모니터링 분석 (전이 엔트로피 + 압축 분석 + 로고스-니트로)
    3. 통합 신호 생성 및 거래 실행
    4. 자동 리스크 관리
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        testnet: bool = True,
        initial_capital: float = 1000.0,
        leverage: int = 2,
        enable_monitoring: bool = True,
        enable_trading: bool = False,  # 기본값: 모니터링만
        regime_observation_only: bool = True,  # True: 레짐 방어 시 알림만, False: 청산·신호 강제 연동
    ):
        """
        초기화

        Args:
            symbol: 거래 심볼
            testnet: 테스트넷 사용 여부
            initial_capital: 초기 자본
            leverage: 레버리지 배수
            enable_monitoring: 모니터링 활성화 여부
            enable_trading: 거래 활성화 여부 (실전 거래 시 True)
            regime_observation_only: True면 레짐 방어 모드 시 알림만 발송(청산·신호 강제 없음). False면 기존처럼 선제 청산·HOLD 강제.
        """
        self.symbol = symbol
        self._regime_observation_only = regime_observation_only
        self.testnet = testnet
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.enable_trading = enable_trading
        self._maker_only = os.environ.get("MKM_MAKER_ONLY", "1").strip().lower() in ("1", "true", "yes")
        self._strict_maker_enforcement = os.environ.get(
            "MKM_STRICT_MAKER_ENFORCEMENT", "1"
        ).strip().lower() in ("1", "true", "yes")
        
        # Binance API 클라이언트
        logger.info("🔐 Binance API 클라이언트 초기화 중...")
        self.binance = BinanceFuturesClient(testnet=testnet, maker_only=self._maker_only)
        
        # 통합 모니터링 시스템
        logger.info("🏛️ 통합 모니터링 시스템 초기화 중...")
        self.monitor = UnifiedTradingMonitor(
            symbol=symbol,
            enable_monitoring=enable_monitoring,
            enable_trading=enable_trading
        )
        
        # 리스크 관리 (기존)
        logger.info("🛡️ 리스크 관리 시스템 초기화 중...")
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        
        # 리스크 가디언 (MDD 억제 강화)
        logger.info("🛡️ 리스크 가디언 시스템 초기화 중...")
        try:
            from src.risk.risk_guardian import RiskGuardian
            self.risk_guardian = RiskGuardian(
                base_position_size=0.30,
                daily_loss_limit=0.05,
                max_consecutive_losses=3
            )
            logger.info("✅ 리스크 가디언 초기화 완료")
        except ImportError:
            logger.warning("⚠️ 리스크 가디언 모듈을 찾을 수 없습니다. 기본 리스크 관리만 사용합니다.")
            self.risk_guardian = None
        
        # 압축-트레이딩 브릿지 (노이즈 제거)
        logger.info("📊 압축-트레이딩 브릿지 초기화 중...")
        try:
            self.compression_bridge = CompressionTradingBridge(enable_compression=True)
            logger.info("✅ 압축-트레이딩 브릿지 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 압축-트레이딩 브릿지 초기화 실패: {e}")
            self.compression_bridge = None
        
        # Equity 추적 (Drawdown 계산용)
        self.equity_history = [initial_capital]
        self.peak_equity = initial_capital
        
        # WebSocket 커넥터
        logger.info("🔌 WebSocket 커넥터 초기화 중...")
        self.connector = BinanceRealtimeConnector(
            symbol=symbol.lower(),
            use_futures=True,
            callback=self._on_websocket_data
        )
        
        # 가격 히스토리 (모니터링용)
        self.price_history = []
        self.max_history_size = 1000
        _bar_sec = float(os.environ.get("OHLC_BAR_INTERVAL_SEC", "60") or "60")
        _min_bars = int(os.environ.get("OHLC_MIN_COMPLETED_BARS", "48") or "48")
        self._ohlc_min_completed_bars = max(2, _min_bars)
        self._ohlc_feed = TickOhlcAggregator(
            bar_interval_sec=max(1.0, _bar_sec),
            max_stored_bars=500,
        )
        logger.info(
            "📈 Tick OHLC: interval=%ss min_completed_bars=%s (env OHLC_BAR_INTERVAL_SEC / OHLC_MIN_COMPLETED_BARS)",
            int(max(1.0, _bar_sec)),
            self._ohlc_min_completed_bars,
        )
        self._seed_ohlc_from_exchange()
        
        # 실행 상태
        self.running = False
        self.ws_tick_count = 0
        self._last_state_persist_ts = 0.0
        self.signal_total_count = 0
        self.singular_action_counts = {"BUY": 0, "SELL": 0, "LOCKED": 0}
        self.last_signal_summary: Dict[str, Any] = {}
        self.last_execution_trace: Dict[str, Any] = {
            "ts": None,
            "decision": "idle",
            "reason": "init",
            "signal": None,
            "confidence": None,
            "details": {},
        }
        self.last_4ai_trace: Dict[str, Any] = {
            "timestamp": None,
            "ai1_signal": {},
            "ai2_risk": {},
            "ai3_execution": {},
            "ai4_audit": {},
        }
        self._min_position_hold_seconds = int(
            os.environ.get("POSITION_MIN_HOLD_SECONDS", "180") or "180"
        )
        self._reversal_cooldown_seconds = int(
            os.environ.get("REVERSAL_COOLDOWN_SECONDS", "120") or "120"
        )
        self._last_position_open_ts: Optional[float] = None
        self._last_position_side: Optional[str] = None
        self._last_reversal_ts: float = 0.0
        root = Path(__file__).resolve().parents[2]
        self._risk_profile_candidates = [
            root / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json",
            root / "memory" / "v2" / "risk" / "risk_profile_latest.json",
            root / "memory" / "risk_profile_latest.json",
        ]
        self._risk_limits_cache: Dict[str, Any] = {}
        self._risk_limits_cache_ts: float = 0.0
        self._exchange_runtime_state_cache: Dict[str, Any] = {
            "ts": None,
            "current_position": None,
            "open_orders_count": None,
            "recent_fills_count": None,
            "exchange_error": None,
            "credential_source": "unknown",
            "credential_key_suffix": "****",
        }
        self._exchange_runtime_state_cache_ts = 0.0
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = log_dir / "trading_state.json"
        self.startup_reconcile_status: Dict[str, Any] = {
            "completed": False,
            "ts": None,
            "open_orders_count": None,
            "has_position": None,
            "position_side": None,
            "position_qty": None,
            "recent_fills_count": None,
            "error": None,
        }
        
        # 🏛️ 레짐 엔진 (SSOT 230751, Sensor/Logic용)
        self._prophecy_stack = None
        self._regime_defense_mode = False
        self._last_regime_id = "unknown"
        self.alert_manager = None
        if _env_flag_true("DISABLE_PROPHECY_STACK"):
            logger.info("DISABLE_PROPHECY_STACK: ProphecyStack 초기화 생략")
        else:
            try:
                from tools.prophecy.prophecy_stack import ProphecyStack
                self._prophecy_stack = ProphecyStack()
                logger.info("✅ ProphecyStack 초기화 완료 (레짐·포스트잇 이식)")
            except Exception as e:
                logger.warning(f"⚠️ ProphecyStack 초기화 실패(레짐 감지 비활성): {e}")
        
        logger.info("✅ 실전 거래 엔진 + 통합 모니터링 시스템 초기화 완료")

    def _seed_ohlc_from_exchange(self) -> None:
        """
        Warm up OHLC aggregator from recent exchange klines so signal loop
        can start without waiting for full live-bar accumulation.
        """
        try:
            interval_sec = int(max(1.0, float(getattr(self._ohlc_feed, "_interval", 60))))
            interval_map = {
                60: "1m",
                180: "3m",
                300: "5m",
                900: "15m",
                1800: "30m",
                3600: "1h",
            }
            kline_interval = interval_map.get(interval_sec, "1m")
            target = int(self._ohlc_min_completed_bars) + 5
            klines = self.binance.get_klines(symbol=self.symbol, interval=kline_interval, limit=max(50, target))
            if not isinstance(klines, list) or len(klines) < 3:
                logger.warning("⚠️ OHLC warmup seed skipped: insufficient klines")
                return

            seeded = 0
            for row in klines:
                if not isinstance(row, (list, tuple)) or len(row) < 6:
                    continue
                close_ts_ms = int(row[6]) if len(row) > 6 else int(row[0]) + (interval_sec * 1000)
                close_price = float(row[4])
                volume = float(row[5])
                ts = datetime.fromtimestamp(max(0, close_ts_ms) / 1000.0)
                self._ohlc_feed.push(ts, close_price, volume)
                seeded += 1

            logger.info(
                "✅ OHLC warmup seed complete: interval=%s seeded=%s completed=%s",
                kline_interval,
                seeded,
                self._ohlc_feed.completed_count(),
            )
        except Exception as e:
            logger.warning(f"⚠️ OHLC warmup seed failed: {e}")

    def _get_position(self) -> Optional[Dict[str, Any]]:
        """현재 포지션 조회 (Binance API). 없으면 None."""
        try:
            return self.binance.get_position(self.symbol)
        except Exception as e:
            logger.warning(f"⚠️ 포지션 조회 실패: {e}")
            return None

    def _close_position(
        self,
        position_side: str,
        *,
        close_reason: str = "manual_close",
        enforce_min_hold: bool = True,
    ) -> bool:
        """포지션 청산 (LONG 또는 SHORT). 성공 여부 반환."""
        try:
            if enforce_min_hold and self._last_position_open_ts is not None:
                hold_elapsed = time.time() - float(self._last_position_open_ts)
                if hold_elapsed < float(self._min_position_hold_seconds):
                    details = {
                        "position_side": position_side,
                        "close_reason": close_reason,
                        "hold_elapsed_sec": round(float(hold_elapsed), 3),
                        "min_hold_sec": int(self._min_position_hold_seconds),
                    }
                    logger.info("🛑 청산 차단(min_hold): %s", details)
                    self._set_execution_trace(
                        decision="skipped",
                        reason="close_blocked_min_hold",
                        details=details,
                    )
                    return False
            result = self.binance.close_position(self.symbol, position_side)
            if result:
                logger.info(f"✅ 포지션 청산 완료: {self.symbol} {position_side}")
                self._last_position_open_ts = None
                self._last_position_side = None
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 포지션 청산 실패 ({position_side}): {e}")
            return False

    async def _check_and_close_sl_tp(self, current_price: float) -> None:
        """
        손절/익절 체크 — 매 주기 실행. RiskManager 비율(기본 2%/6%) 적용.
        현재가가 손절/익절가에 도달하면 해당 포지션 청산.
        """
        pos = self._get_position()
        if not pos:
            return
        if float(current_price or 0.0) <= 0.0:
            self._set_execution_trace(
                decision="skipped",
                reason="sl_tp_invalid_current_price",
                details={"current_price": current_price},
            )
            return
        if self._last_position_open_ts is not None:
            hold_elapsed = time.time() - float(self._last_position_open_ts)
            if hold_elapsed < float(self._min_position_hold_seconds):
                logger.info(
                    "🕒 SL/TP 청산 대기: hold_elapsed=%.1fs < min_hold=%ss",
                    float(hold_elapsed),
                    int(self._min_position_hold_seconds),
                )
                self._set_execution_trace(
                    decision="skipped",
                    reason="sl_tp_blocked_min_hold",
                    details={
                        "hold_elapsed_sec": round(float(hold_elapsed), 3),
                        "min_hold_sec": int(self._min_position_hold_seconds),
                    },
                )
                return
        entry_price = float(pos.get("entry_price", 0))
        side = pos.get("side", "LONG")
        if entry_price <= 0:
            return
        stop_loss = self.risk_manager.calculate_stop_loss(entry_price, side)
        take_profit = self.risk_manager.calculate_take_profit(entry_price, side)
        if side == "LONG":
            if current_price <= stop_loss:
                logger.warning(f"⚠️ 롱 손절: 현재가 {current_price:.2f} <= 손절가 {stop_loss:.2f}")
                self._set_execution_trace(
                    decision="attempted",
                    reason="sl_tp_stop_loss_triggered",
                    details={"position_side": "LONG", "current_price": current_price, "stop_loss": stop_loss},
                )
                self._close_position("LONG", close_reason="sl_tp_stop_loss")
                return
            if current_price >= take_profit:
                logger.info(f"✅ 롱 익절: 현재가 {current_price:.2f} >= 익절가 {take_profit:.2f}")
                self._set_execution_trace(
                    decision="attempted",
                    reason="sl_tp_take_profit_triggered",
                    details={"position_side": "LONG", "current_price": current_price, "take_profit": take_profit},
                )
                self._close_position("LONG", close_reason="sl_tp_take_profit")
                return
        else:
            if current_price >= stop_loss:
                logger.warning(f"⚠️ 숏 손절: 현재가 {current_price:.2f} >= 손절가 {stop_loss:.2f}")
                self._set_execution_trace(
                    decision="attempted",
                    reason="sl_tp_stop_loss_triggered",
                    details={"position_side": "SHORT", "current_price": current_price, "stop_loss": stop_loss},
                )
                self._close_position("SHORT", close_reason="sl_tp_stop_loss")
                return
            if current_price <= take_profit:
                logger.info(f"✅ 숏 익절: 현재가 {current_price:.2f} <= 익절가 {take_profit:.2f}")
                self._set_execution_trace(
                    decision="attempted",
                    reason="sl_tp_take_profit_triggered",
                    details={"position_side": "SHORT", "current_price": current_price, "take_profit": take_profit},
                )
                self._close_position("SHORT", close_reason="sl_tp_take_profit")
                return

    async def _on_websocket_data(self, data: Dict[str, Any]):
        """WebSocket 데이터 수신 콜백"""
        try:
            self.ws_tick_count += 1
            # 가격 데이터 저장
            if 'price' in data or 'close' in data:
                price = data.get('price') or data.get('close')
                if float(price or 0.0) <= 0.0:
                    logger.warning("⚠️ 비정상 실시간 가격 수신(<=0)으로 틱 무시: %s", price)
                    return
                timestamp = data.get('timestamp') or datetime.now()
                vol = float(data.get('volume', 0.0) or 0.0)
                self._ohlc_feed.push(timestamp, float(price), vol)

                self.price_history.append({
                    'timestamp': timestamp,
                    'price': float(price),
                    'volume': vol,
                })

                # 히스토리 크기 제한
                if len(self.price_history) > self.max_history_size:
                    self.price_history = self.price_history[-self.max_history_size:]

                # 주기적으로 가격 데이터 수집 상태 로그 (10개마다)
                if len(self.price_history) % 10 == 0:
                    logger.info(f"📊 가격 데이터 수집: {len(self.price_history)}개 (현재 가격: {price:.2f} USDT)")

            # Persist liveness even before warmup/signal generation
            # so watchdog/health checks don't see a frozen startup snapshot.
            now_ts = datetime.now().timestamp()
            if (now_ts - self._last_state_persist_ts) >= 15:
                self._save_state()
                self._last_state_persist_ts = now_ts

            # 통합 분석: 완료된 OHLC 봉 개수 기준 (랜덤 캔들 제거)
            if self._ohlc_feed.completed_count() >= self._ohlc_min_completed_bars:
                logger.info(
                    "🔍 통합 분석 실행 (완료 봉: %s/%s)",
                    self._ohlc_feed.completed_count(),
                    self._ohlc_min_completed_bars,
                )
                await self._process_integrated_analysis()
            elif len(self.price_history) > 0:
                if len(self.price_history) % 10 == 0:
                    logger.info(
                        "⏳ OHLC 봉 수집 중: %s/%s 완료 (틱 %s개)",
                        self._ohlc_feed.completed_count(),
                        self._ohlc_min_completed_bars,
                        len(self.price_history),
                    )
        
        except Exception as e:
            logger.error(f"❌ WebSocket 데이터 처리 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _process_integrated_analysis(self):
        """통합 분석 처리"""
        try:
            if self._ohlc_feed.completed_count() < self._ohlc_min_completed_bars:
                return

            price_data = self._ohlc_feed.dataframe(max_rows=200)
            if price_data.empty or len(price_data) < self._ohlc_min_completed_bars:
                return

            current_price = float(self.price_history[-1]['price']) if self.price_history else float(
                price_data["close"].iloc[-1]
            )
            if current_price <= 0.0:
                self._set_execution_trace(
                    decision="skipped",
                    reason="invalid_current_price",
                    details={"current_price": current_price},
                )
                self._save_state()
                return

            # ----- 🏛️ [Sensor & Logic] 레짐 감지 및 방어 모드 판단 (SSOT 230751) -----
            regime_id = "unknown"
            defense_mode = False
            if (
                getattr(self, "_prophecy_stack", None) is not None
                and self._ohlc_feed.completed_count() >= self._ohlc_min_completed_bars
            ):
                try:
                    from datetime import datetime as dt
                    vol = float(price_data["close"].pct_change().std()) if len(price_data) > 1 else 0.0
                    vol_score = float(min(max(vol / 0.1, 0.0), 1.0))
                    momentum_score = 0.5
                    if len(price_data) >= 14:
                        ret14 = (price_data["close"].iloc[-1] / price_data["close"].iloc[-14]) - 1.0
                        momentum_score = float(min(max((ret14 + 0.1) / 0.2, 0.0), 1.0))
                    volume_score = 0.5
                    if "volume" in price_data.columns and len(price_data) >= 20:
                        vmean = float(price_data["volume"].iloc[-20:].mean())
                        vcur = float(price_data["volume"].iloc[-1])
                        volume_score = float(min(vcur / vmean, 1.0)) if vmean > 0 else 0.5
                    market_factors = {"realized_vol": vol_score, "momentum_score": momentum_score, "volume_score": volume_score}
                    btc_summary = self._prophecy_stack.get_bitcoin_unified_field_summary(
                        as_of=dt.now(), pathology_vector=None, biblical_text=None, myeongri_gapja=None,
                        domain_hint="btc_spot", market_factors=market_factors
                    )
                    vec_4d = getattr(btc_summary, "unified_vector_4d", None) if btc_summary else None
                    # 다중 렌즈: 오늘 일주(갑자) 전달 시 L₃ 명리 렌즈 활성화. biblical_text=None → L₂ 비활성(단일/2렌즈 fallback)
                    myeongri_gapja = None
                    try:
                        from tools.core.unified_dynamics_engine import _solar_datetime_to_gapja
                        myeongri_gapja = _solar_datetime_to_gapja(dt.now())
                    except Exception:
                        pass
                    regime_result = self._prophecy_stack.get_current_regime(
                        vector_4d=vec_4d if isinstance(vec_4d, dict) else None,
                        biblical_text=None,
                        myeongri_gapja=myeongri_gapja,
                        weights=(0.4, 0.3, 0.3),
                    )
                    regime_id = regime_result.get("regime_id", "unknown")
                    regime_distance = float(regime_result.get("distance", float("inf")))
                    regime_resonance_pct = max(0.0, (1.0 - min(regime_distance, 1.0)) * 100.0)
                    # ----- [Logic] 붕괴 레짐 시 포스트잇 복원 -----
                    if regime_id in ("imf", "it_bubble", "lehman", "covid", "war_shock"):
                        fp = regime_result.get("fingerprint") or {}
                        codebook_ref = fp.get("codebook_ref") or "방법론#12"
                        uft_4d = getattr(btc_summary, "unified_vector_4d", {}) or {}
                        if uft_4d and isinstance(uft_4d, dict):
                            try:
                                from tools.core.postit_restoration_entry import restore_from_postit_and_codebook
                                out = restore_from_postit_and_codebook({"vector_4d": uft_4d, "codebook_ref": codebook_ref})
                                restoration_rate = float(out.get("restoration_rate", 0.0))
                                if regime_id in ("lehman", "covid", "war_shock") or restoration_rate < 0.5:
                                    defense_mode = True
                            except Exception as rest_e:
                                logger.debug(f"포스트잇 복원 실패: {rest_e}")
                    # ----- [Report & Action 선제 청산] 상태 전환 감지 -----
                    if defense_mode and not self._regime_defense_mode:
                        msg = f"🚨 [System Alert] 현재 위상 '{regime_id}' 레짐과 {regime_resonance_pct:.0f}% 공명 중. 방어 모드 전환."
                        logger.warning(msg)
                        if getattr(self, "alert_manager", None):
                            try:
                                self.alert_manager.send_alert("REGIME_DEFENSE", msg)
                            except Exception:
                                pass
                        # Observation Only가 꺼져 있을 때만 선제 청산 실행
                        if not getattr(self, "_regime_observation_only", True) and self.enable_trading:
                            pos = self._get_position()
                            if pos:
                                side = pos.get("side", "LONG")
                                logger.warning(f"🚨 방어 모드: 포지션 선제 청산 ({side})")
                                self._close_position(side, close_reason="regime_defense")
                        elif getattr(self, "_regime_observation_only", True):
                            logger.info("🛡️ [Observation Only] 방어 모드 진입 알림만 발송, 청산/매매 미연동")
                    elif not defense_mode and self._regime_defense_mode:
                        msg = f"✅ [System Alert] 위기 레짐 이탈 (현재: {regime_id}). 방어 모드 해제."
                        logger.info(msg)
                        if getattr(self, "alert_manager", None):
                            try:
                                self.alert_manager.send_alert("REGIME_NORMAL", msg)
                            except Exception:
                                pass
                    self._regime_defense_mode = defense_mode
                    self._last_regime_id = regime_id
                except Exception as reg_e:
                    logger.debug(f"레짐 감지 실패: {reg_e}")

            # Phase 1 방어망: 매 주기 손절/익절 체크 (M축 방어)
            await self._check_and_close_sl_tp(current_price)
            
            # 압축 기반 노이즈 제거 (선처리)
            compression_signal = None
            if self.compression_bridge:
                try:
                    compressed_data = await self.compression_bridge.compress_market_data(
                        price_data=price_data,
                        compression_mode="max_compression"
                    )
                    compression_signal = self.compression_bridge.extract_trading_signal_from_compression(
                        compressed_data
                    )
                    
                    logger.info(
                        f"📊 압축 분석: "
                        f"노이즈 필터링={compression_signal.get('noise_filtered', 0):.1%}, "
                        f"신호={compression_signal.get('signal', 'HOLD')}, "
                        f"신뢰도={compression_signal.get('confidence', 0):.2%}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 압축 분석 실패: {e}")
            
            # 통합 모니터링 분석
            result = await self.monitor.analyze_with_monitoring(
                price_data=price_data,
                current_price=current_price,
                news_texts=None,  # 실제 뉴스 데이터는 별도 수집 필요
                bio_signals=None  # 실제 생체 신호는 별도 수집 필요
            )

            # 레짐·0.25 기반 리스크 정책 적용 (1차 실물 레짐만, 2차 성경 레짐 미사용)
            self.risk_manager.apply_regime_policy(
                result.get("primary_regime"),
                result.get("divine_distance"),
            )
            
            # 🚀 압축 분석 결과 활용 강화 (P1 개선)
            if compression_signal:
                result["compression_signal"] = compression_signal
                compression_signal_type = compression_signal.get("signal", "HOLD")
                compression_confidence = compression_signal.get("confidence", 0.0)
                noise_filtered = compression_signal.get("noise_filtered", 0.0)
                
                # 통합 신호 확인
                integrated_signal = result.get("integrated_signal", "HOLD")
                integrated_confidence = result.get("integrated_confidence", 0.0)
                
                # 1. 압축 신호를 통합 신호 생성에 직접 반영
                if compression_signal_type in ["BUY", "SELL"]:
                    # 압축 신호와 통합 신호 일치 여부 확인
                    if compression_signal_type == integrated_signal:
                        # 신호 일치: 신뢰도 증가
                        signal_match_boost = min(0.1, compression_confidence * 0.15)  # 최대 10% 증가
                        integrated_confidence = min(1.0, integrated_confidence + signal_match_boost)
                        logger.info(f"✅ 압축 신호 일치 ({compression_signal_type}): 신뢰도 +{signal_match_boost:.1%}")
                    elif integrated_signal in ["BUY", "SELL"]:
                        # 신호 불일치: 신뢰도 감소
                        signal_mismatch_penalty = min(0.15, compression_confidence * 0.2)  # 최대 15% 감소
                        integrated_confidence = max(0.0, integrated_confidence - signal_mismatch_penalty)
                        logger.warning(f"⚠️ 압축 신호 불일치 (통합: {integrated_signal}, 압축: {compression_signal_type}): 신뢰도 -{signal_mismatch_penalty:.1%}")
                
                # 2. 노이즈 필터링 비율에 따른 연속적 신뢰도 조정
                # 노이즈 필터링 비율이 높을수록 신뢰도 증가
                if noise_filtered > 0.0:
                    # 연속적 조정: 0% → 0%, 50% → 5%, 100% → 10%
                    noise_boost = noise_filtered * 0.1  # 최대 10% 증가
                    integrated_confidence = min(1.0, integrated_confidence + noise_boost)
                    logger.info(f"📊 노이즈 필터링 연속적 조정: {noise_filtered:.1%} → 신뢰도 +{noise_boost:.1%}")
                
                # 최종 신뢰도 업데이트
                result["integrated_confidence"] = integrated_confidence
                result["integrated_signal"] = integrated_signal  # 압축 신호는 참고용, 통합 신호 유지
            else:
                # 압축 신호 없을 때 기본값
                integrated_signal = result.get("integrated_signal", "HOLD")
                integrated_confidence = result.get("integrated_confidence", 0.0)
            warning_level = result.get("warning_level", "NORMAL")
            self._set_4ai_signal_trace(
                integrated_signal=integrated_signal,
                integrated_confidence=integrated_confidence,
                warning_level=warning_level,
            )
            
            logger.info(
                f"📊 통합 분석 결과: {integrated_signal} "
                f"(신뢰도: {integrated_confidence:.2%}, 경고: {warning_level})"
            )
            result["mkm_singular_core"] = self._derive_singular_core(result)
            core_decision = str(result["mkm_singular_core"].get("decision") or "HOLD").upper()
            if core_decision == "HOLD":
                integrated_signal = "HOLD"
                integrated_confidence = min(integrated_confidence, 0.49)
                result["integrated_signal"] = integrated_signal
                result["integrated_confidence"] = integrated_confidence
                logger.warning(
                    "🔒 Singular core HOLD override (score=%.2f, reason=%s)",
                    float(result["mkm_singular_core"].get("score", 0.0)),
                    str(result["mkm_singular_core"].get("reason") or "unknown"),
                )
            else:
                singular_action = str(result["mkm_singular_core"].get("action") or "").upper()
                # If monitor/strategy consensus is HOLD but singular core passes,
                # promote to directional action for execution path continuity.
                if integrated_signal == "HOLD" and singular_action in ("BUY", "SELL"):
                    integrated_signal = singular_action
                    integrated_confidence = max(integrated_confidence, MIN_CONFIDENCE)
                    result["integrated_signal"] = integrated_signal
                    result["integrated_confidence"] = integrated_confidence
                    logger.info(
                        "🟢 Singular core promotion: HOLD -> %s (score=%.2f, confidence=%.2f)",
                        singular_action,
                        float(result["mkm_singular_core"].get("score", 0.0)),
                        float(integrated_confidence),
                    )
            self._update_singular_core_state(
                result=result,
                integrated_signal=integrated_signal,
                integrated_confidence=integrated_confidence,
                warning_level=warning_level,
                current_price=current_price,
            )
            
            # ----- 🏛️ [Action] 방어 모드 시 신규 매수 차단 (Observation Only면 미적용) -----
            if getattr(self, "_regime_defense_mode", False):
                if not getattr(self, "_regime_observation_only", True):
                    logger.warning(
                        f"🛡️ 방어 모드 활성화 (레짐: {self._last_regime_id}): 신규 진입 신호를 HOLD로 강제 변환합니다."
                    )
                    integrated_signal = "HOLD"
                    integrated_confidence = 0.0
                    result["integrated_signal"] = "HOLD"
                    result["integrated_confidence"] = 0.0
                else:
                    logger.info(
                        f"🛡️ [Observation Only] 방어 모드 (레짐: {self._last_regime_id}): 신호 강제 변환 없음."
                    )
            
            # 거래 실행 (활성화된 경우)
            self._set_4ai_signal_trace(
                integrated_signal=integrated_signal,
                integrated_confidence=integrated_confidence,
                warning_level=warning_level,
            )
            if self.enable_trading and integrated_signal in ["BUY", "SELL"]:
                risk_allowed, risk_reason = self._evaluate_4ai_risk_gate(
                    integrated_signal=integrated_signal,
                    integrated_confidence=integrated_confidence,
                    warning_level=warning_level,
                )
                if not risk_allowed:
                    self._set_execution_trace(
                        decision="skipped",
                        reason=risk_reason,
                        signal=integrated_signal,
                        confidence=integrated_confidence,
                        details={"warning_level": warning_level, "min_confidence": MIN_CONFIDENCE},
                    )
                    self._save_state()
                    return
                # Phase 1 방어망: 반대 신호 시 선청산 후 진입
                pos = self._get_position()
                if pos:
                    side = pos.get("side", "")
                    if (integrated_signal == "BUY" and side == "SHORT") or (integrated_signal == "SELL" and side == "LONG"):
                        reversal_allowed, reversal_reason, reversal_details = self._is_reversal_allowed(
                            current_side=str(side).upper(),
                            integrated_signal=integrated_signal,
                        )
                        if not reversal_allowed:
                            logger.info(
                                "🕒 반전 진입 지연: %s (%s)",
                                reversal_reason,
                                reversal_details,
                            )
                            self._set_execution_trace(
                                decision="skipped",
                                reason=reversal_reason,
                                signal=integrated_signal,
                                confidence=integrated_confidence,
                                details=reversal_details,
                            )
                            self._save_state()
                            return
                        logger.info(f"🔄 반대 신호 선청산: {side} → {integrated_signal} 진입 예정")
                        self._close_position(side, close_reason="signal_reversal")
                        self._last_reversal_ts = time.time()
                await self._execute_trade(integrated_signal, integrated_confidence)
            else:
                reason = "trading_disabled" if not self.enable_trading else "signal_not_directional"
                self._set_execution_trace(
                    decision="skipped",
                    reason=reason,
                    signal=integrated_signal,
                    confidence=integrated_confidence,
                    details={"warning_level": warning_level},
                )
            self._save_state()
        
        except Exception as e:
            logger.error(f"❌ 통합 분석 처리 오류: {e}")
            self._save_state()

    def _derive_singular_core(self, result: Dict[str, Any]) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        if isinstance(result, dict):
            # Prefer top-level fields when present, but fall back to strategy_analysis
            # because unified monitor stores vector outputs there.
            state = (
                result.get("predicted_state")
                or result.get("vector_4d")
                or ((result.get("strategy_analysis") or {}).get("predicted_state"))
                or ((result.get("strategy_analysis") or {}).get("vector_4d"))
                or {}
            )
        core = compute_core_score(
            CoreInput(
                s=float(state.get("S", 0.5)),
                l=float(state.get("L", 0.5)),
                k=float(state.get("K", 0.5)),
                m=float(state.get("M", 0.5)),
            )
        )
        decision = str(core.get("decision") or "HOLD")
        action = "LOCKED"
        if decision == "PASS_LONG":
            action = "BUY"
        elif decision == "PASS_SHORT":
            action = "SELL"
        return {
            "decision": "HOLD" if decision == "HOLD" else "PASS",
            "score": float(core.get("score_grid", 0.0)),
            "score_raw": float(core.get("score_raw", 0.0)),
            "reason": str(core.get("reason") or "unknown"),
            "contract_version": str(core.get("contract_version") or "unknown"),
            "action": action,
        }

    def _update_singular_core_state(
        self,
        result: Dict[str, Any],
        integrated_signal: str,
        integrated_confidence: float,
        warning_level: str,
        current_price: float,
    ) -> None:
        singular_core = result.get("mkm_singular_core") if isinstance(result, dict) else {}
        raw_action = (
            (singular_core or {}).get("action")
            if isinstance(singular_core, dict)
            else None
        )
        action = str(raw_action or integrated_signal or "LOCKED").upper()
        if action in ("HOLD", "LOW"):
            action = "LOCKED"
        if action not in ("BUY", "SELL", "LOCKED"):
            action = "LOCKED"

        self.signal_total_count += 1
        self.singular_action_counts[action] = self.singular_action_counts.get(action, 0) + 1
        self.last_signal_summary = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "symbol": self.symbol,
            "integrated_signal": integrated_signal,
            "integrated_confidence": round(float(integrated_confidence), 6),
            "warning_level": warning_level,
            "singular_action": action,
            "singular_decision": str((singular_core or {}).get("decision") or "HOLD"),
            "singular_score": float((singular_core or {}).get("score") or 0.0),
            "singular_score_raw": float((singular_core or {}).get("score_raw") or 0.0),
            "singular_reason": str((singular_core or {}).get("reason") or "unknown"),
            "price": round(float(current_price), 2),
            "regime_defense_mode": bool(getattr(self, "_regime_defense_mode", False)),
            "regime_id": getattr(self, "_last_regime_id", "unknown"),
        }

    def _set_execution_trace(
        self,
        *,
        decision: str,
        reason: str,
        signal: Optional[str] = None,
        confidence: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.last_execution_trace = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "decision": decision,
            "reason": reason,
            "signal": signal,
            "confidence": None if confidence is None else round(float(confidence), 6),
            "details": details or {},
        }
        self.last_4ai_trace["ai3_execution"] = {
            "decision": decision,
            "reason": reason,
            "signal": signal,
            "confidence": None if confidence is None else round(float(confidence), 6),
        }
        self.last_4ai_trace["timestamp"] = self.last_execution_trace["ts"]
        # SL/TP·리스크 등이 주기적으로 실행 추적만 갱신할 때 ai4가 옛날 주문 거절에 묶이지 않게 동기화한다.
        if reason != "execute_trade_called":
            self._set_4ai_audit_trace(final_decision=decision, final_reason=reason)

    def _set_4ai_signal_trace(
        self,
        *,
        integrated_signal: str,
        integrated_confidence: float,
        warning_level: str,
    ) -> None:
        self.last_4ai_trace["ai1_signal"] = {
            "signal": integrated_signal,
            "confidence": round(float(integrated_confidence), 6),
            "warning_level": str(warning_level),
        }
        self.last_4ai_trace["timestamp"] = datetime.now().isoformat(timespec="seconds")

    def _evaluate_4ai_risk_gate(
        self,
        *,
        integrated_signal: str,
        integrated_confidence: float,
        warning_level: str,
    ) -> Tuple[bool, str]:
        reason = "pass"
        allowed = True
        if _block_live_orders_for_prophecy_fusion(self._prophecy_stack, self.testnet):
            allowed = False
            reason = "prophecy_mainnet_guard"
            logger.warning(
                "Skipping live orders: ProphecyStack active with testnet=%s; "
                "set PROPHECY_FUSION_ALLOW_MAINNET=1 after operator review.",
                self.testnet,
            )
        elif integrated_confidence < MIN_CONFIDENCE:
            allowed = False
            reason = "confidence_below_min"
        elif str(warning_level).upper() == "CRITICAL":
            allowed = False
            reason = "critical_warning_level"
            logger.warning("🚨 CRITICAL 경고: 거래 중단")

        self.last_4ai_trace["ai2_risk"] = {
            "allowed": allowed,
            "reason": reason,
            "signal": integrated_signal,
            "confidence": round(float(integrated_confidence), 6),
            "warning_level": str(warning_level),
        }
        self.last_4ai_trace["timestamp"] = datetime.now().isoformat(timespec="seconds")
        return allowed, reason

    def _set_4ai_audit_trace(self, *, final_decision: str, final_reason: str) -> None:
        self.last_4ai_trace["ai4_audit"] = {
            "final_decision": final_decision,
            "final_reason": final_reason,
            "execution_trace_reason": self.last_execution_trace.get("reason"),
            "execution_trace_decision": self.last_execution_trace.get("decision"),
        }
        self.last_4ai_trace["timestamp"] = datetime.now().isoformat(timespec="seconds")

    def _track_position_open(self, signal: str) -> None:
        side = "LONG" if signal == "BUY" else "SHORT" if signal == "SELL" else None
        if side is None:
            return
        self._last_position_side = side
        self._last_position_open_ts = time.time()

    def _is_reversal_allowed(
        self,
        *,
        current_side: str,
        integrated_signal: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        desired_side = (
            "LONG" if integrated_signal == "BUY" else "SHORT" if integrated_signal == "SELL" else None
        )
        if desired_side is None or current_side == desired_side:
            return True, "not_reversal", {}

        now_ts = time.time()
        hold_elapsed = (
            (now_ts - self._last_position_open_ts)
            if self._last_position_open_ts is not None
            else None
        )
        if (
            hold_elapsed is not None
            and hold_elapsed < float(self._min_position_hold_seconds)
        ):
            return False, "reversal_blocked_min_hold", {
                "current_side": current_side,
                "desired_side": desired_side,
                "hold_elapsed_sec": round(float(hold_elapsed), 3),
                "min_hold_sec": int(self._min_position_hold_seconds),
            }

        cooldown_elapsed = now_ts - float(self._last_reversal_ts or 0.0)
        if cooldown_elapsed < float(self._reversal_cooldown_seconds):
            return False, "reversal_blocked_cooldown", {
                "current_side": current_side,
                "desired_side": desired_side,
                "cooldown_elapsed_sec": round(float(cooldown_elapsed), 3),
                "cooldown_required_sec": int(self._reversal_cooldown_seconds),
            }

        return True, "reversal_allowed", {
            "current_side": current_side,
            "desired_side": desired_side,
            "hold_elapsed_sec": (
                round(float(hold_elapsed), 3) if hold_elapsed is not None else None
            ),
            "min_hold_sec": int(self._min_position_hold_seconds),
            "cooldown_elapsed_sec": round(float(cooldown_elapsed), 3),
            "cooldown_required_sec": int(self._reversal_cooldown_seconds),
        }

    def _load_runtime_risk_limits(self) -> Dict[str, Any]:
        now = time.time()
        if now - self._risk_limits_cache_ts < 60 and self._risk_limits_cache:
            return dict(self._risk_limits_cache)

        default = {
            "max_position_size": None,
            "position_scale_cap": None,
            "daily_loss_cap_ratio": None,
            "source_path": None,
        }
        for p in self._risk_profile_candidates:
            if not p.exists():
                continue
            try:
                profile = json.loads(p.read_text(encoding="utf-8"))
                max_position_size = profile.get("max_position_size")
                if max_position_size is not None:
                    max_position_size = float(max_position_size)
                    if not (0.0 < max_position_size <= 1.0):
                        max_position_size = None

                trinity = profile.get("trinity_governor")
                position_scale_cap = None
                daily_loss_cap_ratio = None
                if isinstance(trinity, dict):
                    psc = trinity.get("position_scale_cap")
                    if psc is not None:
                        psc = float(psc)
                        if 0.0 < psc <= 1.0:
                            position_scale_cap = psc
                    dl_pct = trinity.get("daily_loss_cap_pct")
                    if dl_pct is not None:
                        dl_pct = float(dl_pct)
                        if dl_pct > 0.0:
                            daily_loss_cap_ratio = dl_pct / 100.0

                out = {
                    "max_position_size": max_position_size,
                    "position_scale_cap": position_scale_cap,
                    "daily_loss_cap_ratio": daily_loss_cap_ratio,
                    "source_path": str(p),
                }
                self._risk_limits_cache = out
                self._risk_limits_cache_ts = now
                return dict(out)
            except Exception:
                continue

        self._risk_limits_cache = default
        self._risk_limits_cache_ts = now
        return dict(default)

    def _collect_order_fill_quality(self, order_id: Optional[Any]) -> Dict[str, Any]:
        result = {
            "order_id": order_id,
            "fill_count": 0,
            "maker_true_count": 0,
            "maker_false_count": 0,
        }
        try:
            if order_id is None:
                return result
            if not hasattr(self.binance, "get_recent_fills"):
                return result
            oid = str(order_id)
            seen_keys: set[str] = set()
            # Fills can lag the order response; poll briefly and dedupe legs.
            for delay_s in (0.0, 0.2, 0.55, 1.1):
                if delay_s > 0:
                    time.sleep(delay_s)
                recent = self.binance.get_recent_fills(symbol=self.symbol, limit=100)
                if not isinstance(recent, list):
                    continue
                for f in recent:
                    if str(f.get("orderId")) != oid:
                        continue
                    tid = f.get("id") or f.get("tradeId")
                    if tid is not None:
                        key = f"id:{tid}"
                    else:
                        key = "leg:" + "|".join(
                            str(f.get(k, ""))
                            for k in ("price", "qty", "time", "maker", "realizedPnl")
                        )
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    result["fill_count"] += 1
                    if bool(f.get("maker")):
                        result["maker_true_count"] += 1
                    else:
                        result["maker_false_count"] += 1
        except Exception:
            pass
        return result

    def _save_state(self) -> None:
        try:
            connector_metrics: Dict[str, Any] = {}
            try:
                connector_metrics = self.connector.get_metrics() if self.connector else {}
            except Exception:
                connector_metrics = {}
            state = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "symbol": self.symbol,
                "running": self.running,
                "enable_trading": self.enable_trading,
                "runtime_config": {
                    "maker_only": bool(self._maker_only),
                    "strict_maker_enforcement": bool(self._strict_maker_enforcement),
                    "min_position_hold_seconds": int(self._min_position_hold_seconds),
                    "reversal_cooldown_seconds": int(self._reversal_cooldown_seconds),
                    "risk_limits": self._load_runtime_risk_limits(),
                },
                "ws_tick_count": int(self.ws_tick_count),
                "connector_metrics": connector_metrics,
                "startup_reconcile": self.startup_reconcile_status,
                "signal_total_count": self.signal_total_count,
                "singular_action_counts": self.singular_action_counts,
                "last_signal_summary": self.last_signal_summary,
                "last_execution_trace": self.last_execution_trace,
                "last_4ai_trace": self.last_4ai_trace,
                "exchange_runtime_state": self._collect_exchange_runtime_state(),
            }
            self.state_file.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.debug(f"상태 저장 실패: {e}")

    async def _state_persist_loop(self) -> None:
        """Persist runtime liveness/state regardless of signal warmup."""
        while self.running:
            try:
                self._save_state()
            except Exception:
                pass
            await asyncio.sleep(15)

    def _collect_exchange_runtime_state(self) -> Dict[str, Any]:
        now = time.time()
        if now - self._exchange_runtime_state_cache_ts < 15 and self._exchange_runtime_state_cache:
            return self._exchange_runtime_state_cache

        state: Dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "current_position": None,
            "open_orders_count": None,
            "recent_fills_count": None,
            "exchange_error": None,
            "credential_source": "unknown",
            "credential_key_suffix": "****",
        }
        try:
            position = self.binance.get_position(self.symbol) if hasattr(self.binance, "get_position") else None
            open_orders = self.binance.get_open_orders(self.symbol) if hasattr(self.binance, "get_open_orders") else []
            recent_fills = self.binance.get_recent_fills(symbol=self.symbol, limit=20) if hasattr(self.binance, "get_recent_fills") else []
            cred = get_last_binance_credential_meta()
            state.update(
                {
                    "current_position": position if isinstance(position, dict) else None,
                    "open_orders_count": len(open_orders) if isinstance(open_orders, list) else None,
                    "recent_fills_count": len(recent_fills) if isinstance(recent_fills, list) else None,
                    "credential_source": str(cred.get("credential_source") or "unknown"),
                    "credential_key_suffix": str(cred.get("credential_key_suffix") or "****"),
                }
            )
        except Exception as e:
            state["exchange_error"] = str(e)

        self._exchange_runtime_state_cache = state
        self._exchange_runtime_state_cache_ts = now
        return state

    def _startup_reconcile(self) -> None:
        """
        Trustless bootstrap:
        Always align runtime view from exchange before signal loop starts.
        """
        try:
            open_orders = []
            recent_fills = []
            position = None

            if hasattr(self.binance, "get_open_orders"):
                open_orders = self.binance.get_open_orders(self.symbol) or []
            position = self._get_position()
            if hasattr(self.binance, "get_recent_fills"):
                recent_fills = self.binance.get_recent_fills(self.symbol, limit=50) or []

            self.startup_reconcile_status = {
                "completed": True,
                "ts": datetime.now().isoformat(timespec="seconds"),
                "open_orders_count": len(open_orders) if isinstance(open_orders, list) else None,
                "has_position": bool(position),
                "position_side": (position or {}).get("side") if isinstance(position, dict) else None,
                "position_qty": (position or {}).get("quantity") if isinstance(position, dict) else None,
                "recent_fills_count": len(recent_fills) if isinstance(recent_fills, list) else None,
                "error": None,
            }
            if isinstance(position, dict) and float(position.get("quantity") or 0.0) > 0.0:
                self._last_position_side = str(position.get("side") or "").upper() or None
                self._last_position_open_ts = time.time()
            logger.info(
                "🔁 Startup reconcile 완료: open_orders=%s, has_position=%s, recent_fills=%s",
                self.startup_reconcile_status["open_orders_count"],
                self.startup_reconcile_status["has_position"],
                self.startup_reconcile_status["recent_fills_count"],
            )
        except Exception as e:
            self.startup_reconcile_status = {
                "completed": False,
                "ts": datetime.now().isoformat(timespec="seconds"),
                "open_orders_count": None,
                "has_position": None,
                "position_side": None,
                "position_qty": None,
                "recent_fills_count": None,
                "error": str(e),
            }
            logger.warning(f"⚠️ Startup reconcile 실패: {e}")
    
    async def _execute_trade(self, signal: str, confidence: float):
        """거래 실행 (OTel: execute_trade 스팬)."""
        from src.monitoring import trading_otel as _otel

        with _otel.span(
            "execute_trade",
            attributes={
                "signal": str(signal),
                "symbol": self.symbol,
                "confidence": str(confidence),
                "testnet": str(self.testnet),
                "enable_trading": str(self.enable_trading),
            },
        ):
            await self._execute_trade_impl(signal, confidence)

    async def _execute_trade_impl(self, signal: str, confidence: float):
        """거래 실행 구현."""
        try:
            self._set_execution_trace(
                decision="attempted",
                reason="execute_trade_called",
                signal=signal,
                confidence=confidence,
            )
            logger.info(
                f"📈 거래 신호 수신: {signal} "
                f"(신뢰도: {confidence:.2%})"
            )
            
            # 현재 자본 확인 (실제 계좌에서)
            try:
                account_info = self.binance.get_account_info()
                current_capital = account_info.get('available_balance', self.initial_capital)
            except:
                current_capital = self.initial_capital  # 폴백
            
            current_time = datetime.now()
            
            # 리스크 가디언 검증 (우선순위)
            if self.risk_guardian:
                # 일일 추적 업데이트
                self.risk_guardian.update_daily_tracking(current_time, current_capital)
                
                # 거래 허용 여부 확인
                allowed, reason = self.risk_guardian.check_trading_allowed(current_time)
                if not allowed:
                    logger.warning(f"⚠️ 리스크 가디언이 거래를 차단했습니다: {reason}")
                    self._set_execution_trace(
                        decision="skipped",
                        reason="risk_guardian_blocked",
                        signal=signal,
                        confidence=confidence,
                        details={"risk_guardian_reason": reason},
                    )
                    return
                
                # Drawdown 계산
                current_equity = current_capital
                self.equity_history.append(current_equity)
                if len(self.equity_history) > 1000:
                    self.equity_history = self.equity_history[-1000:]
                
                # Peak Equity 업데이트
                if current_equity > self.peak_equity:
                    self.peak_equity = current_equity
                
                # 현재 Drawdown 계산
                current_drawdown = abs((current_equity - self.peak_equity) / self.peak_equity) if self.peak_equity > 0 else 0.0
                
                # 동적 포지션 크기 계산
                dynamic_position_size = self.risk_guardian.calculate_dynamic_position_size(
                    current_drawdown,
                    current_capital
                )
                
                logger.info(
                    f"🛡️ 리스크 가디언 상태: "
                    f"Drawdown={current_drawdown:.2%}, "
                    f"포지션 크기={dynamic_position_size:.2%}"
                )
            else:
                dynamic_position_size = 0.30  # 기본값

            risk_limits = self._load_runtime_risk_limits()
            cap_candidates = []
            if risk_limits.get("max_position_size") is not None:
                cap_candidates.append(float(risk_limits["max_position_size"]))
            if risk_limits.get("position_scale_cap") is not None:
                cap_candidates.append(float(risk_limits["position_scale_cap"]))
            if cap_candidates:
                hard_cap_ratio = min(cap_candidates)
                if dynamic_position_size > hard_cap_ratio:
                    logger.warning(
                        "🧷 포지션 비중 하드캡 적용: %.2f%% -> %.2f%% (source=%s)",
                        dynamic_position_size * 100.0,
                        hard_cap_ratio * 100.0,
                        risk_limits.get("source_path"),
                    )
                dynamic_position_size = min(dynamic_position_size, hard_cap_ratio)
            dynamic_position_size = max(0.001, float(dynamic_position_size))

            if (
                self.risk_guardian
                and risk_limits.get("daily_loss_cap_ratio") is not None
            ):
                cap_ratio = float(risk_limits["daily_loss_cap_ratio"])
                if 0.0 < cap_ratio < float(self.risk_guardian.daily_loss_limit):
                    self.risk_guardian.daily_loss_limit = cap_ratio
            
            # 기존 리스크 관리 검증
            if not self.risk_manager.can_trade():
                logger.warning("⚠️ 리스크 관리 시스템이 거래를 차단했습니다.")
                self._set_execution_trace(
                    decision="skipped",
                    reason="risk_manager_blocked",
                    signal=signal,
                    confidence=confidence,
                )
                return

            # 기존 포지션 과대/동일방향 누적 진입 차단
            existing_pos = self._get_position()
            if isinstance(existing_pos, dict):
                existing_side = str(existing_pos.get("side") or "").upper()
                existing_qty = float(existing_pos.get("quantity") or 0.0)
                desired_side = "LONG" if signal == "BUY" else "SHORT"
                if existing_qty > 0.0 and existing_side == desired_side:
                    details = {
                        "existing_side": existing_side,
                        "existing_qty": existing_qty,
                        "desired_side": desired_side,
                    }
                    self._set_execution_trace(
                        decision="skipped",
                        reason="same_side_pyramiding_blocked",
                        signal=signal,
                        confidence=confidence,
                        details=details,
                    )
                    return

            # 주문 수량 계산 (USDT 선물 기준)
            try:
                mark_price = float(self.binance.get_current_price(self.symbol) or 0.0)
            except Exception:
                mark_price = 0.0
            if mark_price <= 0:
                self._set_execution_trace(
                    decision="skipped",
                    reason="invalid_mark_price",
                    signal=signal,
                    confidence=confidence,
                )
                return

            if (
                isinstance(existing_pos, dict)
                and existing_pos.get("quantity") is not None
                and risk_limits.get("max_position_size") is not None
            ):
                existing_qty = float(existing_pos.get("quantity") or 0.0)
                if existing_qty > 0.0:
                    existing_notional = existing_qty * mark_price
                    cap_ratio = float(risk_limits["max_position_size"])
                    cap_notional = float(current_capital) * cap_ratio * float(self.leverage)
                    if cap_notional > 0 and existing_notional > (cap_notional * 1.05):
                        details = {
                            "existing_notional": round(existing_notional, 6),
                            "cap_notional": round(cap_notional, 6),
                            "cap_ratio": cap_ratio,
                            "leverage": float(self.leverage),
                            "existing_qty": existing_qty,
                        }
                        self._set_execution_trace(
                            decision="skipped",
                            reason="existing_position_exceeds_cap",
                            signal=signal,
                            confidence=confidence,
                            details=details,
                        )
                        return
            margin_usdt = max(0.0, float(current_capital) * float(dynamic_position_size))
            raw_quantity = (margin_usdt * float(self.leverage)) / mark_price
            order_quantity = round(max(0.001, raw_quantity), 3)
            
            # 주문 실행 전 체결/포지션 스냅샷 (빈 응답 대비 사후 검증용)
            fills_before = None
            try:
                if hasattr(self.binance, "get_recent_fills"):
                    recent_before = self.binance.get_recent_fills(symbol=self.symbol, limit=20)
                    if isinstance(recent_before, list):
                        fills_before = len(recent_before)
            except Exception:
                fills_before = None

            # 주문 실행 (동적 포지션 크기 적용)
            if signal == "BUY":
                order = self.binance.open_long_position(
                    symbol=self.symbol,
                    quantity=order_quantity,
                    leverage=self.leverage,
                )
            elif signal == "SELL":
                order = self.binance.open_short_position(
                    symbol=self.symbol,
                    quantity=order_quantity,
                    leverage=self.leverage,
                )
            else:
                self._set_execution_trace(
                    decision="skipped",
                    reason="non_directional_signal",
                    signal=signal,
                    confidence=confidence,
                )
                return
            
            if order is not None:
                position_size_str = f"{dynamic_position_size:.2%}" if self.risk_guardian else "기본"
                logger.info(
                    f"✅ 주문 실행 완료: {signal} "
                    f"(포지션 크기: {position_size_str})"
                )
                order_id = order.get("orderId") if isinstance(order, dict) else None
                fill_quality = self._collect_order_fill_quality(order_id)
                if (
                    self._maker_only
                    and fill_quality.get("maker_false_count", 0) > 0
                    and self._strict_maker_enforcement
                ):
                    details = {
                        "has_order_payload": True,
                        "quantity": order_quantity,
                        "mark_price": mark_price,
                        "margin_usdt": round(float(margin_usdt), 6),
                        "maker_only": True,
                        "strict_maker_enforcement": True,
                        "fill_quality": fill_quality,
                    }
                    self.enable_trading = False
                    logger.error(
                        "🛑 Maker 위반 체결 감지로 거래 중단: order_id=%s quality=%s",
                        order_id,
                        fill_quality,
                    )
                    self._set_execution_trace(
                        decision="skipped",
                        reason="maker_violation_trading_paused",
                        signal=signal,
                        confidence=confidence,
                        details=details,
                    )
                    self._save_state()
                    return
                
                # 리스크 관리 업데이트
                if hasattr(self.risk_manager, "record_trade"):
                    self.risk_manager.record_trade(order)
                else:
                    logger.debug("risk_manager.record_trade 미구현: 업데이트 스킵")
                self._set_execution_trace(
                    decision="executed",
                    reason="order_submitted",
                    signal=signal,
                    confidence=confidence,
                    details={
                        "has_order_payload": True,
                        "quantity": order_quantity,
                        "mark_price": mark_price,
                        "margin_usdt": round(float(margin_usdt), 6),
                        "maker_only": bool(self._maker_only),
                        "strict_maker_enforcement": bool(self._strict_maker_enforcement),
                        "fill_quality": fill_quality,
                    },
                )
                self._track_position_open(signal)
                
                # 리스크 가디언 업데이트 (거래 결과는 주문 체결 후 별도로 업데이트 필요)
                # 실제 PnL은 주문 체결 후 업데이트
            else:
                # 일부 거래소/클라이언트 경로는 주문 응답 바디가 비어도 실제 체결이 발생할 수 있어
                # 포지션/체결 변화를 2차 확인해 오탐 실패를 줄인다.
                await asyncio.sleep(0.7)
                pos_after = None
                fills_after = None
                try:
                    pos_after = self._get_position()
                except Exception:
                    pos_after = None
                try:
                    if hasattr(self.binance, "get_recent_fills"):
                        recent_after = self.binance.get_recent_fills(symbol=self.symbol, limit=20)
                        if isinstance(recent_after, list):
                            fills_after = len(recent_after)
                except Exception:
                    fills_after = None

                expected_side = "LONG" if signal == "BUY" else "SHORT"
                position_matches = (
                    isinstance(pos_after, dict)
                    and str(pos_after.get("side", "")).upper() == expected_side
                    and float(pos_after.get("quantity") or 0.0) > 0.0
                )
                fills_increased = (
                    fills_before is not None
                    and fills_after is not None
                    and fills_after > fills_before
                )

                if position_matches or fills_increased:
                    logger.warning("⚠️ 주문 응답은 비었지만 사후 상태 기준 체결 반영 확인")
                    self._set_execution_trace(
                        decision="executed",
                        reason="order_reconciled_after_empty_response",
                        signal=signal,
                        confidence=confidence,
                        details={
                            "quantity": order_quantity,
                            "mark_price": mark_price,
                            "margin_usdt": round(float(margin_usdt), 6),
                            "fills_before": fills_before,
                            "fills_after": fills_after,
                            "position_side_after": (pos_after or {}).get("side") if isinstance(pos_after, dict) else None,
                        },
                    )
                    self._track_position_open(signal)
                    return

                order_error = None
                if hasattr(self.binance, "get_last_order_error"):
                    try:
                        order_error = self.binance.get_last_order_error()
                    except Exception:
                        order_error = None
                logger.error(f"❌ 주문 실행 실패: {signal}")
                self._set_execution_trace(
                    decision="failed",
                    reason="order_empty_response",
                    signal=signal,
                    confidence=confidence,
                    details={
                        "quantity": order_quantity,
                        "mark_price": mark_price,
                        "margin_usdt": round(float(margin_usdt), 6),
                        "fills_before": fills_before,
                        "fills_after": fills_after,
                        "position_side_after": (pos_after or {}).get("side") if isinstance(pos_after, dict) else None,
                        "order_error": order_error,
                    },
                )
        
        except Exception as e:
            try:
                from opentelemetry import trace as _otel_trace

                _sp = _otel_trace.get_current_span()
                if _sp is not None and getattr(_sp, "is_recording", lambda: False)():
                    _sp.record_exception(e)
            except Exception:
                pass
            logger.error(f"❌ 거래 실행 오류: {e}")
            self._set_execution_trace(
                decision="failed",
                reason="execute_trade_exception",
                signal=signal,
                confidence=confidence,
                details={"error": str(e)},
            )
    
    async def run(self):
        """메인 실행 루프"""
        logger.info("🚀 실전 거래 엔진 + 통합 모니터링 시스템 시작")
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   테스트넷: {self.testnet}")
        logger.info(f"   초기 자본: {self.initial_capital} USDT")
        logger.info(f"   레버리지: {self.leverage}배")
        logger.info(f"   모니터링: {'활성화' if self.monitor.enable_monitoring else '비활성화'}")
        logger.info(f"   거래: {'활성화' if self.enable_trading else '비활성화 (모니터링만)'}")
        logger.info(f"   Maker-only: {'ON' if self._maker_only else 'OFF'} (env MKM_MAKER_ONLY)")
        if self.risk_guardian:
            logger.info(f"   🛡️ 리스크 가디언: 활성화 (MDD <15% 목표)")
            logger.info(f"      기본 포지션 크기: {self.risk_guardian.base_position_size:.2%}")
            logger.info(f"      일일 손실 한도: {self.risk_guardian.daily_loss_limit:.2%}")
            logger.info(f"      연속 손실 제한: {self.risk_guardian.max_consecutive_losses}회")
        if self.compression_bridge and self.compression_bridge.enable_compression:
            logger.info(f"   📊 압축-트레이딩 브릿지: 활성화 (노이즈 제거, 420배 빠름)")
            logger.info(f"      압축 모드: max_compression (99% 노이즈 제거)")
        
        self._startup_reconcile()
        self.running = True
        self._save_state()
        
        persist_task = asyncio.create_task(self._state_persist_loop())

        # WebSocket 커넥터 실행
        try:
            await self.connector.run()
        except KeyboardInterrupt:
            logger.info("⏹️ 사용자에 의해 중단됨")
        finally:
            self.running = False
            persist_task.cancel()
            try:
                await persist_task
            except asyncio.CancelledError:
                pass
            self._save_state()
            
            # 정리
            await self.connector.disconnect()
            
            # 최종 리포트 저장
            report_path = self.monitor.save_integrated_report()
            logger.info(f"📁 최종 리포트 저장: {report_path}")
            
            logger.info("✅ 실전 거래 엔진 + 통합 모니터링 시스템 종료")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 조회"""
        total = int(self.signal_total_count or 0)
        buy = int(self.singular_action_counts.get("BUY", 0) or 0)
        sell = int(self.singular_action_counts.get("SELL", 0) or 0)
        locked = int(self.singular_action_counts.get("LOCKED", 0) or 0)
        status = {
            "running": self.running,
            "price_history_size": len(self.price_history),
            "monitoring_enabled": self.monitor.enable_monitoring,
            "trading_enabled": self.enable_trading,
            "runtime_config": {
                "maker_only": bool(self._maker_only),
                "strict_maker_enforcement": bool(self._strict_maker_enforcement),
                "min_position_hold_seconds": int(self._min_position_hold_seconds),
                "reversal_cooldown_seconds": int(self._reversal_cooldown_seconds),
                "risk_limits": self._load_runtime_risk_limits(),
            },
            "startup_reconcile": self.startup_reconcile_status,
            "mkm_singular_core": {
                "total_signals": total,
                "buy_count": buy,
                "sell_count": sell,
                "locked_count": locked,
                "locked_ratio": (locked / total) if total > 0 else None,
                "buy_ratio": (buy / total) if total > 0 else None,
                "sell_ratio": (sell / total) if total > 0 else None,
                "last_signal_summary": self.last_signal_summary or None,
            },
            "last_execution_trace": self.last_execution_trace or None,
            "last_4ai_trace": self.last_4ai_trace or None,
            "exchange_runtime_state": self._collect_exchange_runtime_state(),
            "risk_manager": {
                "daily_pnl": self.risk_manager.daily_pnl,
                "can_trade": self.risk_manager.can_trade(),
            },
            "recent_alerts": self.monitor.get_recent_alerts(24)
        }
        
        # 리스크 가디언 상태 추가
        if self.risk_guardian:
            current_equity = self.equity_history[-1] if self.equity_history else self.initial_capital
            current_drawdown = abs((current_equity - self.peak_equity) / self.peak_equity) if self.peak_equity > 0 else 0.0
            
            status["risk_guardian"] = {
                **self.risk_guardian.get_status(),
                "current_drawdown": current_drawdown,
                "peak_equity": self.peak_equity,
                "current_equity": current_equity
            }
        
        # 압축 브릿지 상태 추가
        if self.compression_bridge:
            status["compression_bridge"] = self.compression_bridge.get_statistics()
        
        return status


async def main():
    """테스트 실행"""
    engine = RealtimeTradingWithMonitoring(
        symbol="BTCUSDT",
        testnet=True,
        initial_capital=1000.0,
        leverage=2,
        enable_monitoring=True,
        enable_trading=False  # 테스트: 모니터링만
    )
    
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())

