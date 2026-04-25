#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Financial Sovereign Upgrade 블랙박스 백테스트 시스템

과거 시점에서 Financial Sovereign Harness와 명리 컨트롤러 Phase 2가 통합된
비트코인 자동매매 시스템의 성능을 검증합니다.

핵심 특징:
1. 블랙박스 테스트: 실제 전략 클래스 사용 (내부 로직 숨김)
2. 과거 데이터 재현: 실제 시장 조건 재현
3. Financial Sovereign Harness 통합: Signal ID 생성 및 검증
4. 명리 컨트롤러 Phase 2 통합: 타이밍 판단 및 신뢰도 조정
5. 성능 지표 수집: 수익률, 승률, 최대 낙폭 등

작성일: 2026-02-14
"""

import argparse
import os
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import pandas as pd
import numpy as np
import json
import logging
import yaml

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
bitcoin_trading_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))
sys.path.insert(0, str(bitcoin_trading_root))
sys.path.insert(0, str(bitcoin_trading_root / "src"))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 백테스트에서 하위 모듈 INFO/WARNING 스팸 억제 (초기화·루프 공통)
# import 경로에 따라 __name__이 src.* 또는 패키지 루트(*.strategy.*)로 달라질 수 있음.
_QUIET_EXTRA_LOGGER_NAMES: Tuple[str, ...] = (
    "tools.core.financial_sovereign_harness",
)
_QUIET_BACKTEST_LOGGER_SUFFIXES: Tuple[str, ...] = (
    "integration.athena_router_integration",
    "analysis.p1_p4_calibration",
    "analysis.phase_resonance_fact_check",
    "strategy.crypto_nitro_live_strategy",
    "strategy.phase1_model_predictor",
    "models.timexer_exog_model",
    "analysis.quaternion_finance_analyzer",
    "analysis.sbsc_strategy_verifier",
    "strategy.pmi_nitro_engine",
)
_QUIET_BACKTEST_LOGGER_NAMES: Tuple[str, ...] = tuple(
    name
    for suffix in _QUIET_BACKTEST_LOGGER_SUFFIXES
    for name in (f"src.{suffix}", suffix)
) + _QUIET_EXTRA_LOGGER_NAMES

# Logger.setLevel(ERROR)면 하위 로거의 INFO·WARNING이 버려져 스팸·경고 노이즈가 줄어듦
_QUIET_CHILD_LOG_LEVEL = logging.ERROR


@contextmanager
def _suppress_backtest_child_loggers(level: int = _QUIET_CHILD_LOG_LEVEL):
    prev: Dict[str, int] = {}
    try:
        for name in _QUIET_BACKTEST_LOGGER_NAMES:
            lg = logging.getLogger(name)
            prev[name] = lg.level
            lg.setLevel(level)
        yield
    finally:
        for name, old in prev.items():
            logging.getLogger(name).setLevel(old)


def _resolve_quiet_logging(
    quiet_logging: Optional[bool],
    record_signals: bool,
    record_equity_curve: bool,
) -> bool:
    if quiet_logging is None:
        ql = not (record_signals and record_equity_curve)
    else:
        ql = bool(quiet_logging)
    _q = os.environ.get("MKM_BACKTEST_QUIET", "").strip().lower()
    if _q in ("1", "true", "yes", "on"):
        ql = True
    elif _q in ("0", "false", "no", "off"):
        ql = False
    return ql


STRATEGY_AVAILABLE = False
_CryptoNitroLiveStrategyCls: Optional[type] = None


def _ensure_crypto_nitro_live_strategy_class(quiet_logging: bool) -> Optional[type]:
    """첫 호출 시 전략 클래스를 로드. quiet_logging 이면 import·초기화 로그 스팸을 줄인다."""
    global STRATEGY_AVAILABLE, _CryptoNitroLiveStrategyCls
    if _CryptoNitroLiveStrategyCls is not None:
        return _CryptoNitroLiveStrategyCls
    guard = (
        _suppress_backtest_child_loggers(_QUIET_CHILD_LOG_LEVEL)
        if quiet_logging
        else nullcontext()
    )
    root_lg = logging.getLogger()
    prev_root_level = root_lg.level
    with guard:
        if quiet_logging:
            root_lg.setLevel(logging.ERROR)
        try:
            try:
                from src.strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy as Cls
                _CryptoNitroLiveStrategyCls = Cls
                STRATEGY_AVAILABLE = True
                return Cls
            except ImportError:
                pass
            try:
                from strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy as Cls
                _CryptoNitroLiveStrategyCls = Cls
                STRATEGY_AVAILABLE = True
                return Cls
            except ImportError as e:
                STRATEGY_AVAILABLE = False
                logger.warning(f"⚠️ CryptoNitroLiveStrategy를 import할 수 없습니다: {e}")
                return None
        finally:
            if quiet_logging:
                root_lg.setLevel(prev_root_level)


_FinancialSovereignHarnessCls: Optional[type] = None


def _ensure_financial_sovereign_harness_class() -> Optional[type]:
    """Lazy-load harness; 실패 시 None (모듈 로드 시 경고 로그를 내지 않음)."""
    global _FinancialSovereignHarnessCls
    if _FinancialSovereignHarnessCls is not None:
        return _FinancialSovereignHarnessCls
    try:
        from tools.core.financial_sovereign_harness import FinancialSovereignHarness as H
        _FinancialSovereignHarnessCls = H
        return H
    except ImportError:
        pass
    try:
        tools_path = workspace_root / "tools" / "core"
        if tools_path.exists():
            sys.path.insert(0, str(tools_path.parent.parent))
        from tools.core.financial_sovereign_harness import FinancialSovereignHarness as H
        _FinancialSovereignHarnessCls = H
        return H
    except ImportError:
        logger.debug("FinancialSovereignHarness 사용 불가 (tools.core 미구성)")
        return None


class FinancialSovereignBacktester:
    """
    🏛️ Financial Sovereign Upgrade 블랙박스 백테스트 시스템
    
    과거 데이터를 사용하여 통합된 시스템의 성능을 검증합니다.
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        commission_rate: float = 0.001,  # 0.1% 수수료
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        data_file: Optional[str] = None,  # 과거 데이터 파일 경로
        calibration_mode: bool = False,  # True: harness 미생성, 전략 경량 모드(4D/PhaseSpace/Historical 스킵)
        backtest_engine: str = "fast",  # cpu|fast (fast: 루프 오버헤드 절감)
        record_signals: bool = True,  # False면 signal history 누적을 생략해 메모리/속도 최적화
        record_equity_curve: bool = True,  # False면 equity_curve 누적을 생략
        quiet_logging: Optional[bool] = None,  # None이면 record 모두 켜진 경우만 상세 로그, 아니면 하위 로거 억제
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 레버리지
            commission_rate: 거래 수수료율
            start_date: 백테스트 시작 날짜
            end_date: 백테스트 종료 날짜
            data_file: 과거 데이터 파일 경로 (CSV 또는 JSON)
            calibration_mode: 캘리브레이션용 경량 모드 (harness 미생성, 전략은 backtest_calibration=True)
            quiet_logging: 하위 모듈 반복 로그 억제. None이면 signal·equity 기록이 모두 True일 때만 상세 로그.
                MKM_BACKTEST_QUIET=1|0 으로 덮어쓸 수 있음.
        """
        ql = _resolve_quiet_logging(quiet_logging, record_signals, record_equity_curve)
        CryptoNitroCls = _ensure_crypto_nitro_live_strategy_class(ql)
        if CryptoNitroCls is None:
            raise ImportError("CryptoNitroLiveStrategy를 사용할 수 없습니다.")

        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.commission_rate = commission_rate
        self.start_date = start_date
        self.end_date = end_date
        self.data_file = data_file
        self.calibration_mode = calibration_mode
        self.backtest_engine = backtest_engine if backtest_engine in {"cpu", "fast"} else "fast"
        self.record_signals = bool(record_signals)
        self.record_equity_curve = bool(record_equity_curve)
        self.quiet_logging = ql

        # 백테스트 상태
        self.capital = initial_capital
        self.position = 0.0  # 포지션 크기 (BTC)
        self.position_value = 0.0  # 포지션 가치 (USDT)
        self.entry_price = 0.0
        self.position_side = None  # "LONG" or "SHORT"
        
        # 거래 기록
        self.trades = []
        self.equity_curve = []
        self.signals = []
        
        # 성능 지표
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        _init_guard = (
            _suppress_backtest_child_loggers(_QUIET_CHILD_LOG_LEVEL)
            if self.quiet_logging
            else nullcontext()
        )
        with _init_guard:
            # Financial Sovereign Harness 통합 (calibration_mode면 스킵)
            self.harness = None
            if not calibration_mode:
                HarnessCls = _ensure_financial_sovereign_harness_class()
                if HarnessCls is not None:
                    try:
                        codebook_path = bitcoin_trading_root / "data" / "backtest_signal_codebook.json"
                        codebook_path.parent.mkdir(parents=True, exist_ok=True)
                        self.harness = HarnessCls(codebook_path=str(codebook_path))
                        logger.info("✅ Financial Sovereign Harness 초기화 완료 (백테스트용)")
                    except Exception as e:
                        logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")

            # 전략 초기화 (블랙박스) — calibration_mode면 경량 모드(4D/PhaseSpace/Historical 스킵)
            self.strategy = CryptoNitroCls(
                symbol=symbol,
                initial_capital=initial_capital,
                leverage=leverage,
                use_great_trunk_filter=True,
                binance_client=None,  # 백테스트에서는 실제 API 불필요
                backtest_calibration=calibration_mode,
            )
        
        logger.info(f"✅ Financial Sovereign Backtester 초기화 완료")
        logger.info(f"   초기 자본: ${initial_capital:,.2f}")
        logger.info(f"   레버리지: {leverage}x")
        logger.info(f"   수수료율: {commission_rate:.2%}")
    
    def download_historical_data(
        self,
        months: int = 6,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Binance에서 과거 데이터 자동 다운로드
        
        Args:
            months: 다운로드할 개월 수
            interval: 시간 간격 ("1m", "5m", "15m", "1h", "4h", "1d" 등)
        
        Returns:
            가격 데이터 DataFrame
        """
        logger.info("📥 Binance에서 과거 데이터 다운로드 중...")
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   간격: {interval}")
        logger.info(f"   기간: 최근 {months}개월")
        
        try:
            import requests
            from datetime import timedelta
            
            # Binance 공개 API 엔드포인트 (API 키 불필요)
            url = "https://api.binance.com/api/v3/klines"
            
            # 날짜 범위 계산
            end_date = self.end_date if self.end_date else datetime.now()
            start_date = self.start_date if self.start_date else (end_date - timedelta(days=months * 30))
            
            # 시작 시간 (밀리초)
            start_time = int(start_date.timestamp() * 1000)
            end_time = int(end_date.timestamp() * 1000)
            
            all_klines = []
            current_start = start_time
            limit = 1000  # Binance API 최대 제한
            
            logger.info(f"   시작: {start_date.strftime('%Y-%m-%d')}")
            logger.info(f"   종료: {end_date.strftime('%Y-%m-%d')}")
            
            # 배치로 데이터 다운로드
            while current_start < end_time:
                params = {
                    'symbol': self.symbol,
                    'interval': interval,
                    'startTime': current_start,
                    'endTime': end_time,
                    'limit': limit
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                klines = response.json()
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # 다음 배치 시작 시간 (마지막 캔들의 종료 시간 + 1ms)
                current_start = klines[-1][6] + 1  # close_time + 1ms
                
                # 진행 상황 출력
                progress = (current_start - start_time) / (end_time - start_time) * 100
                print(f"   진행: {progress:.1f}% ({len(all_klines)}개 캔들)", end='\r')
                
                # API Rate Limit 방지 (0.1초 대기)
                import time
                time.sleep(0.1)
            
            logger.info("")  # 줄바꿈
            
            if not all_klines:
                logger.error("❌ 데이터를 다운로드할 수 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # 날짜 컬럼 변환
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('date', inplace=True)
            
            # 숫자 형식 변환
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            # 중복 제거 및 정렬
            df = df.drop_duplicates(subset=['timestamp'])
            df = df.sort_index()
            
            # 날짜 필터링
            if self.start_date:
                df = df[df.index >= self.start_date]
            if self.end_date:
                df = df[df.index <= self.end_date]
            
            logger.info(f"✅ 데이터 다운로드 완료: {len(df)}개 캔들")
            logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
            logger.info(f"   가격 범위: ${df['low'].min():.2f} ~ ${df['high'].max():.2f}")
            
            # 데이터 저장 (선택적)
            data_dir = bitcoin_trading_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            data_file = data_dir / f"{self.symbol}_{interval}_historical.csv"
            df.to_csv(data_file)
            logger.info(f"💾 데이터 저장: {data_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 데이터 다운로드 실패: {e}")
            return pd.DataFrame()
    
    def load_historical_data(self, data_file: Optional[str] = None) -> pd.DataFrame:
        """
        과거 데이터 로드 (파일이 없으면 자동 다운로드)
        
        Args:
            data_file: 데이터 파일 경로 (None이면 기본 경로 사용)
        
        Returns:
            가격 데이터 DataFrame
        """
        if data_file is None:
            data_file = self.data_file
        
        if data_file is None:
            # 기본 데이터 파일 경로
            data_file = bitcoin_trading_root / "data" / "historical_btc_data.csv"
        
        data_path = Path(data_file)
        requested_months = 6
        if self.start_date and self.end_date and self.end_date > self.start_date:
            days = max(30, (self.end_date - self.start_date).days)
            requested_months = max(1, int(np.ceil(days / 30)))
        
        # 파일이 없으면 자동 다운로드 (요청 기간 기반)
        if not data_path.exists():
            logger.info(f"📥 데이터 파일이 없습니다. 자동 다운로드를 시작합니다...")
            return self.download_historical_data(months=requested_months, interval="1d")
        
        try:
            # CSV 파일 로드
            df = pd.read_csv(data_path)
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

            # 날짜 컬럼 변환
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            elif 'datetime' in df.columns:
                df['date'] = pd.to_datetime(df['datetime'])
            else:
                logger.error("❌ 날짜 컬럼을 찾을 수 없습니다. 자동 다운로드를 시도합니다...")
                return self.download_historical_data(months=requested_months, interval="1d")
            
            df.set_index('date', inplace=True)
            
            # 필수 컬럼 확인
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"❌ 필수 컬럼이 없습니다: {missing_columns}. 자동 다운로드를 시도합니다...")
                return self.download_historical_data(months=requested_months, interval="1d")
            
            # 날짜 필터링
            if self.start_date:
                df = df[df.index >= self.start_date]
            if self.end_date:
                df = df[df.index <= self.end_date]

            if self.start_date and self.end_date and not df.empty:
                requested_days = max(1, (self.end_date - self.start_date).days)
                covered_days = max(1, (df.index.max() - df.index.min()).days)
                if covered_days < int(requested_days * 0.9):
                    logger.warning(
                        f"⚠️ 로컬 CSV 기간 부족(요청 {requested_days}d / 보유 {covered_days}d), "
                        "요청 기간 기준으로 재다운로드합니다."
                    )
                    return self.download_historical_data(months=requested_months, interval="1d")
            
            logger.info(f"✅ 과거 데이터 로드 완료: {len(df)}개 캔들")
            logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 데이터 로드 실패: {e}. 자동 다운로드를 시도합니다...")
            return self.download_historical_data(months=requested_months, interval="1d")
    
    def run_backtest(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            historical_data: 과거 가격 데이터
        
        Returns:
            백테스트 결과
        """
        if len(historical_data) == 0:
            logger.error("❌ 과거 데이터가 없습니다.")
            return {}
        started_at = time.perf_counter()
        
        logger.info("=" * 80)
        logger.info("🏛️ Financial Sovereign Upgrade 블랙박스 백테스트 시작")
        logger.info("=" * 80)

        progress_step = 500 if self.quiet_logging else 100
        
        # 백테스트 루프 — 시점 t까지의 봉만 전략에 전달 (미래 봉 누설 방지)
        # fast 엔진은 iterrows 대신 인덱스/가격 배열 기반 순회로 파이썬 오버헤드를 줄인다.
        close_values = historical_data["close"].to_numpy(dtype=float)
        timestamps = historical_data.index.to_list()

        loop_guard = (
            _suppress_backtest_child_loggers(_QUIET_CHILD_LOG_LEVEL)
            if self.quiet_logging
            else nullcontext()
        )
        with loop_guard:
            for idx in range(len(historical_data)):
                timestamp = timestamps[idx]
                current_price = float(close_values[idx])
                current_time = timestamp if isinstance(timestamp, datetime) else pd.to_datetime(timestamp)

                if self.backtest_engine == "fast":
                    # 전략이 히스토리를 수정하지 않는다는 가정 하에 copy 비용을 제거.
                    self.strategy.price_data = historical_data.iloc[: idx + 1]
                else:
                    self.strategy.price_data = historical_data.iloc[: idx + 1].copy()

                # 🏛️ 블랙박스: 전략 클래스의 calculate_trading_signal 호출
                try:
                    signal_data = self.strategy.calculate_trading_signal(
                        current_price=current_price,
                        current_time=current_time
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 신호 생성 실패: {e}")
                    signal_data = {
                        "signal": "HOLD",
                        "confidence": 0.0,
                        "leverage_multiplier": 1.0
                    }

                signal = signal_data.get("signal", "HOLD")
                confidence = signal_data.get("confidence", 0.0)
                signal_id = signal_data.get("signal_id")

                # 신호 기록
                if self.record_signals:
                    self.signals.append({
                        "timestamp": current_time,
                        "signal": signal,
                        "confidence": confidence,
                        "price": current_price,
                        "signal_id": signal_id
                    })

                # 🏛️ Financial Sovereign Harness: 신호 검증 (거래 실행 전)
                if self.harness and signal_id and signal != "HOLD":
                    try:
                        expected_signal = {
                            "signal": signal,
                            "confidence": confidence,
                            "price": current_price
                        }

                        verified_signal = self.harness.verify_signal(
                            signal_id=signal_id,
                            expected_signal=expected_signal
                        )

                        if not verified_signal.is_valid:
                            logger.warning(
                                f"⚠️ 헌법 제3조 위반: 신호 검증 실패 (Signal ID: {signal_id})"
                            )
                            logger.warning(f"   오류: {verified_signal.error_message}")
                            logger.warning("   거래 실행 중단 (100% Literal Restoration 보장)")
                            signal = "HOLD"  # 검증 실패 시 거래 중단
                    except Exception as e:
                        logger.warning(f"⚠️ 신호 검증 실패: {e}, 거래 계속 진행 (Fallback)")

                # 거래 실행
                if signal != "HOLD" and confidence >= self.strategy.min_confidence:
                    self._execute_trade(
                        signal=signal,
                        price=current_price,
                        confidence=confidence,
                        timestamp=current_time,
                        signal_data=signal_data
                    )

                # 자산 업데이트
                self._update_equity(current_price)

                # 🛡️ 리스크 관리: TP/SL 조건 만족 시 포지션 청산
                # (calibration_mode에서도 스윕 안정화를 위해 활성화)
                try:
                    stop_loss_ratio = float(getattr(self.strategy, "stop_loss_ratio", 0.02) or 0.02)
                    take_profit_ratio = float(getattr(self.strategy, "take_profit_ratio", 0.04) or 0.04)

                    if self.position_side == "LONG" and self.entry_price > 0:
                        move_ratio = (current_price - self.entry_price) / self.entry_price
                        if move_ratio <= -stop_loss_ratio or move_ratio >= take_profit_ratio:
                            self._close_position(price=current_price, timestamp=current_time)

                    elif self.position_side == "SHORT" and self.entry_price > 0:
                        move_ratio = (self.entry_price - current_price) / self.entry_price
                        if move_ratio <= -stop_loss_ratio or move_ratio >= take_profit_ratio:
                            self._close_position(price=current_price, timestamp=current_time)
                except Exception as e:
                    logger.debug(f"TP/SL close check failed(무시): {e}")

                # 진행 상황 로깅 (quiet 모드에서는 간격 확대)
                if (idx + 1) % progress_step == 0:
                    progress = (idx + 1) / len(historical_data) * 100
                    logger.info(
                        f"📊 진행 상황: {progress:.1f}% "
                        f"(자산: ${self.capital + self.position_value:,.2f}, "
                        f"거래: {self.total_trades}회)"
                    )

            # 백테스트 종료 시점에 미청산 포지션을 청산해 승패/수수료가 누락되지 않게 함
            if self.position != 0 and self.position_side in ("LONG", "SHORT"):
                last_row = historical_data.iloc[-1]
                last_price = float(last_row["close"])
                last_ts = historical_data.index[-1]
                last_time = last_ts if isinstance(last_ts, datetime) else pd.to_datetime(last_ts)
                self._close_position(price=last_price, timestamp=last_time)

        # 최종 결과 계산
        final_capital = self.capital + self.position_value
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        result = {
            "engine": self.backtest_engine,
            "quiet_logging": self.quiet_logging,
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0,
            "max_drawdown": self.max_drawdown,
            "total_pnl": self.total_pnl,
            "signals_count": len(self.signals),
            "trades": self.trades[-100:] if len(self.trades) > 100 else self.trades  # 최근 100개만
        }
        
        logger.info("=" * 80)
        logger.info("🏛️ 백테스트 완료")
        logger.info("=" * 80)
        logger.info(f"초기 자본: ${self.initial_capital:,.2f}")
        logger.info(f"최종 자산: ${final_capital:,.2f}")
        logger.info(f"총 수익률: {total_return:.2%}")
        logger.info(f"총 거래 횟수: {self.total_trades}회")
        logger.info(f"승률: {result['win_rate']:.2%}")
        logger.info(f"최대 낙폭: {self.max_drawdown:.2%}")
        
        return result

    def get_signals_dataframe(self) -> pd.DataFrame:
        """
        백테스트 실행 후 기록된 신호를 DataFrame으로 반환 (VectorBT 등 외부 백테스트용).
        index=timestamp, columns=['close','signal'].
        """
        if not self.signals:
            return pd.DataFrame(columns=["close", "signal"])
        timestamps = [s["timestamp"] for s in self.signals]
        if hasattr(timestamps[0], "tzinfo") and timestamps[0].tzinfo is None:
            timestamps = [pd.Timestamp(t) for t in timestamps]
        return pd.DataFrame(
            {
                "close": [s["price"] for s in self.signals],
                "signal": [s["signal"] for s in self.signals],
            },
            index=pd.DatetimeIndex(timestamps),
        )

    def _execute_trade(
        self,
        signal: str,
        price: float,
        confidence: float,
        timestamp: datetime,
        signal_data: Dict[str, Any]
    ):
        """
        거래 실행 (백테스트)
        
        Args:
            signal: 매매 신호 (BUY, SELL)
            price: 현재 가격
            confidence: 신뢰도
            timestamp: 타임스탬프
            signal_data: 신호 데이터
        """
        # 포지션 크기: 전략 max_position_size × BTC-6 레짐 multiplier
        leverage_mult = float(signal_data.get("leverage_multiplier", 1.0))
        min_mul = float(getattr(self.strategy, "risk_multiplier_min", 0.5) or 0.5)
        max_mul = float(getattr(self.strategy, "risk_multiplier_max", 1.2) or 1.2)
        leverage_mult = max(min_mul, min(max_mul, leverage_mult))
        base_position_size = float(getattr(self.strategy, "max_position_size", 0.3) or 0.3)
        position_size_usdt = self.capital * base_position_size * leverage_mult
        position_size_btc = position_size_usdt / price
        
        # 수수료 계산
        commission = position_size_usdt * self.commission_rate
        
        if signal == "BUY" and self.position_side != "LONG":
            # 롱 포지션 오픈
            if self.position_side == "SHORT":
                # 기존 숏 포지션 청산
                self._close_position(price, timestamp)
            
            # 롱 포지션 오픈
            self.position = position_size_btc
            self.position_value = position_size_usdt
            self.entry_price = price
            self.position_side = "LONG"
            self.capital -= (position_size_usdt + commission)
            
            self.trades.append({
                "timestamp": timestamp,
                "action": "OPEN_LONG",
                "price": price,
                "size": position_size_btc,
                "value": position_size_usdt,
                "commission": commission,
                "confidence": confidence,
                "signal_id": signal_data.get("signal_id")
            })
            self.total_trades += 1
            
        elif signal == "SELL" and self.position_side != "SHORT":
            # 숏 포지션 오픈
            if self.position_side == "LONG":
                # 기존 롱 포지션 청산
                self._close_position(price, timestamp)
            
            # 숏 포지션 오픈
            self.position = position_size_btc
            self.position_value = position_size_usdt
            self.entry_price = price
            self.position_side = "SHORT"
            self.capital -= (position_size_usdt + commission)
            
            self.trades.append({
                "timestamp": timestamp,
                "action": "OPEN_SHORT",
                "price": price,
                "size": position_size_btc,
                "value": position_size_usdt,
                "commission": commission,
                "confidence": confidence,
                "signal_id": signal_data.get("signal_id")
            })
            self.total_trades += 1
    
    def _close_position(self, price: float, timestamp: datetime):
        """
        포지션 청산
        
        Args:
            price: 청산 가격
            timestamp: 타임스탬프
        """
        if self.position == 0:
            return
        
        # 손익 계산
        if self.position_side == "LONG":
            pnl = (price - self.entry_price) * self.position * self.leverage
        else:  # SHORT
            pnl = (self.entry_price - price) * self.position * self.leverage
        
        # 수수료/자본 업데이트 스케일 보정
        # position_value은 _update_equity에서 레버리지 기반 마크투마켓으로 덮어써질 수 있어
        # 잦은 청산(TP/SL)에서 회계 스케일이 폭주할 수 있음.
        # 여기서는 청산 시점의 레버리지 포지션가가 아니라, 포지션 진입 명목가를 기준으로 계산한다.
        position_notional_usdt = float(self.position * self.entry_price)
        commission = position_notional_usdt * self.commission_rate

        # 순 손익
        net_pnl = pnl - commission

        # 자본 업데이트: 마진(명목가) + 손익(순)
        self.capital += position_notional_usdt + net_pnl
        self.total_pnl += net_pnl
        
        # 거래 기록
        self.trades.append({
            "timestamp": timestamp,
            "action": f"CLOSE_{self.position_side}",
            "price": price,
            "entry_price": self.entry_price,
            "size": self.position,
            "pnl": pnl,
            "net_pnl": net_pnl,
            "commission": commission
        })
        
        # 승패 기록
        if net_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 포지션 초기화
        self.position = 0.0
        self.position_value = 0.0
        self.entry_price = 0.0
        self.position_side = None
    
    def _update_equity(self, current_price: float):
        """
        자산 업데이트 (낙폭 계산 포함)
        
        Args:
            current_price: 현재 가격
        """
        # 포지션 가치 계산
        if self.position > 0:
            if self.position_side == "LONG":
                self.position_value = self.position * current_price * self.leverage
            else:  # SHORT
                self.position_value = self.position * (2 * self.entry_price - current_price) * self.leverage
        
        # 총 자산
        total_equity = self.capital + self.position_value
        
        # 자산 곡선 기록
        if self.record_equity_curve:
            self.equity_curve.append(total_equity)
        
        # 최대 자산 업데이트
        if total_equity > self.peak_capital:
            self.peak_capital = total_equity
        
        # 최대 낙폭 계산
        if self.peak_capital > 0:
            drawdown = (self.peak_capital - total_equity) / self.peak_capital
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
    
    def save_results(self, output_file: Optional[str] = None):
        """
        백테스트 결과 저장
        
        Args:
            output_file: 출력 파일 경로
        """
        if output_file is None:
            output_file = bitcoin_trading_root / "data" / "backtest_results.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = {
            "backtest_date": datetime.now().isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.capital + self.position_value,
            "total_return": (self.capital + self.position_value - self.initial_capital) / self.initial_capital,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0,
            "max_drawdown": self.max_drawdown,
            "total_pnl": self.total_pnl,
            "signals_count": len(self.signals),
            "trades": self.trades[-100:] if len(self.trades) > 100 else self.trades
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✅ 백테스트 결과 저장 완료: {output_path}")


CLI_SCHEMA_VERSION = "financial_sovereign_backtest_cli_v2"
_CLI_LOG_LEVEL_NAMES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def build_financial_sovereign_cli_parser(default_out: Path) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Financial Sovereign 블랙박스 백테스트 CLI",
        epilog=(
            "환경변수 MKM_BACKTEST_QUIET=1|true|yes|on 으로 조용 로그를 강제할 수 있습니다. "
            "프로세스 내 첫 번째 FinancialSovereignBacktester 생성 시점의 조용 설정이 전략 모듈 최초 import 톤을 고정합니다."
        ),
    )
    ap.add_argument(
        "--data-file",
        type=Path,
        default=None,
        help="OHLCV CSV 경로 (미지정 시 백테스터 기본 경로·없으면 다운로드)",
    )
    ap.add_argument("--days", type=int, default=180, help="종료 시점 기준 과거 일수 (기본 180)")
    ap.add_argument("--quiet", action="store_true", help="조용 로그 모드 강제")
    ap.add_argument("--verbose", action="store_true", help="조용 로그 비활성화 강제")
    ap.add_argument(
        "--calibration",
        action="store_true",
        help="캘리브레이션 경량 모드 (Harness 생략, 전략 backtest_calibration)",
    )
    ap.add_argument(
        "--no-record-signals",
        dest="record_signals",
        action="store_false",
        default=True,
        help="신호 이력 미적재 (속도·메모리)",
    )
    ap.add_argument(
        "--no-record-equity",
        dest="record_equity_curve",
        action="store_false",
        default=True,
        help="에쿼티 커브 미적재",
    )
    ap.add_argument("--output", "-o", type=Path, default=None, help=f"결과 JSON (기본 {default_out})")
    ap.add_argument(
        "--log-level",
        default="INFO",
        choices=_CLI_LOG_LEVEL_NAMES,
        metavar="LEVEL",
        help="루트 로깅 레벨 (기본 INFO)",
    )
    return ap


def run_financial_sovereign_cli_main(argv: Optional[list[str]] = None) -> int:
    """CLI 스크립트·모듈 직행(`python -m`/`__main__`) 공통 진입점. exit 코드만 반환."""
    default_out = bitcoin_trading_root / "data" / "backtest_cli_results.json"
    args = build_financial_sovereign_cli_parser(default_out).parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    if args.quiet and args.verbose:
        logger.error("--quiet 과 --verbose 는 함께 쓸 수 없습니다.")
        return 2

    end_date = datetime.now()
    start_date = end_date - timedelta(days=max(1, args.days))

    quiet_opt: Optional[bool]
    if args.quiet:
        quiet_opt = True
    elif args.verbose:
        quiet_opt = False
    else:
        quiet_opt = None

    data_path_str = str(args.data_file.resolve()) if args.data_file else None

    backtester = FinancialSovereignBacktester(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2,
        commission_rate=0.001,
        start_date=start_date,
        end_date=end_date,
        data_file=data_path_str,
        calibration_mode=args.calibration,
        backtest_engine="fast",
        record_signals=args.record_signals,
        record_equity_curve=args.record_equity_curve,
        quiet_logging=quiet_opt,
    )

    logger.info("📥 과거 데이터 로드 중...")
    historical_data = backtester.load_historical_data(data_file=data_path_str)

    if len(historical_data) == 0:
        logger.error("과거 데이터가 없습니다.")
        return 1

    logger.info("백테스트 시작 (%s 캔들)", len(historical_data))
    results = backtester.run_backtest(historical_data)

    out_path = Path(args.output) if args.output else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "schema": CLI_SCHEMA_VERSION,
        "backtest_date": datetime.now().isoformat(),
        "log_level": args.log_level,
        "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "days": args.days},
        "data_file": data_path_str,
        **results,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    logger.info("✅ 결과 저장: %s", out_path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(run_financial_sovereign_cli_main())

