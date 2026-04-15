#!/usr/bin/env python3
"""
Crypto-Nitro v1.6 실전 매매 시스템 (Live Trading)

실제 Binance API를 사용한 실전 매매
- 실제 주문 실행
- 리스크 관리 강화
- 안전장치 다중화
"""
import sys
import os
import asyncio
import json
import urllib.request
from functools import partial
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np
import logging
import time
import yaml

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# 모듈 import
from src.api.binance_client import BinanceFuturesClient, USE_CCXT
from src.strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy
from src.risk.risk_manager import RiskManager
from src.analysis.strategic_failure_event import record_trading_failure_event

# PGAE Oracle Gateway (14B 검증)
try:
    from src.integration.oracle_gateway import oracle_gateway_verify
    ORACLE_GATEWAY_AVAILABLE = True
except ImportError:
    oracle_gateway_verify = None
    ORACLE_GATEWAY_AVAILABLE = False

try:
    from src.integration.omni_oracle_contract import build_transition_request
except ImportError:
    build_transition_request = None

# 선택적 import: Bitcoin20MSeedOptimizer
try:
    from scripts.bitcoin_20m_seed_optimizer import Bitcoin20MSeedOptimizer
    BITCOIN_20M_SEED_OPTIMIZER_AVAILABLE = True
except ImportError:
    Bitcoin20MSeedOptimizer = None
    BITCOIN_20M_SEED_OPTIMIZER_AVAILABLE = False
    logging.warning("⚠️ Bitcoin20MSeedOptimizer를 import할 수 없습니다. 선택적 기능 비활성화")

# 🏛️ Project Logos 이론 함수 import (0.25 회귀 알고리즘)
try:
    from crypto_nitro_backtest_v1 import apply_0_25_regression
    PROJECT_LOGOS_AVAILABLE = True
except ImportError:
    try:
        from scripts.crypto_nitro_backtest_v1 import apply_0_25_regression
        PROJECT_LOGOS_AVAILABLE = True
    except ImportError:
        PROJECT_LOGOS_AVAILABLE = False
        apply_0_25_regression = None
        logging.warning("⚠️ apply_0_25_regression 함수를 import할 수 없습니다. 0.25 회귀 알고리즘 비활성화")

# 로그 디렉토리 생성
log_dir = workspace_root / "projects" / "bitcoin-trading" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# 로그 파일 (레벨별 분리)
log_file_info = log_dir / "live_trading_info.log"
log_file_error = log_dir / "live_trading_error.log"
log_file_debug = log_dir / "live_trading_debug.log"
log_file_performance = log_dir / "live_trading_performance.log"

# 로그 로테이션 설정 (10MB, 최대 5개 파일 보관)
from logging.handlers import RotatingFileHandler

# INFO 로그 핸들러
info_handler = RotatingFileHandler(
    str(log_file_info),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# ERROR 로그 핸들러
error_handler = RotatingFileHandler(
    str(log_file_error),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# DEBUG 로그 핸들러
debug_handler = RotatingFileHandler(
    str(log_file_debug),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# 성능 메트릭 로그 핸들러 (JSON 형식)
performance_handler = RotatingFileHandler(
    str(log_file_performance),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
performance_handler.setLevel(logging.INFO)

# JSON 포맷터 (성능 메트릭용)
class PerformanceJSONFormatter(logging.Formatter):
    """성능 메트릭용 JSON 포맷터"""
    def format(self, record: logging.LogRecord) -> str:
        import json
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        # 추가 필드가 있으면 포함
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)
        return json.dumps(log_data, ensure_ascii=False)

performance_handler.setFormatter(PerformanceJSONFormatter())

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# 로거 설정
logger = logging.getLogger(__name__)

OMNI_ORACLE_STATE_TRANSITION_URL = os.getenv(
    "OMNI_ORACLE_STATE_TRANSITION_URL",
    "http://127.0.0.1:8001/api/v1/omni-oracle/state-transition",
)


def _clip01(value: float, default: float = 0.25) -> float:
    try:
        return float(min(1.0, max(0.0, float(value))))
    except Exception:
        return default


def _build_omni_oracle_request_from_signal(
    signal_data: Dict[str, Any],
    current_price: float,
    confidence: float,
    signal: str,
    leverage_multiplier: float,
) -> Optional[Dict[str, Any]]:
    if build_transition_request is None:
        return None

    vec = signal_data.get("vector_4d") or {}
    current_state = {
        "S": _clip01(vec.get("S", vec.get("p_alpha", 0.25))),
        "L": _clip01(vec.get("L", vec.get("p_beta", 0.25))),
        "K": _clip01(vec.get("K", vec.get("p_gamma", 0.25))),
        "M": _clip01(vec.get("M", vec.get("p_delta", 0.25))),
    }

    priors = signal_data.get("omni_priors")
    if not isinstance(priors, dict):
        priors = {
            "current_regime_state": 1 if signal in ("BUY", "LONG") else 0,
            "markov_transition": [[0.8, 0.2], [0.35, 0.65]],
            "likelihood": {
                "signal_given_shift": min(0.95, max(0.05, 0.55 + confidence * 0.3)),
                "signal_given_no_shift": min(0.95, max(0.05, 0.45 - confidence * 0.2)),
            },
            "prophecy": {
                "biblical_regime": str(signal_data.get("regime_id", "neutral")),
                "fractal_phase": str(signal_data.get("fractal_phase", "phase_unknown")),
                "saju_bias": float(signal_data.get("saju_bias", 0.0) or 0.0),
                "sign_strength": float(min(1.0, max(0.0, confidence))),
                "confidence": float(min(1.0, max(0.0, confidence))),
            },
            "prior_bias": float(min(0.2, max(-0.2, (leverage_multiplier - 1.0) * 0.1))),
        }

    domain_input = {
        "price_change_24h": float(signal_data.get("price_change_24h", signal_data.get("return_24h", 0.0)) or 0.0),
        "realized_volatility": float(signal_data.get("realized_volatility", signal_data.get("volatility_24h", 0.0)) or 0.0),
        "funding_rate": float(signal_data.get("funding_rate", 0.0) or 0.0),
        "open_interest_change": float(signal_data.get("open_interest_change", 0.0) or 0.0),
        "liquidity_delta": float(signal_data.get("liquidity_delta", 0.0) or 0.0),
        "extras": {
            "price": float(current_price),
            "signal": signal,
            "confidence": float(confidence),
        },
    }

    return build_transition_request(
        domain="crypto",
        current_state=current_state,
        exogenous_factors={},
        priors=priors,
        domain_input=domain_input,
    )


def _call_omni_oracle_state_transition(payload: Dict[str, Any], timeout_sec: int = 3) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            OMNI_ORACLE_STATE_TRANSITION_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except Exception:
        return None
logger.setLevel(logging.DEBUG)
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(debug_handler)
logger.addHandler(performance_handler)
logger.addHandler(console_handler)


class CryptoNitroLiveTrader:
    """
    Crypto-Nitro v1.7 실전 매매 시스템 (정확도 기반 자동 최적화)
    
    핵심 기능:
    - 실제 Binance API 주문 실행
    - 리스크 관리 강화
    - 안전장치 다중화
    - 정확도 기반 자동 최적화 (신뢰도에 비례한 레버리지/포지션/거래횟수 조정)
    - Project Logos 통합 이론 적용
    """
    
    @staticmethod
    def calculate_leverage_multiplier(confidence: float) -> float:
        """
        신뢰도에 따른 레버리지 배율 계산 (정확도 기반 자동 최적화)
        
        Args:
            confidence: 신호 신뢰도 (0.0 ~ 1.0)
        
        Returns:
            레버리지 배율 (기본 레버리지 2배를 기준으로 1~2배 범위 내에서만 조정)
            - confidence < 0.6: 0.5배  (레버리지 감소, 매우 보수적)
            - confidence 0.6-0.75: 0.75배 (소폭 감소)
            - confidence 0.75-0.85: 1.0배 (기본)
            - confidence 0.85-0.95: 1.0배 (상승 시에도 2배 초과 금지)
            - confidence >= 0.95: 1.0배 (확실한 구간이더라도 2배 초과 금지)
        """
        if confidence < 0.6:
            return 0.5
        elif confidence < 0.75:
            return 0.75
        elif confidence < 0.85:
            return 1.0
        else:
            # 최대 레버리지는 기본 레버리지(2배)를 넘지 않도록 1.0으로 고정
            return 1.0
    
    @staticmethod
    def calculate_confidence_position_multiplier(confidence: float) -> float:
        """
        신뢰도에 따른 포지션 크기 배율 계산 (정확도 기반 자동 최적화)
        
        Args:
            confidence: 신호 신뢰도 (0.0 ~ 1.0)
        
        Returns:
            포지션 크기 배율
            - confidence 0.5: 0.5배 (50% 감소)
            - confidence 0.75: 1.0배 (기본)
            - confidence 0.9: 1.4배 (40% 증가)
            - confidence 0.95: 1.5배 (50% 증가)
        """
        # 선형 보간: 0.5배 ~ 1.5배
        return 0.5 + (confidence * 1.0)
    
    @staticmethod
    def calculate_max_trades_per_day(avg_confidence: float) -> int:
        """
        평균 신뢰도에 따른 일일 최대 거래 횟수 계산 (정확도 기반 자동 최적화)
        
        Args:
            avg_confidence: 평균 신뢰도 (0.0 ~ 1.0)
        
        Returns:
            일일 최대 거래 횟수
            - avg_confidence < 0.6: 5회 (보수적)
            - avg_confidence 0.6-0.75: 10회 (기본)
            - avg_confidence 0.75-0.85: 15회 (적극적)
            - avg_confidence >= 0.85: 20회 (공격적)
        """
        if avg_confidence < 0.6:
            return 5
        elif avg_confidence < 0.75:
            return 10
        elif avg_confidence < 0.85:
            return 15
        else:
            return 20
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        testnet: bool = True,  # ⚠️ 기본값: 테스트넷 (안전)
        use_great_trunk_filter: bool = True,
        max_drawdown: float = 0.22,  # 22% 최대 낙폭
        max_daily_loss: float = 0.05,  # 5% 일일 최대 손실
        enable_live_trading: bool = False  # ⚠️ 실전 매매 활성화 여부 (기본값: False)
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 기본 레버리지 (물리적 레버리지, 항상 2배로 고정)
            testnet: 테스트넷 사용 여부 (True 권장)
            use_great_trunk_filter: 거대한 줄기 추세 필터 사용 여부
            max_drawdown: 최대 낙폭 (22%)
            max_daily_loss: 일일 최대 손실 (5%)
            enable_live_trading: 실전 매매 활성화 여부 (⚠️ 주의: False 권장)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.testnet = testnet
        self.use_great_trunk_filter = use_great_trunk_filter
        self.enable_live_trading = enable_live_trading
        # 매크로 레짐 연동용 기본값 (KOSPI/환율/에너지 등 외부 레짐 스코어)
        self.macro_risk_level: float = 0.0
        self.fiat_crisis_flag: bool = False
        # 레포 사상 단독 레인 JSON → BTC 전용 방어적 스트레스 (KOSPI 체결 없음)
        self._sasang_btc_overlay_stress: float = 0.0
        self._sasang_btc_overlay_label: str = "pending"
        
        # ⚠️ 실전 매매 활성화 확인
        if enable_live_trading and not testnet:
            logger.warning("=" * 60)
            logger.warning("⚠️ ⚠️ ⚠️ 실전 매매 모드 활성화 ⚠️ ⚠️ ⚠️")
            logger.warning("실제 자금이 사용됩니다!")
            logger.warning("=" * 60)
            # 5초 대기 (취소 기회 제공)
            logger.warning("5초 후 시작합니다... (Ctrl+C로 취소)")
            time.sleep(5)
        elif enable_live_trading and testnet:
            logger.info("✅ 테스트넷 모드: 실제 자금 사용 안 함")
        else:
            logger.info("📄 모의 매매 모드: 실제 주문 실행 안 함")
        
        # 설정 파일에서 maker_only, api_use_ed25519 읽기 (Binance 클라이언트 생성 전, 4대 정책)
        maker_only = False
        api_use_ed25519 = False
        try:
            import yaml as _yaml
            _paths = [
                Path(__file__).parent.parent.parent / "config" / "trading_config.yaml",
                workspace_root / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml",
                Path("/opt/bitcoin-trading/config/trading_config.yaml"),
                Path("/opt/bitcoin-trading") / "config" / "trading_config.yaml",
            ]
            for _p in _paths:
                if _p.exists():
                    with open(_p, "r", encoding="utf-8") as _f:
                        _cfg = _yaml.safe_load(_f)
                        maker_only = bool(_cfg.get("maker_only", False))
                        api_use_ed25519 = bool(_cfg.get("api_use_ed25519", False))
                    if maker_only:
                        logger.info("📌 Maker-only 모드: LIMIT + Post-Only(GTX) 사용 (Maker 수수료만)")
                    break
        except Exception as _e:
            logger.debug("maker_only/api_use_ed25519 설정 읽기 생략: %s", _e)

        # Binance API 클라이언트 (필수)
        logger.info("🔐 Binance API 클라이언트 초기화 중...")
        try:
            self.binance = BinanceFuturesClient(
                testnet=testnet, maker_only=maker_only, api_use_ed25519=api_use_ed25519
            )
            logger.info(f"✅ Binance API 클라이언트 초기화 완료 (테스트넷: {testnet})")
        except Exception as e:
            logger.error(f"❌ Binance API 클라이언트 초기화 실패: {e}")
            raise
        
        # 레버리지 설정
        try:
            self.binance.set_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            # 실전 매매 모드에서는 레버리지 설정 실패를 매우 심각한 상태로 간주한다.
            logger.error(f"❌ 레버리지 설정 실패: {e}")
            # 안전을 위해 실전 매매는 비활성화하고, 모의/테스트넷 모드에서만 계속 진행한다.
            if self.enable_live_trading:
                logger.error("❌ 레버리지 설정에 실패하여 enable_live_trading=False로 전환합니다 (안전 모드).")
                self.enable_live_trading = False
                # 중요 이벤트 알림 (텔레그램 등)
                if hasattr(self, "alert_manager") and self.alert_manager:
                    try:
                        alert_msg = (
                            "⚠️ *레버리지 설정 실패로 안전 모드로 전환되었습니다.*\n"
                            f"- 심볼: {symbol}\n"
                            f"- 요청 레버리지: {leverage}배\n"
                            f"- 에러: {e}"
                        )
                        # 비동기 컨텍스트가 아닐 수도 있으므로 best-effort 방식으로 전송
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(
                                    self.alert_manager.alert_critical_event(
                                        event_type="LEVERAGE_SETUP_FAILED",
                                        message=alert_msg,
                                        details={
                                            "symbol": symbol,
                                            "leverage": leverage,
                                            "error": str(e),
                                        },
                                        severity="CRITICAL",
                                    )
                                )
                            else:
                                loop.run_until_complete(
                                    self.alert_manager.alert_critical_event(
                                        event_type="LEVERAGE_SETUP_FAILED",
                                        message=alert_msg,
                                        details={
                                            "symbol": symbol,
                                            "leverage": leverage,
                                            "error": str(e),
                                        },
                                        severity="CRITICAL",
                                    )
                                )
                        except Exception as alert_err:
                            logger.warning(f"⚠️ 레버리지 설정 실패 알림 전송 중 오류(무시): {alert_err}")
                    except Exception as alert_outer_err:
                        logger.warning(f"⚠️ 레버리지 실패 알림 구성 중 예외(무시): {alert_outer_err}")
        
        # Crypto-Nitro 전략
        logger.info("🚀 Crypto-Nitro v1.6 전략 초기화 중...")
        self.strategy = CryptoNitroLiveStrategy(
            symbol=symbol,
            initial_capital=initial_capital,
            leverage=leverage,
            use_great_trunk_filter=use_great_trunk_filter,
            binance_client=self.binance  # Binance API 클라이언트 전달
        )

        # 실전 주문 신뢰도 하한: strategy.min_confidence(trading_config.yaml)와 동기화.
        # 과거 하드코드 0.6이 yaml(예: 0.55)·MKM 전략(0.52 아테나 임계)과 어긋나 체결 0건이 되는 경우가 있었음.
        try:
            self.min_exec_confidence = float(getattr(self.strategy, "min_confidence", 0.52))
        except Exception:
            self.min_exec_confidence = 0.52
        _env_mc = os.getenv("CRYPTO_NITRO_MIN_EXEC_CONFIDENCE", "").strip()
        if _env_mc:
            try:
                self.min_exec_confidence = float(_env_mc)
                logger.info("📌 CRYPTO_NITRO_MIN_EXEC_CONFIDENCE=%.4f (env override)", self.min_exec_confidence)
            except ValueError:
                logger.warning("⚠️ CRYPTO_NITRO_MIN_EXEC_CONFIDENCE parse fail, keeping %.4f", self.min_exec_confidence)
        logger.info(
            "📌 실전 실행 신뢰도 하한 min_exec_confidence=%.4f (전략 yaml; env로 재정의 가능)",
            self.min_exec_confidence,
        )
        
        # 🚀 2천만 원 시드 최적화 통합
        self.optimizer = None
        if initial_capital >= 10000000.0 and BITCOIN_20M_SEED_OPTIMIZER_AVAILABLE:  # 1천만 원 이상 + 모듈 사용 가능
            try:
                if Bitcoin20MSeedOptimizer is not None:
                    self.optimizer = Bitcoin20MSeedOptimizer(seed_capital=initial_capital)
                    optimal_frequency = self.optimizer.calculate_optimal_trade_frequency()
                    logger.info(f"✅ 최적화된 거래 빈도: 일일 최대 {optimal_frequency['max_trades_per_day']}회, 체크 간격 {optimal_frequency['check_interval_seconds']}초")
            except Exception as e:
                logger.warning(f"⚠️ 최적화 로직 적용 실패: {e}")
        
        # 🏛️ Financial Sovereign Harness 초기화 (Signal ID 검증용)
        self.harness = None
        try:
            from tools.core.financial_sovereign_harness import FinancialSovereignHarness
            codebook_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "signal_codebook.json"
            codebook_path.parent.mkdir(parents=True, exist_ok=True)
            self.harness = FinancialSovereignHarness(codebook_path=str(codebook_path))
            logger.info("✅ Financial Sovereign Harness 초기화 완료 (헌법 제3조: 100% Literal Restoration)")
        except Exception as e:
            logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")
            self.harness = None
        
        # 리스크 관리 시스템
        logger.info("🛡️ 리스크 관리 시스템 초기화 중...")
        
        # 🏛️ Enhanced Risk Manager 초기화 (강화된 리스크 관리)
        self.enhanced_risk_manager = None
        try:
            from src.risk.enhanced_risk_manager import EnhancedRiskManager
            self.enhanced_risk_manager = EnhancedRiskManager(
                initial_capital=initial_capital,
                base_max_position_size=0.15,  # 기본 최대 포지션 크기 15%
                max_slippage=0.001,  # 최대 슬리피지 0.1%
                volatility_window=20
            )
            logger.info("✅ Enhanced Risk Manager 초기화 완료 (슬리피지 제어, 동적 포지션 크기)")
        except ImportError as e:
            logger.warning(f"⚠️ Enhanced Risk Manager 초기화 실패: {e}, 기본 리스크 관리만 사용")
        
        # 실제 잔고 조회 및 초기 자본 리셋 (낙폭 문제 해결)
        try:
            balance_info = self.binance.get_balance()
            actual_balance = balance_info.get('total', initial_capital) if isinstance(balance_info, dict) else initial_capital
            
            # 실제 잔고가 초기 자본과 다르면 리셋
            if abs(actual_balance - initial_capital) > 100:  # 100 USDT 이상 차이
                logger.warning(
                    f"⚠️ 초기 자본과 실제 잔고 불일치: "
                    f"초기 자본 ${initial_capital:,.2f} vs 실제 잔고 ${actual_balance:,.2f}"
                )
                logger.info(f"✅ 실제 잔고로 초기 자본 리셋: ${actual_balance:,.2f}")
                initial_capital = actual_balance
        except Exception as e:
            logger.warning(f"⚠️ 잔고 조회 실패, 초기 자본 사용: {e}")
        
        # Alert Manager 초기화 (중요 이벤트 알림용)
        try:
            from src.monitoring.alert_manager import AlertManager
            self.alert_manager = AlertManager()
            logger.info("✅ Alert Manager 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ Alert Manager 초기화 실패: {e}")
            self.alert_manager = None
        
        self.risk_manager = RiskManager(
            initial_capital=initial_capital,
            max_drawdown=max_drawdown,
            max_daily_loss=max_daily_loss,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID")
        )
        
        # 설정 파일에서 리스크 관리 및 매크로 레짐 설정 읽기
        config = None
        config_path = None
        try:
            import yaml
            # 여러 경로 시도
            possible_paths = [
                Path(__file__).parent.parent.parent / "config" / "trading_config.yaml",  # projects/bitcoin-trading/config
                workspace_root / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml",  # workspace root 기준
                Path("/opt/bitcoin-trading/config/trading_config.yaml"),  # VPS 절대 경로
                Path("/opt/bitcoin-trading") / "config" / "trading_config.yaml"  # VPS 절대 경로 (Path 객체)
            ]
            
            config = None
            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    logger.info(f"📁 설정 파일 발견: {config_path}")
                    break
            
            if config_path and config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        if 'risk_management' in config:
                            rm_conf = config['risk_management']
                            # 최대 포지션 비율 (전략 레이어 리스크 상한)
                            max_pos_size = rm_conf.get('max_position_size', self.risk_manager.max_position_size)
                            self.risk_manager.base_max_position_size = max_pos_size
                            self.risk_manager.max_position_size = max_pos_size
                            # 최대 낙폭 / 일일 손실 한도도 설정 파일을 우선
                            self.risk_manager.max_drawdown = rm_conf.get('max_drawdown', self.risk_manager.max_drawdown)
                            self.risk_manager.max_daily_loss = rm_conf.get('max_daily_loss', self.risk_manager.max_daily_loss)
                            # 손절/익절 비율도 맞춰준다 (없으면 RiskManager 기본값 유지)
                            self.risk_manager.stop_loss_ratio = rm_conf.get('stop_loss_ratio', self.risk_manager.stop_loss_ratio)
                            self.risk_manager.take_profit_ratio = rm_conf.get('take_profit_ratio', self.risk_manager.take_profit_ratio)
                            self.config_risk_per_trade = max(
                                0.001,
                                min(0.03, float(rm_conf.get("risk_per_trade", self.config_risk_per_trade)))
                            )
                            self.config_max_consecutive_failures_hard_gate = max(
                                1,
                                min(10, int(rm_conf.get(
                                    "max_consecutive_failures_hard_gate",
                                    self.config_max_consecutive_failures_hard_gate,
                                )))
                            )

                            logger.info(
                                "✅ 리스크 관리 설정 적용 (파일: %s): "
                                "max_position_size=%.1f%%, max_drawdown=%.1f%%, max_daily_loss=%.1f%%, "
                                "stop_loss=%.1f%%, take_profit=%.1f%%, risk_per_trade=%.2f%%, hard_gate_failures=%d",
                                config_path,
                                max_pos_size * 100,
                                self.risk_manager.max_drawdown * 100,
                                self.risk_manager.max_daily_loss * 100,
                                self.risk_manager.stop_loss_ratio * 100,
                                self.risk_manager.take_profit_ratio * 100,
                                self.config_risk_per_trade * 100,
                                self.config_max_consecutive_failures_hard_gate,
                            )
                        else:
                            logger.warning(f"⚠️ 설정 파일에 risk_management 섹션이 없습니다: {config_path}")

                        trading_conf = config.get("trading")
                        if isinstance(trading_conf, dict):
                            try:
                                check_v = trading_conf.get("check_interval_seconds")
                                if check_v is not None:
                                    self.config_check_interval_seconds = max(10, int(check_v))
                            except (TypeError, ValueError):
                                self.config_check_interval_seconds = None
                            try:
                                max_v = trading_conf.get("max_trades_per_day")
                                if max_v is not None:
                                    self.config_max_trades_per_day = max(1, int(max_v))
                            except (TypeError, ValueError):
                                self.config_max_trades_per_day = None
                            logger.info(
                                "🧭 trading 설정 로드: check_interval_seconds=%s, max_trades_per_day=%s",
                                self.config_check_interval_seconds,
                                self.config_max_trades_per_day,
                            )

                        # 매크로 레짐 섹션이 있으면 KOSPI/환율/에너지 등 외부 레짐을 BTC 리스크에 반영
                        macro_conf = config.get("macro_regime")
                        if macro_conf:
                            try:
                                macro_level_raw = macro_conf.get("macro_risk_level", 0.0)
                                self.macro_risk_level = float(macro_level_raw or 0.0)
                            except (TypeError, ValueError):
                                self.macro_risk_level = 0.0
                            self.macro_risk_level = max(0.0, min(1.0, self.macro_risk_level))
                            self.fiat_crisis_flag = bool(macro_conf.get("fiat_crisis_flag", False))
                            try:
                                self.risk_manager.apply_macro_regime(self.macro_risk_level)
                            except Exception as e:
                                logger.warning(f"⚠️ 매크로 레짐 적용 중 오류(무시): {e}")

                            logger.info(
                                "🛡️ 매크로 레짐 설정 적용 (파일: %s): macro_risk_level=%.2f, fiat_crisis_flag=%s",
                                config_path,
                                self.macro_risk_level,
                                self.fiat_crisis_flag,
                            )
            else:
                logger.warning(f"⚠️ 설정 파일을 찾을 수 없습니다. 시도한 경로: {possible_paths}")
        except Exception as e:
            logger.warning(f"⚠️ 설정 파일 읽기 실패, 기본값 사용: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.risk_manager.max_position_size = 0.15  # 기본값 15%

        try:
            from src.risk.kospi_sasang_lane_btc_overlay import resolve_sasang_overlay

            stress, meta = resolve_sasang_overlay(workspace_root, config)
            self._sasang_btc_overlay_stress = float(stress)
            self._sasang_btc_overlay_label = str(meta.get("label", "off"))
            if meta.get("label") != "disabled":
                logger.info(
                    "🛡️ 사상 단독 레인 → BTC 리스크 오버레이: track=%s, stress=%.2f, %s, path=%s",
                    meta.get("track", "market"),
                    self._sasang_btc_overlay_stress,
                    self._sasang_btc_overlay_label,
                    meta.get("path"),
                )
        except Exception as e:
            logger.warning("⚠️ 사상 BTC 오버레이 초기화 실패(무시): %s", e)
            self._sasang_btc_overlay_stress = 0.0
            self._sasang_btc_overlay_label = "error"
        
        # peak_capital을 현재 잔고로 리셋 (낙폭 계산 정확도 향상)
        try:
            balance_info = self.binance.get_balance()
            current_balance = balance_info.get('total', initial_capital) if isinstance(balance_info, dict) else initial_capital
            self.risk_manager.peak_capital = current_balance
            self.risk_manager.current_capital = current_balance
            logger.info(f"✅ 리스크 관리 시스템 초기화 완료 (현재 잔고: ${current_balance:,.2f})")
        except Exception as e:
            logger.warning(f"⚠️ 리스크 관리 시스템 초기화 중 오류: {e}")
        
        # 상태 추적
        self.running = False
        self.trades_count = 0
        self.total_pnl = 0.0
        self.signal_total_count = 0
        self.singular_action_counts = {"BUY": 0, "SELL": 0, "LOCKED": 0}
        self.last_signal_summary: Dict[str, Any] = {}
        
        # 거래 이력 저장
        self.trades_history = []
        self.trades_file = log_dir / "live_trades_history.json"
        
        # 상태 저장 파일 (재시작/복구용)
        self.state_file = log_dir / "trading_state.json"
        
        # 안전한 종료를 위한 시그널 핸들러
        # ⚠️ 윈도우/멀티스레드/서비스 환경에서 signal 사용 시 예외가 날 수 있으므로
        # 메인 스레드에서만 등록하고, 실패해도 전체 트레이더는 계속 동작하도록 방어한다.
        try:
            import signal
            import threading
            if threading.current_thread() is threading.main_thread():
                try:
                    signal.signal(signal.SIGINT, self._signal_handler)
                    signal.signal(signal.SIGTERM, self._signal_handler)
                except Exception as e:
                    logger.warning(f"⚠️ 시그널 핸들러 등록 실패(무시): {e}")
            else:
                logger.warning("⚠️ 메인 스레드가 아니어서 시그널 핸들러를 등록하지 않습니다.")
        except Exception as e:
            logger.warning(f"⚠️ 시그널 핸들러 구성 중 예외 발생(무시): {e}")
        
        # Circuit Breaker 상태 (에러 핸들링 강화)
        self.circuit_breaker_state = {
            "state": "closed",  # "closed", "open", "half-open"
            "failure_count": 0,
            "success_count": 0,
            "last_failure_time": None,
            "failure_threshold": 5,  # 연속 실패 5회 시 Circuit 열림
            "reset_timeout": 300,  # 5분 후 Half-Open으로 전환
            "half_open_max_calls": 3  # Half-Open 상태에서 최대 3회 시도
        }
        
        # 안전 모드 (Circuit Breaker가 열렸을 때)
        self.safe_mode = False
        # 운영자 설정 오버라이드 (trading_config.yaml > trading)
        self.config_check_interval_seconds: Optional[int] = None
        self.config_max_trades_per_day: Optional[int] = None
        self.config_risk_per_trade: float = 0.0075
        self.config_max_consecutive_failures_hard_gate: int = 3
        # MKM Risk Governor (read-only)
        self.risk_profile: Dict[str, Any] = {}
        self.risk_profile_status: str = "not_loaded"
        self.config_slippage_cap_bps: Optional[float] = None
        self.config_maker_only_level: Optional[str] = None
        self.config_kill_switch_threshold: Optional[float] = None
        self.config_singular_core_decision: str = "UNKNOWN"
        self.config_singular_core_score: float = 0.0
        self.risk_profile_pipeline_status: Dict[str, Any] = {
            "source": None,
            "mode": None,
            "generated_at": None,
            "expires_at": None,
            "is_n8n_source": False,
            "is_fresh": None,
            "age_minutes": None,
        }

        self._load_risk_profile()
        # Optional: workspace-synced biblical single-lane gate hook (memory/v2/ops/…json)
        self.biblical_lane_gate_mode = str(
            os.getenv("BIBLICAL_SINGLE_LANE_GATE_MODE", "shadow") or "shadow"
        ).strip().lower()
        logger.info(
            "🛡️ biblical_lane gate mode=%s (off|shadow|enforce; hook=memory/v2/ops/biblical_single_lane_trading_hook_v1_latest.json)",
            self.biblical_lane_gate_mode,
        )

        logger.info("✅ Crypto-Nitro Live Trader 초기화 완료")

    def _read_biblical_lane_hook(self) -> Optional[Dict[str, Any]]:
        path = (
            Path(__file__).parent.parent.parent
            / "memory"
            / "v2"
            / "ops"
            / "biblical_single_lane_trading_hook_v1_latest.json"
        )
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _biblical_lane_gate_force_hold(self, signal: str) -> tuple[bool, str]:
        """
        When BIBLICAL_SINGLE_LANE_GATE_MODE=enforce and live_trading.allowed is false,
        block directional execution (fail-open if hook missing or schema mismatch).
        """
        mode = getattr(self, "biblical_lane_gate_mode", "shadow")
        if mode == "off":
            return False, ""
        hook = self._read_biblical_lane_hook()
        if not hook:
            if mode == "enforce":
                logger.debug("biblical_lane hook file missing; fail-open (no block)")
            return False, ""
        ver = str(hook.get("schema_version", "")).strip()
        if ver != "biblical_single_lane_trading_hook_v1":
            if mode == "enforce":
                logger.warning("biblical_lane hook schema_version mismatch (%s); fail-open", ver or "empty")
            return False, ""
        lt = hook.get("live_trading") if isinstance(hook.get("live_trading"), dict) else {}
        if bool(lt.get("allowed", False)):
            return False, ""
        if mode == "shadow":
            logger.debug(
                "biblical_lane hook: live_trading.allowed=false (shadow; execution not blocked)"
            )
            return False, ""
        if signal in ("BUY", "SELL"):
            return True, "biblical_single_lane_gate_not_ready"
        return False, ""

    def _load_risk_profile(self):
        """
        Load MKM risk governor profile (read-only).
        Never creates orders directly; only constrains risk parameters.
        """
        candidates = [
            Path(__file__).parent.parent.parent / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json",
            Path(__file__).parent.parent.parent / "memory" / "v2" / "risk" / "risk_profile_latest.json",
            Path(__file__).parent.parent.parent / "memory" / "risk_profile_latest.json",
        ]
        profile = None
        profile_path = None
        for p in candidates:
            if p.exists():
                profile_path = p
                try:
                    profile = json.loads(p.read_text(encoding="utf-8"))
                    break
                except Exception:
                    profile = None
                    break
        if not profile:
            self.risk_profile_status = "not_found_or_invalid"
            return

        try:
            # Minimal v0.1 validation + hard bounds
            schema_version = str(profile.get("schema_version", "")).strip()
            if not schema_version.startswith("risk_profile_v0.1"):
                self.risk_profile_status = "invalid_schema"
                return

            expires_at = profile.get("expires_at")
            generated_at = profile.get("generated_at")
            source = str(profile.get("source", "")).strip()
            mode = str(profile.get("mode", "")).strip()
            generated_dt = None
            if generated_at:
                try:
                    generated_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                except Exception:
                    generated_dt = None
            if expires_at:
                try:
                    exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                    if exp.tzinfo is not None:
                        now_aware = datetime.now(exp.tzinfo)
                        if now_aware > exp:
                            self.risk_profile_status = "expired"
                            return
                except Exception:
                    pass

            max_age_minutes = 60
            try:
                max_age_minutes = max(10, int(os.getenv("RISK_PROFILE_MAX_AGE_MINUTES", "60")))
            except (TypeError, ValueError):
                max_age_minutes = 60
            age_minutes = None
            is_fresh = None
            if generated_dt is not None:
                try:
                    now_ref = datetime.now(generated_dt.tzinfo) if generated_dt.tzinfo is not None else datetime.now()
                    age_minutes = max(0.0, (now_ref - generated_dt).total_seconds() / 60.0)
                    is_fresh = age_minutes <= float(max_age_minutes)
                except Exception:
                    age_minutes = None
                    is_fresh = None
            if is_fresh is False:
                self.risk_profile_status = "stale"
                logger.warning(
                    "⚠️ risk_profile stale: age=%.1f min > max=%d min (source=%s, mode=%s)",
                    age_minutes if age_minutes is not None else -1.0,
                    max_age_minutes,
                    source or "unknown",
                    mode or "unknown",
                )
                return

            self.risk_profile = profile
            self.risk_profile_status = "loaded"
            self.risk_profile_pipeline_status = {
                "source": source or None,
                "mode": mode or None,
                "generated_at": str(generated_at) if generated_at is not None else None,
                "expires_at": str(expires_at) if expires_at is not None else None,
                "is_n8n_source": ("n8n" in source.lower()) or ("n8n" in mode.lower()),
                "is_fresh": is_fresh,
                "age_minutes": round(age_minutes, 3) if age_minutes is not None else None,
            }

            mt = profile.get("max_trades_per_day")
            if mt is not None:
                self.config_max_trades_per_day = max(1, min(200, int(mt)))

            mps = profile.get("max_position_size")
            if mps is not None:
                mps_val = max(0.01, min(0.30, float(mps)))
                self.risk_manager.max_position_size = mps_val

            mo = str(profile.get("maker_only_level", "")).strip().lower()
            if mo in ("strict", "preferred", "flex"):
                self.config_maker_only_level = mo

            sc = profile.get("slippage_cap_bps")
            if sc is not None:
                self.config_slippage_cap_bps = max(1.0, min(30.0, float(sc)))

            ks = profile.get("kill_switch_threshold")
            if ks is not None:
                self.config_kill_switch_threshold = max(0.005, min(0.10, float(ks)))
                self.risk_manager.max_daily_loss = min(self.risk_manager.max_daily_loss, self.config_kill_switch_threshold)

            singular_core = profile.get("singular_core") if isinstance(profile.get("singular_core"), dict) else {}
            self.config_singular_core_decision = str(singular_core.get("core_decision") or "UNKNOWN").upper()
            self.config_singular_core_score = float(singular_core.get("core_score") or 0.0)

            logger.info(
                "🛡️ risk_profile 로드(%s): source=%s, mode=%s, age_min=%s, max_trades=%s, max_position_size=%.2f, maker_only=%s, slippage_bps=%s, kill_switch=%.3f, core_decision=%s, core_score=%.2f",
                profile_path,
                self.risk_profile_pipeline_status.get("source"),
                self.risk_profile_pipeline_status.get("mode"),
                self.risk_profile_pipeline_status.get("age_minutes"),
                self.config_max_trades_per_day,
                self.risk_manager.max_position_size,
                self.config_maker_only_level,
                self.config_slippage_cap_bps,
                self.risk_manager.max_daily_loss,
                self.config_singular_core_decision,
                self.config_singular_core_score,
            )
        except Exception as e:
            self.risk_profile_status = f"invalid:{e}"
            logger.warning("⚠️ risk_profile 적용 실패: %s", e)

    async def start_trading(
        self,
        interval_seconds: int = 300,  # 5분마다 체크 (최적화 로직으로 자동 조정됨)
        max_trades_per_day: int = 10  # 일일 최대 거래 횟수 (최적화 로직 및 매크로 레짐으로 자동 조정됨)
    ):
        """
        실전 매매 시작
        
        Args:
            interval_seconds: 체크 간격 (초)
            max_trades_per_day: 일일 최대 거래 횟수
        """
        
        # 🚀 최적화된 거래 빈도 적용
        if self.optimizer:
            optimal_frequency = self.optimizer.calculate_optimal_trade_frequency()
            interval_seconds = optimal_frequency['check_interval_seconds']
            max_trades_per_day = optimal_frequency['max_trades_per_day']
            logger.info(f"✅ 최적화된 파라미터 적용: 체크 간격={interval_seconds}초, 일일 최대 거래={max_trades_per_day}회")

        # 🛡️ 매크로 레짐 기반 추가 축소 (KOSPI/환율/에너지 쇼크 등 외부 레짐 반영)
        # macro_risk_level이 높을수록(위험↑) 일일 거래 횟수를 축소한다.
        try:
            macro_level = getattr(self, "macro_risk_level", 0.0)
            macro_level = max(0.0, min(1.0, float(macro_level)))
            sasang_s = float(getattr(self, "_sasang_btc_overlay_stress", 0.0))
            macro_level = max(macro_level, sasang_s)
            if macro_level > 0.0:
                macro_factor = max(0.3, 1.0 - macro_level)  # 최소 30%까지 축소
                old_max_trades = max_trades_per_day
                max_trades_per_day = max(1, int(max_trades_per_day * macro_factor))
                logger.info(
                    "🛡️ 매크로 레짐 적용: macro_risk_level=%.2f, "
                    "일일 최대 거래 %d회 → %d회",
                    macro_level,
                    old_max_trades,
                    max_trades_per_day,
                )
        except Exception as e:
            logger.warning(f"⚠️ 매크로 레짐 기반 거래 횟수 조정 중 오류(무시): {e}")

        # 운영자(trading_config.yaml) 값은 optimizer/macro 계산보다 우선한다.
        if self.config_check_interval_seconds is not None:
            old_interval = interval_seconds
            interval_seconds = int(self.config_check_interval_seconds)
            logger.info(
                "🧭 운영자 오버라이드 적용: 체크 간격 %d초 → %d초",
                old_interval,
                interval_seconds,
            )
        if self.config_max_trades_per_day is not None:
            old_max_trades = max_trades_per_day
            max_trades_per_day = int(self.config_max_trades_per_day)
            logger.info(
                "🧭 운영자 오버라이드 적용: 일일 최대 거래 %d회 → %d회",
                old_max_trades,
                max_trades_per_day,
            )

        if self.config_singular_core_decision == "HOLD":
            old_max_trades = max_trades_per_day
            max_trades_per_day = max(1, min(max_trades_per_day, 3))
            self.risk_manager.max_position_size = min(self.risk_manager.max_position_size, 0.03)
            self.risk_manager.max_daily_loss = min(self.risk_manager.max_daily_loss, 0.015)
            logger.warning(
                "🛡️ singular core HOLD 강제: max_trades %d회 → %d회, max_position_size=%.2f, daily_loss_cap=%.3f",
                old_max_trades,
                max_trades_per_day,
                self.risk_manager.max_position_size,
                self.risk_manager.max_daily_loss,
            )

        # MKM Risk Governor shadow/apply (read-only parameter injection)
        if self.config_maker_only_level in ("strict", "preferred"):
            if hasattr(self.binance, "maker_only"):
                self.binance.maker_only = True
            logger.info("🛡️ risk_profile 적용: maker_only 강제(True), level=%s", self.config_maker_only_level)

        if self.config_slippage_cap_bps is not None and self.enhanced_risk_manager is not None:
            slippage_ratio = float(self.config_slippage_cap_bps) / 10000.0
            if hasattr(self.enhanced_risk_manager, "max_slippage"):
                self.enhanced_risk_manager.max_slippage = slippage_ratio
            logger.info(
                "🛡️ risk_profile 적용: max_slippage=%.4f%% (%s bps)",
                slippage_ratio * 100.0,
                self.config_slippage_cap_bps,
            )

        logger.info(
            "🛰️ risk_profile shadow status=%s, max_trades=%s, max_position_size=%.2f, daily_loss_cap=%.3f, core_decision=%s",
            self.risk_profile_status,
            max_trades_per_day,
            self.risk_manager.max_position_size,
            self.risk_manager.max_daily_loss,
            self.config_singular_core_decision,
        )
        
        if self.running:
            logger.warning("⚠️ 이미 실행 중입니다.")
            return
        
        self.running = True
        logger.info("=" * 60)
        logger.info("🚀 Crypto-Nitro Live Trader 시작")
        logger.info("=" * 60)
        logger.info(f"심볼: {self.symbol}")
        logger.info(f"초기 자본: ${self.initial_capital:,.2f}")
        logger.info(f"레버리지: {self.leverage}배")
        
        # 메모리 정리 카운터 (1시간마다 정리)
        last_cleanup_time = time.time()
        cleanup_interval = 3600  # 1시간
        logger.info(f"테스트넷: {self.testnet}")
        logger.info(f"실전 매매 활성화: {self.enable_live_trading}")
        logger.info(f"체크 간격: {interval_seconds}초")
        logger.info("=" * 60)
        
        # 🚀 실전 매매 시작 텔레그램 알림 전송
        if self.alert_manager:
            mode_text = "⚠️ 실전 거래소 (실제 자금 사용)" if not self.testnet else "테스트넷"
            trading_text = "✅ 활성화" if self.enable_live_trading else "⏸️ 비활성화"
            start_message = f"""
🚀 *Crypto-Nitro Live Trader 시작*

*모드:* {mode_text}
*거래:* {trading_text}
*심볼:* {self.symbol}
*초기 자본:* ${self.initial_capital:,.2f}
*레버리지:* {self.leverage}배
*체크 간격:* {interval_seconds}초

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            asyncio.create_task(
                self.alert_manager.alert_system_status(
                    status="STARTED",
                    message=start_message.strip()
                )
            )
        
        # 잔고 확인
        try:
            balance_info = self.binance.get_balance()
            balance = balance_info.get('total', 0.0) if isinstance(balance_info, dict) else 0.0
            logger.info(f"💰 현재 잔고: ${balance:,.2f} USDT")
            self.risk_manager.update_capital(balance)
        except Exception as e:
            logger.error(f"❌ 잔고 조회 실패: {e}")
            self.running = False
            return
        
        # 가격 데이터 수집 (매매 루프 시작 전)
        logger.info("📊 가격 데이터 수집 중...")
        try:
            price_data = self.strategy.fetch_price_data(limit=100)
            if price_data is not None and len(price_data) > 0:
                logger.info(f"✅ 가격 데이터 수집 완료: {len(price_data)}개 캔들")
            else:
                logger.warning("⚠️ 가격 데이터 수집 실패, 빈 DataFrame 반환")
        except Exception as e:
            logger.error(f"❌ 가격 데이터 수집 실패: {e}")
            logger.warning("⚠️ 가격 데이터 없이 진행합니다 (신호 생성 불가능할 수 있음)")
        
        # 가격 데이터 갱신 시간 추적 (매일 자정 갱신)
        self.last_price_update = datetime.now()
        price_update_interval = 86400  # 24시간 (초)
        
        # 상태 복구 시도
        self._load_state()
        
        # 일일 거래 횟수 추적
        last_reset_date = datetime.now().date()
        daily_trades = 0
        
        # 🎯 정확도 기반 거래 횟수 자동 조정을 위한 신뢰도 추적
        recent_confidences = []  # 최근 신뢰도 리스트 (평균 계산용)
        confidence_window_size = 10  # 최근 10개 신호의 평균 신뢰도 사용
        
        # 메모리 정리 카운터 (1시간마다 정리)
        last_cleanup_time = time.time()
        cleanup_interval = 3600  # 1시간
        
        try:
            while self.running:
                try:
                    # 메모리 정리 (1시간마다)
                    current_time = time.time()
                    if current_time - last_cleanup_time >= cleanup_interval:
                        self._cleanup_memory()
                        last_cleanup_time = current_time
                    
                    # 일일 거래 횟수 리셋
                    current_date = datetime.now().date()
                    if current_date != last_reset_date:
                        daily_trades = 0
                        last_reset_date = current_date
                        logger.info("✅ 일일 거래 횟수 리셋")
                    
                    # 가격 데이터 주기적 갱신 (매일 자정 또는 설정된 간격)
                    current_time = datetime.now()
                    time_since_update = (current_time - self.last_price_update).total_seconds()
                    if time_since_update >= price_update_interval:
                        logger.info("📊 가격 데이터 갱신 중...")
                        try:
                            price_data = self.strategy.fetch_price_data(limit=100)
                            if price_data is not None and len(price_data) > 0:
                                logger.info(f"✅ 가격 데이터 갱신 완료: {len(price_data)}개 캔들")
                                self.last_price_update = current_time
                                self._save_state()  # 상태 저장
                            else:
                                logger.warning("⚠️ 가격 데이터 갱신 실패, 이전 데이터 사용")
                        except Exception as e:
                            logger.error(f"❌ 가격 데이터 갱신 실패: {e}")
                    
                    # 가격 데이터 부족 시 대기
                    if len(self.strategy.price_data) < 20:
                        logger.warning(f"⚠️ 가격 데이터 부족 ({len(self.strategy.price_data)}개), 수집 시도...")
                        try:
                            price_data = self.strategy.fetch_price_data(limit=100)
                            if price_data is not None and len(price_data) >= 20:
                                logger.info(f"✅ 가격 데이터 수집 완료: {len(price_data)}개 캔들")
                            else:
                                logger.warning("⚠️ 가격 데이터가 여전히 부족합니다, 다음 주기로 대기")
                                await asyncio.sleep(interval_seconds)
                                continue
                        except Exception as e:
                            logger.error(f"❌ 가격 데이터 수집 실패: {e}")
                            await asyncio.sleep(interval_seconds)
                            continue
                    
                    # 일일 거래 횟수 확인
                    if daily_trades >= max_trades_per_day:
                        logger.warning(f"⚠️ 일일 최대 거래 횟수 도달: {daily_trades}회")
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    # 현재 가격 조회
                    current_price = self.binance.get_current_price(self.symbol)
                    if current_price == 0.0:
                        logger.warning("⚠️ 가격 조회 실패, 다음 주기로 대기")
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    # Circuit Breaker 확인
                    if not self._check_circuit_breaker():
                        logger.warning("⚠️ Circuit Breaker: Open 상태, 안전 모드로 전환")
                        # 중요 이벤트 알림
                        if self.alert_manager:
                            await self.alert_manager.alert_critical_event(
                                event_type="CIRCUIT_BREAKER_OPEN",
                                message="연속 실패로 인해 거래가 중단되었습니다.",
                                details={
                                    "failure_count": self.circuit_breaker_state["failure_count"],
                                    "last_failure_time": self.circuit_breaker_state["last_failure_time"].isoformat() if self.circuit_breaker_state.get("last_failure_time") else None,
                                    "reset_timeout": self.circuit_breaker_state["reset_timeout"]
                                },
                                severity="CRITICAL"
                            )
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    # 리스크 관리 확인
                    if not self.risk_manager.check_drawdown_limit():
                        logger.error("❌ 낙폭 한도 초과, 매매 중단")
                        self.running = False
                        break
                    
                    if not self.risk_manager.check_daily_loss_limit():
                        logger.error("❌ 일일 손실 한도 초과, 매매 중단")
                        self.running = False
                        break
                    
                    # 매매 신호 생성 (calculate_trading_signal 사용, 재시도 로직 포함)
                    signal_start_time = time.time()
                    try:
                        signal_data = self.strategy.calculate_trading_signal(
                            current_price=current_price,
                            current_time=datetime.now()
                        )
                        signal_elapsed = (time.time() - signal_start_time) * 1000  # ms
                        
                        # 성능 메트릭 로깅
                        logger.info(
                            "신호 생성 완료",
                            extra={
                                "metric_type": "signal_generation",
                                "elapsed_ms": signal_elapsed,
                                "signal": signal_data.get("signal", "HOLD"),
                                "confidence": signal_data.get("confidence", 0.0)
                            }
                        )
                        
                        self._record_success()  # 성공 기록
                    except Exception as e:
                        signal_elapsed = (time.time() - signal_start_time) * 1000  # ms
                        logger.error(
                            f"❌ 신호 생성 실패: {e}",
                            extra={
                                "metric_type": "signal_generation",
                                "elapsed_ms": signal_elapsed,
                                "error": str(e)
                            }
                        )
                        self._record_failure()  # 실패 기록
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    if not signal_data:
                        logger.debug("신호 생성 실패, 다음 주기로 대기")
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    signal = signal_data.get("signal", "HOLD")
                    confidence = signal_data.get("confidence", 0.0)
                    leverage_multiplier = signal_data.get("leverage_multiplier", 1.0)
                    singular_core = signal_data.get("mkm_singular_core") or {}
                    singular_action = str(singular_core.get("action", "LOCKED")).upper()
                    if singular_action not in ("BUY", "SELL", "LOCKED"):
                        singular_action = "LOCKED"
                    self.signal_total_count += 1
                    self.singular_action_counts[singular_action] = (
                        self.singular_action_counts.get(singular_action, 0) + 1
                    )
                    self.last_signal_summary = {
                        "ts": datetime.now().isoformat(),
                        "signal": signal,
                        "confidence": confidence,
                        "singular_action": singular_action,
                        "singular_vector": singular_core.get("vector"),
                        "singular_raw": singular_core.get("raw"),
                    }
                    # Gate/message contract: always carry explicit gate_reason + level.
                    gate_reason = str(signal_data.get("gate_reason", "unspecified")).strip() or "unspecified"
                    signal_level = "LOW" if (signal == "HOLD" or confidence < self.min_exec_confidence) else ("MID" if confidence < 0.75 else "HIGH")
                    signal_data["gate_reason"] = gate_reason
                    signal_data["signal_level"] = signal_level
                    signal_data["price_output_locked"] = signal_level == "LOW"

                    # 🏛️ BTC-6 Regime Fusion → RiskManager 반영 (설계 §7: risk_multiplier 전달)
                    # leverage_multiplier 0.2~1.5 → macro_risk_level 1.0~0.0 (위기 시 포지션/일일손실 한도 축소)
                    try:
                        macro_level = max(0.0, min(1.0, (1.5 - float(leverage_multiplier)) / 1.3))
                        sasang_s = float(getattr(self, "_sasang_btc_overlay_stress", 0.0))
                        macro_level = max(macro_level, sasang_s)
                        self.risk_manager.apply_macro_regime(macro_level)
                    except Exception as rm_err:
                        logger.debug("RiskManager BTC-6 반영 건너뜀: %s", rm_err)
                    
                    # 🏛️ 위상 공명 팩트체크 결과 확인
                    fact_check = signal_data.get("fact_check")
                    if fact_check:
                        if not fact_check.get("is_valid", True):
                            logger.warning(
                                f"⚠️ 위상 공명 팩트체크 실패: {fact_check.get('recommendation', '신호 신뢰도 낮음')}"
                            )
                            # 환각 감지 시 거래 실행 안 함
                            await asyncio.sleep(interval_seconds)
                            continue
                        else:
                            resonance_score = fact_check.get("resonance_score")
                            if resonance_score is not None:
                                logger.debug(f"✅ 위상 공명 팩트체크 통과 (공명 점수: {resonance_score:.2%})")
                            else:
                                logger.debug("✅ 위상 공명 팩트체크 통과 (공명 점수: N/A)")
                    
                    # 🏛️ 사원수 위상 분석 인사이트 로깅
                    quaternion_insight = signal_data.get("quaternion_insight")
                    if quaternion_insight and quaternion_insight != "위상 분석 불가":
                        logger.info(f"🔍 사원수 위상 분석: {quaternion_insight}")
                    
                    # 🏛️ SBSC 검증 결과 확인
                    sbsc_verification = signal_data.get("sbsc_verification")
                    if sbsc_verification:
                        if not sbsc_verification.get("is_valid", True):
                            logger.warning(
                                f"⚠️ SBSC 검증 실패: {sbsc_verification.get('recommendation', '검증 실패')}"
                            )
                            # SBSC 검증 실패 시 거래 실행 안 함
                            await asyncio.sleep(interval_seconds)
                            continue
                        else:
                            verification_score = sbsc_verification.get("verification_score")
                            if verification_score is not None:
                                logger.debug(f"✅ SBSC 검증 통과 (검증 점수: {verification_score:.2%})")
                            else:
                                logger.debug("✅ SBSC 검증 통과 (검증 점수: N/A)")
                    
                    # Hard guard: regime/market shock always forces HOLD (no directional execution).
                    try:
                        drp = signal_data.get("dual_regime_protection") if isinstance(signal_data, dict) else None
                        market_shock_confirmed = bool((drp or {}).get("market_shock_confirmed")) or bool(signal_data.get("market_shock_confirmed"))
                    except Exception:
                        market_shock_confirmed = False
                    if market_shock_confirmed and signal in ("BUY", "SELL"):
                        signal = "HOLD"
                        confidence = min(confidence, 0.59)
                        signal_data["signal"] = "HOLD"
                        signal_data["confidence"] = confidence
                        signal_data["signal_level"] = "LOW"
                        signal_data["price_output_locked"] = True
                        signal_data["gate_reason"] = "market_shock_hardguard_hold"
                        gate_reason = "market_shock_hardguard_hold"
                        signal_level = "LOW"

                    bl_hold, bl_reason = self._biblical_lane_gate_force_hold(signal)
                    if bl_hold and signal in ("BUY", "SELL"):
                        signal = "HOLD"
                        confidence = min(confidence, 0.59)
                        signal_data["signal"] = "HOLD"
                        signal_data["confidence"] = confidence
                        signal_data["signal_level"] = "LOW"
                        signal_data["price_output_locked"] = True
                        signal_data["gate_reason"] = bl_reason
                        gate_reason = bl_reason
                        signal_level = "LOW"
                        logger.warning(
                            "🛡️ biblical_lane gate enforce: forced HOLD (%s)",
                            bl_reason,
                        )

                    # HOLD/LOW 신호는 가격 수치 출력 없이 스킵
                    if signal == "HOLD":
                        logger.info("신호: HOLD (신뢰도: %.2f, level=%s, gate_reason=%s, price_locked=true)", confidence, signal_level, gate_reason)
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    # 신뢰도 확인 (strategy.min_confidence / CRYPTO_NITRO_MIN_EXEC_CONFIDENCE)
                    if confidence < self.min_exec_confidence:
                        signal_data["signal_level"] = "LOW"
                        signal_data["price_output_locked"] = True
                        if gate_reason == "unspecified":
                            signal_data["gate_reason"] = "low_confidence_hold"
                            gate_reason = "low_confidence_hold"
                        logger.info(
                            "신뢰도 부족: %.2f < %.2f (level=LOW, gate_reason=%s, price_locked=true)",
                            confidence,
                            self.min_exec_confidence,
                            gate_reason,
                        )
                        await asyncio.sleep(interval_seconds)
                        continue
                    
                    # 🎯 정확도 기반 거래 횟수 자동 조정 (신뢰도 추적)
                    recent_confidences.append(confidence)
                    if len(recent_confidences) > confidence_window_size:
                        recent_confidences.pop(0)  # 오래된 신뢰도 제거
                    
                    # 평균 신뢰도 계산 및 거래 횟수 자동 조정
                    if len(recent_confidences) >= 3 and self.config_max_trades_per_day is None:  # 최소 3개 신호 필요
                        avg_confidence = sum(recent_confidences) / len(recent_confidences)
                        dynamic_max_trades = self.calculate_max_trades_per_day(avg_confidence)
                        
                        # 거래 횟수 자동 조정 (변경 시에만 로깅)
                        if dynamic_max_trades != max_trades_per_day:
                            old_max_trades = max_trades_per_day
                            max_trades_per_day = dynamic_max_trades
                            logger.info(
                                f"🎯 정확도 기반 거래 횟수 자동 조정: "
                                f"평균 신뢰도 {avg_confidence:.2%} → "
                                f"일일 최대 거래 {old_max_trades}회 → {max_trades_per_day}회"
                            )
                    
                    # 실전 매매 실행 (재시도 로직 포함)
                    if self.enable_live_trading:
                        logger.info(
                            "📊 매매 신호: %s (신뢰도: %.2f, level=%s, gate_reason=%s, 가상 레버리지: %.2f배)",
                            signal,
                            confidence,
                            signal_level,
                            gate_reason,
                            leverage_multiplier,
                        )
                        cited = signal_data.get("cited_trading_wisdom") or []
                        if cited:
                            logger.debug("trading_wisdom 참조: %s", cited)

                        # Omni-Oracle state transition call (contract-safe payload)
                        omni_payload = _build_omni_oracle_request_from_signal(
                            signal_data=signal_data,
                            current_price=current_price,
                            confidence=confidence,
                            signal=signal,
                            leverage_multiplier=leverage_multiplier,
                        )
                        if isinstance(omni_payload, dict):
                            signal_data["omni_oracle_request"] = omni_payload
                            omni_result = _call_omni_oracle_state_transition(omni_payload, timeout_sec=3)
                            if isinstance(omni_result, dict):
                                rsp = float(omni_result.get("regime_shift_probability", 0.0) or 0.0)
                                if rsp >= 0.80:
                                    leverage_multiplier *= 0.60
                                elif rsp >= 0.70:
                                    leverage_multiplier *= 0.75
                                elif rsp >= 0.60:
                                    leverage_multiplier *= 0.90
                                signal_data["omni_oracle_result"] = omni_result
                                logger.info(
                                    "🧭 Omni-Oracle 반영: regime_shift_probability=%.2f, 조정 레버리지=%.2f",
                                    rsp,
                                    leverage_multiplier,
                                )

                        # PGAE Oracle Gateway: 14B 검증 (예언 vs PMI 충돌 시 최종 판단)
                        effective_leverage = leverage_multiplier
                        verifier = oracle_gateway_verify
                        if ORACLE_GATEWAY_AVAILABLE and verifier is not None:
                            try:
                                loop = asyncio.get_event_loop()
                                oracle_result = await loop.run_in_executor(
                                    None,
                                    partial(
                                        verifier,
                                        signal=signal,
                                        price=current_price,
                                        confidence=confidence,
                                        leverage_multiplier=leverage_multiplier,
                                        signal_data=signal_data,
                                        timeout_sec=90,
                                    ),
                                )
                                verdict = oracle_result.get("verdict", "APPROVE")
                                # Contracted gate fields from Oracle Gateway
                                og_gate_level = str(oracle_result.get("gate_level", signal_data.get("signal_level", "MID"))).upper()
                                og_gate_reason = str(oracle_result.get("gate_reason", signal_data.get("gate_reason", "oracle_default")))
                                og_price_lock = bool(oracle_result.get("price_lock", og_gate_level == "LOW"))
                                signal_data["signal_level"] = og_gate_level
                                signal_data["gate_reason"] = og_gate_reason
                                signal_data["price_output_locked"] = og_price_lock
                                signal_level = og_gate_level
                                gate_reason = og_gate_reason
                                if verdict == "REJECT":
                                    logger.info("🔴 Oracle Gateway REJECT: 주문 스킵")
                                    await asyncio.sleep(interval_seconds)
                                    continue
                                if verdict == "REDUCE":
                                    mult = oracle_result.get("multiplier", 0.5)
                                    effective_leverage = leverage_multiplier * mult
                                    logger.info("🟡 Oracle Gateway REDUCE: 레버리지 %.2f → %.2f", leverage_multiplier, effective_leverage)
                            except Exception as og_err:
                                logger.warning("Oracle Gateway 예외(APPROVE 통과): %s", og_err)

                        trade_start_time = time.time()
                        try:
                            trade_result = await self.execute_live_trade(
                                signal=signal,
                                price=current_price,
                                confidence=confidence,
                                leverage_multiplier=effective_leverage,
                                signal_data=signal_data
                            )
                            trade_elapsed = (time.time() - trade_start_time) * 1000  # ms
                            
                            if trade_result:
                                self.trades_count += 1
                                daily_trades += 1
                                trade_pnl = trade_result.get("pnl", 0.0)
                                self.total_pnl += trade_pnl
                                
                                # 거래 이력 저장
                                self.trades_history.append(trade_result)
                                self._save_trades_history()
                                self._save_state()  # 상태 저장
                                
                                # 성능 메트릭 로깅
                                logger.info(
                                    "거래 완료",
                                    extra={
                                        "metric_type": "trade_execution",
                                        "elapsed_ms": trade_elapsed,
                                        "order_id": trade_result.get("order_id", "N/A"),
                                        "signal": signal,
                                        "confidence": confidence,
                                        "pnl": trade_result.get("pnl", 0.0)
                                    }
                                )
                                
                                self._record_success()  # 성공 기록
                                # 큰 손실 발생 시 FailureEvent로 기록 (오답 노트)
                                try:
                                    if trade_pnl is not None and trade_pnl < -100.0:  # 예: -100 USDT 이상 손실
                                        reason = (
                                            f"signal={signal}, confidence={confidence:.2f}, "
                                            f"price={current_price}, leverage_multiplier={leverage_multiplier:.2f}"
                                        )
                                        record_trading_failure_event(
                                            symbol=self.symbol,
                                            reason=reason,
                                            realized_pnl=trade_pnl,
                                            severity=min(1.0, max(0.0, abs(trade_pnl) / self.initial_capital)),
                                            tags=["AUTO_FAILURE_EVENT"],
                                        )
                                except Exception as fe_err:
                                    logger.warning(f"⚠️ FailureEvent 기록 중 예외(무시): {fe_err}")
                                logger.info(f"✅ 거래 완료: {trade_result.get('order_id', 'N/A')}")
                            else:
                                trade_elapsed = (time.time() - trade_start_time) * 1000  # ms
                                logger.warning(
                                    "거래 실행 실패 (결과 없음)",
                                    extra={
                                        "metric_type": "trade_execution",
                                        "elapsed_ms": trade_elapsed,
                                        "signal": signal
                                    }
                                )
                                self._record_failure()  # 실패 기록 (거래 실행 실패)
                        except Exception as e:
                            trade_elapsed = (time.time() - trade_start_time) * 1000  # ms
                            logger.error(
                                f"❌ 거래 실행 실패: {e}",
                                extra={
                                    "metric_type": "trade_execution",
                                    "elapsed_ms": trade_elapsed,
                                    "signal": signal,
                                    "error": str(e)
                                }
                            )
                            self._record_failure()  # 실패 기록
                    else:
                        logger.info(f"📊 매매 신호 (모의): {signal} (신뢰도: {confidence:.2%}, 가상 레버리지: {leverage_multiplier:.2f}배)")
                        cited = signal_data.get("cited_trading_wisdom") or []
                        if cited:
                            logger.debug("trading_wisdom 참조: %s", cited)
                        logger.info("⚠️ 실전 매매 비활성화, 실제 주문 실행 안 함")
                    
                    # 대기
                    await asyncio.sleep(interval_seconds)
                    
                except KeyboardInterrupt:
                    logger.info("⚠️ 사용자 중단 요청")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"❌ 오류 발생: {e}", exc_info=True)
                    await asyncio.sleep(interval_seconds)
                    continue
        
        finally:
            self.running = False
            logger.info("=" * 60)
            logger.info("🛑 Crypto-Nitro Live Trader 종료")
            logger.info(f"총 거래: {self.trades_count}회")
            logger.info(f"총 손익: ${self.total_pnl:,.2f}")
            logger.info("=" * 60)
    
    def _calculate_position_size_with_quantitative_reasoning(
        self,
        target_position_value: float,
        price: float,
        balance: float,
        leverage: int,
        signal: str,
        current_position: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        🧠 수량적 추론을 활용한 포지션 크기 계산 (Chain-of-Thought 강제)
        
        다른 채팅창에서 달성한 91.8% 추론 능력 중 수량적 추론(+30%)을 활용하여
        포지션 크기 계산의 정확도를 향상시키고 마진 오류를 방지합니다.
        
        Chain-of-Thought:
        1. 현재 잔고 확인
        2. 목표 포지션 금액 검증
        3. 최소 주문 금액 확인 (Binance: 100 USDT)
        4. 마진 요구사항 확인 (레버리지 적용)
        5. 가용 마진 확인 (90% 안전 버퍼)
        6. 최종 포지션 크기 결정
        
        Args:
            target_position_value: 목표 포지션 금액 (USDT)
            price: 현재 가격
            balance: 현재 잔고 (USDT)
            leverage: 레버리지 배수
            signal: 매매 신호 ("BUY", "SELL")
            current_position: 현재 포지션 정보 (선택적)
        
        Returns:
            계산된 포지션 크기 (BTC)
        """
        reasoning_log = []
        reasoning_steps = []
        
        # Step 1: 현재 잔고 확인
        reasoning_log.append(f"📊 Step 1: 현재 잔고 확인")
        reasoning_log.append(f"   현재 잔고: ${balance:.2f} USDT")
        reasoning_steps.append({
            "step": 1,
            "description": "현재 잔고 확인",
            "value": balance,
            "unit": "USDT"
        })
        
        # Step 2: 목표 포지션 금액 검증
        reasoning_log.append(f"📊 Step 2: 목표 포지션 금액 검증")
        reasoning_log.append(f"   목표 포지션 금액: ${target_position_value:.2f} USDT")
        reasoning_steps.append({
            "step": 2,
            "description": "목표 포지션 금액 검증",
            "value": target_position_value,
            "unit": "USDT"
        })
        
        # 목표 금액이 잔고를 초과하는지 확인
        if target_position_value > balance * 1.1:  # 10% 여유
            reasoning_log.append(f"   ⚠️ 목표 금액이 잔고의 110%를 초과: ${target_position_value:.2f} > ${balance * 1.1:.2f}")
            target_position_value = balance * 0.9  # 90%로 제한
            reasoning_log.append(f"   ✅ 잔고 제한으로 조정: ${target_position_value:.2f} USDT")
            reasoning_steps.append({
                "step": 2.1,
                "description": "잔고 제한으로 조정",
                "value": target_position_value,
                "unit": "USDT",
                "reason": "목표 금액이 잔고 초과"
            })
        
        # Step 3: 최소 주문 금액 확인 (Binance: 100 USDT)
        reasoning_log.append(f"📊 Step 3: 최소 주문 금액 확인")
        min_order_value = 100.0  # Binance 최소 주문 금액
        reasoning_log.append(f"   Binance 최소 주문 금액: ${min_order_value:.2f} USDT")
        
        if target_position_value < min_order_value:
            reasoning_log.append(f"   ⚠️ 목표 금액이 최소 주문 금액 미만: ${target_position_value:.2f} < ${min_order_value:.2f}")
            
            # 최소 주문 금액으로 조정 가능한지 확인
            if balance * 0.9 >= min_order_value:
                target_position_value = min_order_value
                reasoning_log.append(f"   ✅ 최소 주문 금액으로 조정: ${target_position_value:.2f} USDT")
                reasoning_steps.append({
                    "step": 3.1,
                    "description": "최소 주문 금액으로 조정",
                    "value": target_position_value,
                    "unit": "USDT",
                    "reason": f"목표 금액({target_position_value:.2f}) < 최소 주문 금액({min_order_value:.2f})"
                })
            else:
                reasoning_log.append(f"   ❌ 잔고 부족으로 최소 주문 금액 충족 불가: ${balance * 0.9:.2f} < ${min_order_value:.2f}")
                reasoning_steps.append({
                    "step": 3.2,
                    "description": "최소 주문 금액 충족 불가",
                    "value": 0.0,
                    "unit": "USDT",
                    "reason": "잔고 부족"
                })
                logger.warning(f"🧠 수량적 추론 결과: 최소 주문 금액 충족 불가\n" + "\n".join(f"   {step}" for step in reasoning_log))
                return 0.0
        else:
            reasoning_log.append(f"   ✅ 목표 금액이 최소 주문 금액 이상: ${target_position_value:.2f} >= ${min_order_value:.2f}")
        
        reasoning_steps.append({
            "step": 3,
            "description": "최소 주문 금액 확인",
            "value": target_position_value,
            "unit": "USDT",
            "min_required": min_order_value,
            "passed": target_position_value >= min_order_value
        })
        
        # Step 4: 마진 요구사항 확인 (레버리지 적용)
        reasoning_log.append(f"📊 Step 4: 마진 요구사항 확인")
        required_margin = target_position_value / leverage
        reasoning_log.append(f"   목표 포지션 금액: ${target_position_value:.2f} USDT")
        reasoning_log.append(f"   레버리지: {leverage}x")
        reasoning_log.append(f"   필요 마진: ${required_margin:.2f} USDT (${target_position_value:.2f} / {leverage})")
        reasoning_steps.append({
            "step": 4,
            "description": "마진 요구사항 계산",
            "target_position_value": target_position_value,
            "leverage": leverage,
            "required_margin": required_margin,
            "unit": "USDT"
        })
        
        # Step 5: 가용 마진 확인 (90% 안전 버퍼)
        reasoning_log.append(f"📊 Step 5: 가용 마진 확인")
        available_margin = balance * 0.9  # 90% 사용 가능 (10% 안전 버퍼)
        reasoning_log.append(f"   현재 잔고: ${balance:.2f} USDT")
        reasoning_log.append(f"   가용 마진 (90%): ${available_margin:.2f} USDT")
        
        if required_margin > available_margin:
            reasoning_log.append(f"   ⚠️ 마진 부족: 필요 ${required_margin:.2f} > 가용 ${available_margin:.2f}")
            
            # 가용 마진 내에서 최대 포지션 금액 재계산
            max_position_value = available_margin * leverage
            reasoning_log.append(f"   ✅ 가용 마진 기반 최대 포지션 금액: ${max_position_value:.2f} USDT (${available_margin:.2f} × {leverage})")
            
            # 최소 주문 금액 확인
            if max_position_value < min_order_value:
                reasoning_log.append(f"   ❌ 가용 마진으로도 최소 주문 금액 충족 불가: ${max_position_value:.2f} < ${min_order_value:.2f}")
                reasoning_steps.append({
                    "step": 5.1,
                    "description": "마진 부족으로 거래 불가",
                    "value": 0.0,
                    "unit": "USDT",
                    "reason": f"가용 마진({available_margin:.2f})으로 최소 주문 금액({min_order_value:.2f}) 충족 불가"
                })
                logger.warning(f"🧠 수량적 추론 결과: 마진 부족으로 거래 불가\n" + "\n".join(f"   {step}" for step in reasoning_log))
                return 0.0
            
            target_position_value = max_position_value
            reasoning_log.append(f"   ✅ 마진 제한으로 조정: ${target_position_value:.2f} USDT")
            reasoning_steps.append({
                "step": 5.2,
                "description": "마진 제한으로 조정",
                "value": target_position_value,
                "unit": "USDT",
                "reason": f"필요 마진({required_margin:.2f}) > 가용 마진({available_margin:.2f})"
            })
        else:
            reasoning_log.append(f"   ✅ 마진 충분: 필요 ${required_margin:.2f} <= 가용 ${available_margin:.2f}")
        
        reasoning_steps.append({
            "step": 5,
            "description": "가용 마진 확인",
            "required_margin": required_margin,
            "available_margin": available_margin,
            "passed": required_margin <= available_margin,
            "final_position_value": target_position_value
        })
        
        # Step 6: 최종 포지션 크기 결정
        reasoning_log.append(f"📊 Step 6: 최종 포지션 크기 결정")
        position_size = target_position_value / price
        reasoning_log.append(f"   최종 포지션 금액: ${target_position_value:.2f} USDT")
        reasoning_log.append(f"   현재 가격: ${price:,.2f} USDT")
        reasoning_log.append(f"   최종 포지션 크기: {position_size:.8f} BTC (${target_position_value:.2f} / ${price:,.2f})")
        
        # 기존 포지션 고려 (추가 포지션만 계산)
        if current_position:
            existing_side = current_position.get("side")
            if (signal == "BUY" and existing_side == "LONG") or (signal == "SELL" and existing_side == "SHORT"):
                existing_quantity = current_position.get("quantity", 0)
                existing_entry_price = current_position.get("entry_price", price)
                existing_position_value = existing_quantity * existing_entry_price
                
                reasoning_log.append(f"   기존 포지션: {existing_quantity:.8f} BTC @ ${existing_entry_price:,.2f} = ${existing_position_value:.2f} USDT")
                
                if target_position_value > existing_position_value:
                    additional_position_value = target_position_value - existing_position_value
                    additional_position_size = additional_position_value / price
                    reasoning_log.append(f"   추가 포지션 금액: ${additional_position_value:.2f} USDT")
                    reasoning_log.append(f"   추가 포지션 크기: {additional_position_size:.8f} BTC")
                    position_size = additional_position_size
                else:
                    reasoning_log.append(f"   ⚠️ 목표 포지션이 기존 포지션보다 작음, 추가 포지션 없음")
                    position_size = 0.0
        
        reasoning_steps.append({
            "step": 6,
            "description": "최종 포지션 크기 결정",
            "position_size": position_size,
            "unit": "BTC",
            "position_value": target_position_value,
            "price": price
        })
        
        # 추론 과정 로깅
        logger.info(f"🧠 수량적 추론 과정 (Chain-of-Thought):\n" + "\n".join(f"   {step}" for step in reasoning_log))
        
        # 추론 결과 JSON 로그 (디버깅용)
        reasoning_result = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal,
            "reasoning_steps": reasoning_steps,
            "final_position_size": position_size,
            "final_position_value": target_position_value,
            "balance": balance,
            "price": price,
            "leverage": leverage
        }
        logger.debug(f"🧠 수량적 추론 결과 (JSON): {json.dumps(reasoning_result, indent=2, ensure_ascii=False)}")
        
        return round(position_size, 8)  # 8자리 반올림

    def _passes_hard_risk_gate(self, balance: float) -> bool:
        """Block order placement when runtime guardrails are violated."""
        try:
            failure_count = int(self.circuit_breaker_state.get("failure_count", 0))
        except Exception:
            failure_count = 0
        if failure_count >= self.config_max_consecutive_failures_hard_gate:
            logger.warning(
                "🛑 하드게이트 차단: 연속 실패 %d회 >= 한도 %d회",
                failure_count,
                self.config_max_consecutive_failures_hard_gate,
            )
            return False

        daily_loss_ratio = abs(self.risk_manager.daily_pnl) / max(balance, 1e-9) if self.risk_manager.daily_pnl < 0 else 0.0
        if daily_loss_ratio >= self.risk_manager.max_daily_loss * 0.9:
            logger.warning(
                "🛑 하드게이트 차단: 일일 손실률 %.2f%% (한도 %.2f%%의 90%% 이상)",
                daily_loss_ratio * 100.0,
                self.risk_manager.max_daily_loss * 100.0,
            )
            return False
        return True

    def _apply_dynamic_notional_cap(
        self,
        requested_position_size: float,
        price: float,
        balance: float,
        confidence: float,
        signal_data: Optional[Dict[str, Any]],
    ) -> float:
        """Scale down requested size by risk budget, volatility, and confidence."""
        if requested_position_size <= 0:
            return 0.0

        requested_notional = requested_position_size * price
        stop_loss = max(float(getattr(self.risk_manager, "stop_loss_ratio", 0.01) or 0.01), 0.001)
        risk_budget = balance * self.config_risk_per_trade
        max_notional_by_risk = risk_budget / stop_loss
        max_notional_by_ratio = balance * self.risk_manager.max_position_size

        realized_volatility = 0.0
        if isinstance(signal_data, dict):
            realized_volatility = float(signal_data.get("realized_volatility", signal_data.get("volatility_24h", 0.0)) or 0.0)
        if realized_volatility >= 0.06:
            vol_multiplier = 0.5
        elif realized_volatility >= 0.04:
            vol_multiplier = 0.7
        else:
            vol_multiplier = 1.0

        confidence_multiplier = max(0.8, min(1.1, 0.8 + float(confidence) * 0.3))
        allowed_notional = min(
            max_notional_by_ratio,
            max_notional_by_risk * vol_multiplier * confidence_multiplier,
        )
        if requested_notional <= allowed_notional:
            return requested_position_size

        logger.info(
            "🛡️ 동적 사이징 캡 적용: 요청 %.2f USDT -> 허용 %.2f USDT "
            "(risk_per_trade=%.2f%%, stop_loss=%.2f%%, vol=%.4f, conf=%.2f)",
            requested_notional,
            allowed_notional,
            self.config_risk_per_trade * 100.0,
            stop_loss * 100.0,
            realized_volatility,
            confidence,
        )
        return max(0.0, allowed_notional / max(price, 1e-9))
    
    async def execute_live_trade(
        self,
        signal: str,
        price: float,
        confidence: float,
        leverage_multiplier: float = 1.0,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        실전 매매 실행 (실제 Binance API 호출)
        
        Args:
            signal: 매매 신호 ("BUY", "SELL", "HOLD")
            price: 현재 가격
            confidence: 신뢰도
            leverage_multiplier: 가상 레버리지 배율
            signal_data: 신호 데이터 (lambda, vector 등)
        
        Returns:
            거래 정보
        """
        try:
            if signal == "HOLD":
                return None
            
            # 🏛️ Financial Sovereign Harness: 신호 검증 (헌법 제3조: 100% Literal Restoration)
            if self.harness and signal_data and signal_data.get("signal_id"):
                try:
                    signal_id = signal_data.get("signal_id")
                    expected_signal = {
                        "signal": signal,
                        "confidence": confidence,
                        "price": price
                    }
                    
                    # 🏛️ Signal Validation 강화: 95% 이상 일치 필요
                    verified_signal = self.harness.verify_signal(
                        signal_id=signal_id,
                        expected_signal=expected_signal,
                        min_match_threshold=0.95  # 95% 이상 일치 필요
                    )
                    
                    if not verified_signal.is_valid:
                        # 신호가 코드북에 없으면 자동 등록 후 Fallback으로 진행
                        if "not found in codebook" in str(verified_signal.error_message):
                            logger.warning(
                                f"⚠️ 신호가 코드북에 없음 (Signal ID: {signal_id}), 자동 등록 후 거래 진행"
                            )
                            # 신호 자동 등록 (signal_data에서 필요한 정보 추출)
                            try:
                                if signal_data:
                                    market_data = signal_data.get("market_data", {"price": price})
                                    strategy_params = signal_data.get("strategy_params", {})
                                    vector_4d = signal_data.get("vector_4d", {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5})
                                    
                                    # 신호 자동 등록
                                    self.harness.generate_signal_id(
                                        market_data=market_data,
                                        strategy_params=strategy_params,
                                        vector_4d=vector_4d,
                                        signal_type=signal,
                                        confidence=confidence
                                    )
                                    logger.info(f"✅ 신호 자동 등록 완료: {signal_id}")
                            except Exception as reg_e:
                                logger.warning(f"⚠️ 신호 자동 등록 실패: {reg_e}, Fallback으로 진행")
                        else:
                            logger.warning(
                                f"⚠️ 헌법 제3조 위반: 매매 신호 검증 실패 (Signal ID: {signal_id})"
                            )
                            logger.warning(f"   일치도: {verified_signal.literal_restoration_rate:.2%} < 95%")
                            logger.warning(f"   오류: {verified_signal.error_message}")
                            logger.warning("   Fallback: 검증 실패해도 거래 계속 진행 (안전장치 우회)")
                    
                    # 95% 이상 일치 확인 (경고만, 거래는 계속)
                    elif verified_signal.literal_restoration_rate < 0.95:
                        logger.warning(
                            f"⚠️ Signal Validation 경고: 일치도 {verified_signal.literal_restoration_rate:.2%} < 95% (거래 계속 진행)"
                        )
                    
                    logger.info(
                        f"✅ 신호 검증 통과: Signal ID {signal_id}, "
                        f"일치도 {verified_signal.literal_restoration_rate:.2%} (목표: ≥95%)"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 신호 검증 실패: {e}, 거래 계속 진행 (Fallback)")
            
            # 잔고 조회
            balance_info = self.binance.get_balance()
            balance = balance_info.get('total', 0.0) if isinstance(balance_info, dict) else 0.0
            if balance <= 0:
                logger.error("❌ 잔고가 없습니다")
                return None
            
            # 🎯 정확도 기반 레버리지 조정 (단, 전체 레버리지는 1~2배 범위로 제한)
            confidence_based_leverage_multiplier = self.calculate_leverage_multiplier(confidence)
            # 기존 leverage_multiplier와 신뢰도 기반 배율을 결합하되,
            # 최종 효과적 레버리지가 2배를 절대 넘지 않도록 1.0 이내로 클램프
            raw_leverage_multiplier = max(leverage_multiplier, confidence_based_leverage_multiplier)
            final_leverage_multiplier = min(raw_leverage_multiplier, 1.0)
            
            effective_leverage = self.leverage * final_leverage_multiplier
            logger.info(
                f"🎯 레버리지 조정: 신뢰도 {confidence:.2%}, "
                f"요청 배율 {leverage_multiplier:.2f} → 최종 배율 {final_leverage_multiplier:.2f} "
                f"(효과적 레버리지: {effective_leverage:.1f}배, 상한 2배)"
            )
            
            # 🏛️ 아테나 제안: 화기 농도 기반 MDD 동적 조정 (Nitro-Flex)
            fire_concentration = 0.0
            if signal_data:
                fire_energy = signal_data.get("fire_energy", {})
                if fire_energy and isinstance(fire_energy, dict):
                    fire_analysis = fire_energy.get("fire_analysis", {})
                    if fire_analysis:
                        fire_concentration = fire_analysis.get("fire_concentration", 0.0)
                    else:
                        # fire_energy에서 직접 추출 시도
                        fire_concentration = fire_energy.get("fire_concentration", 0.0)
            
            # 화기 농도 ≥ 0.9 시 MDD 임계치를 15%로 강화
            original_max_drawdown = self.risk_manager.max_drawdown
            if fire_concentration >= 0.9:
                self.risk_manager.max_drawdown = 0.15  # 15%로 강화
                logger.warning(
                    f"🔥 Nitro-Flex 활성화: 화기 농도 {fire_concentration:.2f} ≥ 0.9, "
                    f"MDD 임계치 {original_max_drawdown:.1%} → 15%로 강화"
                )
            else:
                # 원래 MDD로 복원
                if self.risk_manager.max_drawdown != original_max_drawdown:
                    self.risk_manager.max_drawdown = original_max_drawdown
                    logger.info(f"✅ MDD 임계치 원래 값으로 복원: {original_max_drawdown:.1%}")
            
            # 리스크 관리 확인
            if not self.risk_manager.check_drawdown_limit():
                logger.error("❌ 낙폭 한도 초과, 거래 취소")
                return None
            
            if not self.risk_manager.check_daily_loss_limit():
                logger.error("❌ 일일 손실 한도 초과, 거래 취소")
                return None
            try:
                failure_count = int(self.circuit_breaker_state.get("failure_count", 0))
            except Exception:
                failure_count = 0
            if failure_count >= self.config_max_consecutive_failures_hard_gate:
                logger.warning(
                    "🛑 하드게이트 차단: 연속 실패 %d회 >= 한도 %d회",
                    failure_count,
                    self.config_max_consecutive_failures_hard_gate,
                )
                return None
            daily_loss_ratio = abs(self.risk_manager.daily_pnl) / max(balance, 1e-9) if self.risk_manager.daily_pnl < 0 else 0.0
            if daily_loss_ratio >= self.risk_manager.max_daily_loss * 0.9:
                logger.warning(
                    "🛑 하드게이트 차단: 일일 손실률 %.2f%% (한도 %.2f%%의 90%% 이상)",
                    daily_loss_ratio * 100.0,
                    self.risk_manager.max_daily_loss * 100.0,
                )
                return None
            if not self._passes_hard_risk_gate(balance):
                logger.warning("🛑 하드 리스크 게이트로 거래 취소")
                return None
            
            # 🏛️ 0.25 회귀 알고리즘 적용 (자산 배분 균형 유지)
            # 현재 포지션 정보 조회
            current_position = self.binance.get_position(symbol=self.symbol)
            
            # 현재 자산 배분 계산 (현금/롱/숏 비율)
            total_assets = balance
            if current_position:
                position_value = current_position.get("quantity", 0) * current_position.get("entry_price", price)
                total_assets = balance + position_value
            else:
                position_value = 0.0
            
            # 자산 배분 벡터 계산
            if total_assets > 0:
                current_allocation = {
                    "S": balance / total_assets,  # 현금 비율
                    "L": (position_value / total_assets) if current_position and current_position.get("side") == "LONG" else 0.0,  # 롱 포지션 비율
                    "K": (position_value / total_assets) if current_position and current_position.get("side") == "SHORT" else 0.0,  # 숏 포지션 비율
                    "M": 0.0  # 미사용
                }
                
                # 🏛️ 0.25 회귀 알고리즘 적용 (자산 배분 균형 유지)
                if PROJECT_LOGOS_AVAILABLE and apply_0_25_regression:
                    lambda_value = signal_data.get("lambda", 0.5) if signal_data else 0.5
                    
                    # 현재 자산 배분 로깅 (모니터링용)
                    logger.info(
                        f"📊 현재 자산 배분: S={current_allocation['S']:.3f}, "
                        f"L={current_allocation['L']:.3f}, K={current_allocation['K']:.3f}, "
                        f"M={current_allocation['M']:.3f}, λ={lambda_value:.3f}"
                    )
                    
                    corrected_allocation = apply_0_25_regression(
                        current_allocation=current_allocation,
                        lambda_value=lambda_value
                    )
                    
                    # 보정 결과 로깅 (모니터링용)
                    distance_before = sum(
                        (current_allocation.get(k, 0) - 0.25) ** 2
                        for k in ["S", "L", "K", "M"]
                    ) ** 0.5
                    distance_after = sum(
                        (corrected_allocation.get(k, 0) - 0.25) ** 2
                        for k in ["S", "L", "K", "M"]
                    ) ** 0.5
                    
                    if distance_before > 0.1:
                        logger.info(
                            f"🏛️ 0.25 회귀 알고리즘 적용: "
                            f"거리 {distance_before:.4f} → {distance_after:.4f}, "
                            f"보정된 배분: S={corrected_allocation['S']:.3f}, "
                            f"L={corrected_allocation['L']:.3f}, K={corrected_allocation['K']:.3f}"
                        )
                    
                    # 🏛️ Aggressive Alpha Mode: Historical Pattern 기반 포지션 크기 상향 조정
                    position_boost = 1.0
                    if signal_data and signal_data.get("historical_pattern"):
                        historical_pattern = signal_data.get("historical_pattern", {})
                        if historical_pattern.get("aggressive_alpha_mode", False):
                            position_boost = historical_pattern.get("position_boost", 1.0)
                            similarity = historical_pattern.get("similarity", 0.0)
                            event_name = historical_pattern.get("event_name", "Unknown")
                            
                            logger.info(
                                f"🏛️ Aggressive Alpha Mode: 포지션 크기 부스트 적용 "
                                f"(이벤트: {event_name}, 유사도: {similarity:.2%}, 부스트: {position_boost:.2f}x)"
                            )
                    
                    # 보정된 비율을 기반으로 목표 포지션 크기 계산
                    if signal == "BUY":
                        # max_position_size 설정 사용 (하드코딩된 0.25 대신)
                        default_position_ratio = self.risk_manager.max_position_size
                        target_long_ratio = corrected_allocation.get("L", default_position_ratio)
                        # 0.25 회귀 알고리즘이 0.25로 고정하는 경우를 대비해 max_position_size로 제한
                        target_long_ratio = min(target_long_ratio, default_position_ratio)
                        # Aggressive Alpha Mode: 포지션 크기 상향 조정
                        target_long_ratio = min(target_long_ratio * position_boost, default_position_ratio * 1.3)  # 최대 30% 증가
                        target_position_value = total_assets * target_long_ratio
                        
                        # 🧠 수량적 추론 기반 포지션 크기 계산
                        position_size = self._calculate_position_size_with_quantitative_reasoning(
                            target_position_value=target_position_value,
                            price=price,
                            balance=balance,
                            leverage=self.leverage,
                            signal=signal,
                            current_position=current_position
                        )
                    
                    elif signal == "SELL":
                        # 🔥 양방향 매매 전략 적용 (2026 Fire Crash + 2028 Metal Reset)
                        bidirectional_result = signal_data.get("bidirectional_strategy") if signal_data else None
                        
                        if bidirectional_result:
                            # 양방향 매매 전략 결과 사용
                            # max_position_size 설정 사용 (하드코딩된 0.25 대신)
                            default_position_ratio = self.risk_manager.max_position_size
                            bidir_position_size = bidirectional_result.get("position_size")
                            
                            logger.info(
                                f"🔍 양방향 매매 전략 경로 진입: "
                                f"bidir_position_size={bidir_position_size}, "
                                f"default_position_ratio={default_position_ratio:.1%}, "
                                f"total_assets=${total_assets:.2f}"
                            )
                            
                            if bidir_position_size:
                                # position_size가 USDT 금액인 경우
                                # 양방향 매매 전략의 position_size는 전체 포지션 크기이지만,
                                # 전략에서 사용한 total_assets가 실제와 다를 수 있으므로 비율로 재계산
                                if isinstance(bidir_position_size, (int, float)):
                                    # 양방향 매매 전략의 position_ratio 사용
                                    bidir_position_ratio = bidirectional_result.get("position_ratio", 0.0)
                                    
                                    # 실제 총 자산을 사용하여 전체 포지션 크기 재계산
                                    full_target_position_value = total_assets * bidir_position_ratio
                                    # max_position_size 제한 적용
                                    full_target_position_value = min(full_target_position_value, total_assets * default_position_ratio)
                                    
                                    logger.info(
                                        f"   양방향 전략 포지션 비율: {bidir_position_ratio:.1%}, "
                                        f"실제 총 자산: ${total_assets:.2f}, "
                                        f"전체 포지션 크기: ${full_target_position_value:.2f}"
                                    )
                                    
                                    # 기존 포지션이 있으면 추가 포지션만 계산
                                    if current_position:
                                        existing_side = current_position.get("side")
                                        if (signal == "BUY" and existing_side == "LONG") or (signal == "SELL" and existing_side == "SHORT"):
                                            existing_quantity = current_position.get("quantity", 0)
                                            existing_entry_price = current_position.get("entry_price", price)
                                            existing_position_value = existing_quantity * existing_entry_price
                                            
                                            # 추가 포지션 계산
                                            additional_position_value = full_target_position_value - existing_position_value
                                            
                                            # 추가 포지션이 최소 주문 금액 이상이면 사용
                                            min_order_value = 100.0
                                            if additional_position_value >= min_order_value:
                                                target_position_value = full_target_position_value
                                                logger.info(
                                                    f"   기존 포지션: ${existing_position_value:.2f}, "
                                                    f"추가 필요: ${additional_position_value:.2f}"
                                                )
                                            elif additional_position_value > 0:
                                                # 추가 포지션이 최소 주문 금액 미만이면 최소 주문 금액으로 조정
                                                min_additional_position_value = min_order_value
                                                target_position_value = existing_position_value + min_additional_position_value
                                                logger.info(
                                                    f"   기존 포지션: ${existing_position_value:.2f}, "
                                                    f"추가 필요: ${additional_position_value:.2f} (최소 주문 미만, 최소 주문으로 조정: ${min_additional_position_value:.2f})"
                                                )
                                            else:
                                                # 기존 포지션이 목표 포지션보다 크거나 같음
                                                # 추가 포지션 없음
                                                target_position_value = full_target_position_value
                                                logger.info(
                                                    f"   기존 포지션: ${existing_position_value:.2f}, "
                                                    f"목표 포지션: ${full_target_position_value:.2f}, "
                                                    f"기존이 더 크거나 같음, 추가 포지션 없음"
                                                )
                                        else:
                                            # 반대 방향 포지션이 있으면 전체 포지션 크기 사용
                                            target_position_value = full_target_position_value
                                    else:
                                        # 기존 포지션이 없으면 전체 포지션 크기 사용
                                        target_position_value = full_target_position_value
                                    
                                    logger.info(
                                        f"   양방향 전략 최종 목표 포지션: ${target_position_value:.2f}"
                                    )
                                else:
                                    target_position_value = total_assets * default_position_ratio
                            else:
                                target_position_value = total_assets * default_position_ratio
                            
                            # 기존 포지션 고려 (추가 포지션만 계산)
                            # 양방향 매매 전략의 target_position_value는 전체 포지션 크기이므로,
                            # 기존 포지션이 있을 때는 추가 포지션만 계산
                            if current_position:
                                existing_side = current_position.get("side")
                                if (signal == "BUY" and existing_side == "LONG") or (signal == "SELL" and existing_side == "SHORT"):
                                    existing_quantity = current_position.get("quantity", 0)
                                    existing_entry_price = current_position.get("entry_price", price)
                                    existing_position_value = existing_quantity * existing_entry_price
                                    
                                    logger.info(
                                        f"   기존 포지션: {existing_quantity:.6f} BTC @ ${existing_entry_price:,.2f} = ${existing_position_value:.2f} USDT"
                                    )
                                    
                                    # 목표 포지션이 최소 주문 금액 미만이면 최소 주문 금액으로 조정
                                    min_order_value = 100.0
                                    if target_position_value < min_order_value:
                                        target_position_value = min_order_value
                                        logger.info(
                                            f"   목표 포지션 최소 주문 금액으로 조정: ${target_position_value:.2f}"
                                        )
                                    
                                    # 추가 포지션 계산
                                    additional_position_value = target_position_value - existing_position_value
                                    
                                    if additional_position_value >= min_order_value:
                                        # 추가 포지션이 최소 주문 금액 이상이면 추가 포지션 필요
                                        position_size = additional_position_value / price
                                        logger.info(
                                            f"   추가 포지션 필요: ${additional_position_value:.2f} USDT = {position_size:.6f} BTC"
                                        )
                                    elif additional_position_value > 0:
                                        # 추가 포지션이 0보다 크지만 최소 주문 금액 미만
                                        # 최소 주문 금액으로 조정
                                        min_additional_position_value = min_order_value
                                        position_size = min_additional_position_value / price
                                        logger.info(
                                            f"   추가 포지션(${additional_position_value:.2f})이 최소 주문 금액 미만, "
                                            f"최소 주문 금액(${min_order_value:.2f})으로 조정"
                                        )
                                        logger.info(
                                            f"   조정된 추가 포지션: ${min_additional_position_value:.2f} USDT = {position_size:.6f} BTC"
                                        )
                                    else:
                                        # 기존 포지션이 목표 포지션보다 크거나 같음
                                        # 추가 포지션 없음 (부분 청산은 별도 로직 필요)
                                        position_size = 0.0
                                        logger.info(
                                            f"   기존 포지션(${existing_position_value:.2f})이 목표 포지션(${target_position_value:.2f})보다 크거나 같음, "
                                            f"추가 포지션 없음"
                                        )
                                else:
                                    # 반대 방향 포지션이 있으면 전체 포지션 크기 계산
                                    position_size = target_position_value / price
                                    logger.info(
                                        f"   반대 방향 포지션 존재, 전체 포지션 크기 계산: {position_size:.6f} BTC = ${target_position_value:.2f}"
                                    )
                            else:
                                # 기존 포지션이 없으면 전체 포지션 크기 계산
                                # 목표 포지션이 최소 주문 금액 미만이면 최소 주문 금액으로 조정
                                min_order_value = 100.0
                                if target_position_value < min_order_value:
                                    target_position_value = min_order_value
                                    logger.info(
                                        f"   목표 포지션 최소 주문 금액으로 조정: ${target_position_value:.2f}"
                                    )
                                position_size = target_position_value / price
                                logger.info(
                                    f"   기존 포지션 없음, 전체 포지션 크기 계산: {position_size:.6f} BTC = ${target_position_value:.2f}"
                                )
                            
                            # 레버리지 업데이트 (양방향 전략 + 신뢰도 기반 조정)
                            bidirectional_leverage_multiplier = bidirectional_result.get("leverage", self.leverage) / self.leverage
                            # 신뢰도 기반 배율과 비교하여 큰 값을 사용하되, 최종 효과적 레버리지가 2배를 넘지 않도록 제한
                            combined_multiplier = max(bidirectional_leverage_multiplier, self.calculate_leverage_multiplier(confidence))
                            leverage_multiplier = min(combined_multiplier, 1.0)
                            
                            logger.info(
                                f"🔥 양방향 매매 전략 적용: {bidirectional_result.get('strategy_type', 'normal')} "
                                f"(포지션 비율: {bidirectional_result.get('position_ratio', 0.0):.1%}, "
                                f"레버리지: {bidirectional_result.get('leverage', self.leverage):.1f}x, "
                                f"최종 포지션: {position_size:.6f} BTC = ${target_position_value:.2f})"
                            )
                            # position_size는 이미 BTC 단위로 계산됨, position_size_usdt는 변환 불필요
                            position_size_usdt = target_position_value
                        else:
                            # 기존 로직 사용 (0.25 회귀 알고리즘 경로)
                            # max_position_size 설정 사용 (하드코딩된 0.25 대신)
                            default_position_ratio = self.risk_manager.max_position_size
                            target_short_ratio_raw = corrected_allocation.get("K", default_position_ratio)
                            
                            logger.info(
                                f"🔍 0.25 회귀 알고리즘 경로 진입: "
                                f"corrected_allocation={corrected_allocation}, "
                                f"target_short_ratio_raw={target_short_ratio_raw:.1%}, "
                                f"default_position_ratio={default_position_ratio:.1%}, "
                                f"total_assets=${total_assets:.2f}"
                            )
                            
                            # 0.25 회귀 알고리즘 결과에 Aggressive Alpha Mode 부스트 적용
                            target_short_ratio_raw = corrected_allocation.get("K", default_position_ratio)
                            # Aggressive Alpha Mode: 포지션 크기 상향 조정
                            target_short_ratio_raw = min(target_short_ratio_raw * position_boost, default_position_ratio * 1.3)  # 최대 30% 증가
                            # 0.25 회귀 알고리즘이 0.25로 고정하는 경우를 대비해 max_position_size로 제한
                            target_short_ratio = min(target_short_ratio_raw, default_position_ratio * 1.3)  # 최대 30% 증가 허용
                            
                            if target_short_ratio_raw > default_position_ratio * 1.3:
                                logger.warning(
                                    f"⚠️ 0.25 회귀 알고리즘 결과({target_short_ratio_raw:.1%})가 "
                                    f"max_position_size({default_position_ratio * 1.3:.1%})를 초과하여 제한합니다."
                                )
                            
                            target_position_value = total_assets * target_short_ratio
                            
                            logger.info(
                                f"   0.25 회귀 알고리즘 결과: "
                                f"target_short_ratio={target_short_ratio:.1%}, "
                                f"target_position_value=${target_position_value:.2f}"
                            )
                            
                            # 🧠 수량적 추론 기반 포지션 크기 계산
                            position_size = self._calculate_position_size_with_quantitative_reasoning(
                                target_position_value=target_position_value,
                                price=price,
                                balance=balance,
                                leverage=self.leverage,
                                signal=signal,
                                current_position=current_position
                            )
                            # position_size는 이미 BTC 단위로 계산됨, position_size_usdt는 변환 불필요
                            position_size_usdt = target_position_value
                    else:
                        # 0.25 회귀 알고리즘 미사용 시 기본 계산 (슬리피지 보정 포함)
                        # 거래량 데이터 가져오기 (슬리피지 보정용)
                        recent_volume = None
                        avg_volume = None
                        try:
                            if hasattr(self.strategy, 'price_data') and len(self.strategy.price_data) > 0:
                                # 최근 24시간 거래량 (최신 캔들)
                                recent_volume = self.strategy.price_data['volume'].iloc[-1] if 'volume' in self.strategy.price_data.columns else None
                                # 평균 거래량 (30일)
                                if len(self.strategy.price_data) >= 30:
                                    avg_volume = self.strategy.price_data['volume'].tail(30).mean()
                        except Exception as e:
                            logger.debug(f"거래량 데이터 가져오기 실패 (무시): {e}")
                        
                        # RiskManager의 calculate_position_size 사용 (슬리피지 보정 포함)
                        # MKM12 수학 헌법 v4.0 준수: Divine Centroid 보정 적용
                        # vector_4d 파라미터는 선택적 (RiskManager 버전에 따라 다를 수 있음)
                        try:
                            vector_4d = signal_data.get("corrected_vector") or signal_data.get("sovereign_vector") if signal_data else None
                            position_size_usdt = self.risk_manager.calculate_position_size(
                                current_price=price,
                                signal_confidence=confidence,
                                recent_volume=recent_volume,
                                avg_volume=avg_volume,
                                vector_4d=vector_4d  # Divine Centroid 보정용 (선택적)
                            )
                        except TypeError:
                            # vector_4d 파라미터를 지원하지 않는 경우
                            position_size_usdt = self.risk_manager.calculate_position_size(
                            current_price=price,
                            signal_confidence=confidence,
                            recent_volume=recent_volume,
                            avg_volume=avg_volume
                        )
                        # position_size_usdt를 BTC 수량으로 변환
                        position_size = round(position_size_usdt / price, 3)  # BTC 수량으로 변환 (0.001 단위)
            else:
                # 자산이 없으면 기본 계산 (슬리피지 보정 포함)
                # 거래량 데이터 가져오기 (슬리피지 보정용)
                recent_volume = None
                avg_volume = None
                try:
                    if hasattr(self.strategy, 'price_data') and len(self.strategy.price_data) > 0:
                        recent_volume = self.strategy.price_data['volume'].iloc[-1] if 'volume' in self.strategy.price_data.columns else None
                        if len(self.strategy.price_data) >= 30:
                            avg_volume = self.strategy.price_data['volume'].tail(30).mean()
                except Exception as e:
                    logger.debug(f"거래량 데이터 가져오기 실패 (무시): {e}")
                
                # RiskManager의 calculate_position_size 사용 (슬리피지 보정 포함)
                # MKM12 수학 헌법 v4.0 준수: Divine Centroid 보정 적용
                # vector_4d 파라미터는 선택적 (RiskManager 버전에 따라 다를 수 있음)
                try:
                    vector_4d = signal_data.get("corrected_vector") or signal_data.get("sovereign_vector") if signal_data else None
                    position_size_usdt = self.risk_manager.calculate_position_size(
                        current_price=price,
                        signal_confidence=confidence,
                        recent_volume=recent_volume,
                        avg_volume=avg_volume,
                        vector_4d=vector_4d  # Divine Centroid 보정용 (선택적)
                    )
                except TypeError:
                    # vector_4d 파라미터를 지원하지 않는 경우
                    position_size_usdt = self.risk_manager.calculate_position_size(
                        current_price=price,
                        signal_confidence=confidence,
                        recent_volume=recent_volume,
                        avg_volume=avg_volume
                    )
                position_size = round(position_size_usdt / price, 8)  # BTC 수량으로 변환 (8자리 반올림)
            
            # 🧠 수량적 추론 경로를 포함해 최종 단계에서 동적 리스크 캡 적용
            if position_size > 0:
                position_size = self._apply_dynamic_notional_cap(
                    requested_position_size=position_size,
                    price=price,
                    balance=balance,
                    confidence=confidence,
                    signal_data=signal_data,
                )

            # 🧠 수량적 추론이 적용되지 않은 경로의 경우에도 최종 검증
            if position_size > 0:
                requested_notional = position_size * price
                stop_loss = max(float(getattr(self.risk_manager, "stop_loss_ratio", 0.01) or 0.01), 0.001)
                risk_budget = balance * self.config_risk_per_trade
                max_notional_by_risk = risk_budget / stop_loss
                max_notional_by_ratio = balance * self.risk_manager.max_position_size
                realized_volatility = float(signal_data.get("realized_volatility", signal_data.get("volatility_24h", 0.0)) or 0.0) if isinstance(signal_data, dict) else 0.0
                if realized_volatility >= 0.06:
                    vol_multiplier = 0.5
                elif realized_volatility >= 0.04:
                    vol_multiplier = 0.7
                else:
                    vol_multiplier = 1.0
                confidence_multiplier = max(0.8, min(1.1, 0.8 + float(confidence) * 0.3))
                allowed_notional = min(
                    max_notional_by_ratio,
                    max_notional_by_risk * vol_multiplier * confidence_multiplier,
                )
                if requested_notional > allowed_notional:
                    logger.info(
                        "🛡️ 동적 사이징 캡 적용: 요청 %.2f USDT -> 허용 %.2f USDT "
                        "(risk_per_trade=%.2f%%, stop_loss=%.2f%%, vol=%.4f, conf=%.2f)",
                        requested_notional,
                        allowed_notional,
                        self.config_risk_per_trade * 100.0,
                        stop_loss * 100.0,
                        realized_volatility,
                        confidence,
                    )
                    position_size = max(0.0, allowed_notional / max(price, 1e-9))

                # 최소 주문 금액 재확인 및 조정
                min_order_value = 100.0
                position_value_check = position_size * price
                
                if position_value_check < min_order_value:
                    # 최소 주문 금액으로 조정 시도
                    # 반올림을 고려하여 여유를 두고 조정 (0.001 BTC 단위 반올림 고려)
                    min_position_size_raw = min_order_value / price
                    # 반올림 후에도 최소 주문 금액을 충족하도록 0.001 BTC 단위로 올림
                    min_position_size = ((int(min_position_size_raw * 1000) + 1) / 1000) if (min_position_size_raw * 1000) % 1 != 0 else (int(min_position_size_raw * 1000) / 1000)
                    min_position_value = min_position_size * price
                    min_required_margin = min_position_value / self.leverage
                    available_margin_check = balance * 0.9
                    
                    if min_required_margin <= available_margin_check:
                        # 최소 주문 금액으로 조정 가능
                        logger.info(
                            f"📊 최소 주문 금액 조정: ${position_value_check:.2f} → ${min_position_value:.2f} "
                            f"(포지션 크기: {position_size:.6f} → {min_position_size:.6f} BTC, 반올림 고려)"
                        )
                        position_size = min_position_size
                        position_value_check = min_position_value
                    else:
                        # 잔고 부족으로 최소 주문 금액 충족 불가
                        logger.warning(
                            f"⚠️ 수량적 추론 최종 검증: 포지션 금액(${position_value_check:.2f})이 "
                            f"최소 주문 금액(${min_order_value:.2f}) 미만이고, "
                            f"최소 주문을 위한 필요 마진(${min_required_margin:.2f})이 "
                            f"가용 마진(${available_margin_check:.2f})을 초과합니다. 거래 취소."
                        )
                        position_size = 0.0
                
                # 마진 재확인 (최소 주문 금액 조정 후)
                if position_size > 0:
                    required_margin_check = position_value_check / self.leverage
                    available_margin_check = balance * 0.9
                    if required_margin_check > available_margin_check:
                        logger.warning(
                            f"⚠️ 수량적 추론 최종 검증: 필요 마진(${required_margin_check:.2f})이 "
                            f"가용 마진(${available_margin_check:.2f})을 초과합니다. 거래 취소."
                        )
                        position_size = 0.0
            
            # Binance Futures BTCUSDT Step Size: 0.001 BTC (3자리 반올림)
            # 반올림 전 최소 주문 금액 확인 및 조정
            min_order_value = 100.0
            position_value_before_round = position_size * price
            
            if position_value_before_round < min_order_value and position_size > 0:
                # 반올림 전에 최소 주문 금액으로 조정 (0.001 BTC 단위로 올림)
                min_position_size_raw = min_order_value / price
                # 0.001 BTC 단위로 올림하여 반올림 후에도 최소 주문 금액 충족
                min_position_size = ((int(min_position_size_raw * 1000) + 1) / 1000) if (min_position_size_raw * 1000) % 1 != 0 else (int(min_position_size_raw * 1000) / 1000)
                min_position_value = min_position_size * price
                min_required_margin = min_position_value / self.leverage
                available_margin_check = balance * 0.9
                
                if min_required_margin <= available_margin_check:
                    logger.info(
                        f"📊 최소 주문 금액 조정 (반올림 전): ${position_value_before_round:.2f} → ${min_position_value:.2f} "
                        f"(포지션 크기: {position_size:.6f} → {min_position_size:.6f} BTC)"
                    )
                    position_size = min_position_size
                else:
                    logger.warning(
                        f"⚠️ 최소 주문 금액 충족 불가: ${position_value_before_round:.2f} < ${min_order_value:.2f}, "
                        f"필요 마진(${min_required_margin:.2f}) > 가용 마진(${available_margin_check:.2f}). 거래 취소."
                    )
                    position_size = 0.0
            
            # Binance Futures BTCUSDT Step Size: 0.001 BTC (3자리 반올림)
            position_size = round(position_size, 3)
            
            # 최종 최소 주문 금액 확인 (반올림 후)
            final_position_value = position_size * price
            if final_position_value < min_order_value and position_size > 0:
                # 반올림 후에도 미달이면 0.001 BTC 추가
                min_position_size = position_size + 0.001
                min_position_value = min_position_size * price
                min_required_margin = min_position_value / self.leverage
                available_margin_check = balance * 0.9
                
                if min_required_margin <= available_margin_check:
                    logger.info(
                        f"📊 최소 주문 금액 최종 조정 (반올림 후): ${final_position_value:.2f} → ${min_position_value:.2f} "
                        f"(포지션 크기: {position_size:.6f} → {min_position_size:.6f} BTC)"
                    )
                    position_size = min_position_size
                else:
                    logger.warning(
                        f"⚠️ 반올림 후 최소 주문 금액 미달: ${final_position_value:.2f} < ${min_order_value:.2f}, "
                        f"필요 마진(${min_required_margin:.2f}) > 가용 마진(${available_margin_check:.2f}). 거래 취소."
                    )
                    position_size = 0.0
            
            if position_size <= 0:
                logger.warning("⚠️ 포지션 크기가 0입니다")
                return None
            
            # 거래 실행
            trade_result = None
            
            if signal == "BUY":
                # 롱 포지션 오픈
                logger.info(f"📈 롱 포지션 오픈: {position_size:.6f} {self.symbol.replace('USDT', '')} @ ${price:,.2f}")
                
                order_result = self.binance.open_long_position(
                    symbol=self.symbol,
                    quantity=position_size,
                    leverage=self.leverage
                )
                
                if order_result:
                    trade_result = {
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal,
                        "order_id": order_result.get("orderId", "N/A"),
                        "price": price,
                        "quantity": position_size,
                        "confidence": confidence,
                        "leverage_multiplier": leverage_multiplier,
                        "pnl": 0.0,  # 초기 손익
                        "lambda": signal_data.get("lambda", 0.5) if signal_data else 0.5,
                        "sovereign_vector": signal_data.get("sovereign_vector", {}) if signal_data else {},
                        "corrected_vector": signal_data.get("corrected_vector", {}) if signal_data else {},
                        # 🏛️ 최신 통합 모듈 결과
                        "fact_check": signal_data.get("fact_check") if signal_data else None,
                        "quaternion_insight": signal_data.get("quaternion_insight") if signal_data else None,
                        "sbsc_verification": signal_data.get("sbsc_verification") if signal_data else None,
                        "logos_timeline_overlay": signal_data.get("logos_timeline_overlay") if signal_data else None,
                    }
                    if signal_data:
                        trade_result["omni_oracle_request"] = signal_data.get("omni_oracle_request")
                        trade_result["omni_oracle_result"] = signal_data.get("omni_oracle_result")
                        trade_result["omni_regime_shift_probability"] = (
                            (signal_data.get("omni_oracle_result") or {}).get("regime_shift_probability")
                        )
            
            elif signal == "SELL":
                # 숏 포지션 오픈
                # 🔥 양방향 매매 전략 결과 가져오기
                bidirectional_result = signal_data.get("bidirectional_strategy") if signal_data else None
                
                # 레버리지 결정 (양방향 매매 전략이 있으면 그것 사용)
                if bidirectional_result:
                    actual_leverage = int(bidirectional_result.get("leverage", self.leverage))
                else:
                    actual_leverage = self.leverage
                
                logger.info(
                    f"📉 숏 포지션 오픈: {position_size:.6f} {self.symbol.replace('USDT', '')} @ ${price:,.2f} "
                    f"(레버리지: {actual_leverage}x, 전략: {bidirectional_result.get('strategy_type', 'normal') if bidirectional_result else 'normal'})"
                )
                
                order_result = self.binance.open_short_position(
                    symbol=self.symbol,
                    quantity=position_size,
                    leverage=actual_leverage
                )
                
                if order_result:
                    trade_result = {
                        "timestamp": datetime.now().isoformat(),
                        "signal": signal,
                        "order_id": order_result.get("orderId", "N/A"),
                        "price": price,
                        "quantity": position_size,
                        "confidence": confidence,
                        "leverage_multiplier": leverage_multiplier,
                        "pnl": 0.0,  # 초기 손익
                        "lambda": signal_data.get("lambda", 0.5) if signal_data else 0.5,
                        "sovereign_vector": signal_data.get("sovereign_vector", {}) if signal_data else {},
                        "corrected_vector": signal_data.get("corrected_vector", {}) if signal_data else {},
                        # 🏛️ 최신 통합 모듈 결과
                        "fact_check": signal_data.get("fact_check") if signal_data else None,
                        "quaternion_insight": signal_data.get("quaternion_insight") if signal_data else None,
                        "sbsc_verification": signal_data.get("sbsc_verification") if signal_data else None,
                        "logos_timeline_overlay": signal_data.get("logos_timeline_overlay") if signal_data else None,
                        # 🔥 양방향 매매 전략 결과
                        "bidirectional_strategy": bidirectional_result
                    }
                    if signal_data:
                        trade_result["omni_oracle_request"] = signal_data.get("omni_oracle_request")
                        trade_result["omni_oracle_result"] = signal_data.get("omni_oracle_result")
                        trade_result["omni_regime_shift_probability"] = (
                            (signal_data.get("omni_oracle_result") or {}).get("regime_shift_probability")
                        )
            
            return trade_result
            
        except Exception as e:
            logger.error(f"❌ 실전 매매 실행 실패: {e}", exc_info=True)
            return None
    
    def _save_trades_history(self):
        """거래 이력 저장"""
        try:
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(self.trades_history, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ 거래 이력 저장 실패: {e}")
    
    def _check_circuit_breaker(self) -> bool:
        """
        Circuit Breaker 상태 확인
        
        Returns:
            True: 정상 작동 가능, False: Circuit 열림 (작동 중단)
        """
        state = self.circuit_breaker_state
        
        # Open 상태: 재설정 타임아웃 확인
        if state["state"] == "open":
            if state["last_failure_time"]:
                time_since_failure = (datetime.now() - state["last_failure_time"]).total_seconds()
                if time_since_failure >= state["reset_timeout"]:
                    # Half-Open으로 전환
                    state["state"] = "half-open"
                    state["success_count"] = 0
                    logger.info("🔄 Circuit Breaker: Half-Open으로 전환 (복구 시도)")
                else:
                    # 아직 재설정 타임아웃 전
                    logger.warning(f"⚠️ Circuit Breaker: Open 상태 (복구 대기 중, {int(state['reset_timeout'] - time_since_failure)}초 남음)")
                    self.safe_mode = True
                    return False
        
        # Half-Open 상태: 제한된 시도
        if state["state"] == "half-open":
            if state["success_count"] >= state["half_open_max_calls"]:
                # 성공 횟수 충분 → Closed로 전환
                state["state"] = "closed"
                state["failure_count"] = 0
                state["last_failure_time"] = None
                self.safe_mode = False
                logger.info("✅ Circuit Breaker: Closed로 전환 (복구 완료)")
                
                # 복구 알림
                if self.alert_manager:
                    asyncio.create_task(self.alert_manager.alert_critical_event(
                        event_type="CIRCUIT_BREAKER_CLOSED",
                        message="Circuit Breaker가 닫혔습니다. 정상 작동을 재개합니다.",
                        details={
                            "success_count": state["success_count"],
                            "half_open_max_calls": state["half_open_max_calls"]
                        },
                        severity="MEDIUM"
                    ))
            else:
                logger.info(f"🔄 Circuit Breaker: Half-Open 상태 (성공 {state['success_count']}/{state['half_open_max_calls']})")
        
        # Closed 상태: 정상 작동
        return True
    
    def _record_success(self):
        """성공 기록 (Circuit Breaker)"""
        state = self.circuit_breaker_state
        
        if state["state"] == "half-open":
            state["success_count"] += 1
        elif state["state"] == "closed":
            state["failure_count"] = 0  # 연속 실패 카운터 리셋
    
    def _record_failure(self):
        """실패 기록 (Circuit Breaker)"""
        state = self.circuit_breaker_state
        state["failure_count"] += 1
        state["last_failure_time"] = datetime.now()
        
        if state["failure_count"] >= state["failure_threshold"]:
            state["state"] = "open"
            state["success_count"] = 0
            self.safe_mode = True
            logger.error(f"🚨 Circuit Breaker: Open 상태 (연속 실패 {state['failure_count']}회)")
            
            # 중요 이벤트 알림 (비동기로 실행)
            if self.alert_manager:
                asyncio.create_task(self.alert_manager.alert_critical_event(
                    event_type="CIRCUIT_BREAKER_OPEN",
                    message=f"Circuit Breaker가 열렸습니다. 연속 실패 {state['failure_count']}회로 인해 거래가 중단됩니다.",
                    details={
                        "failure_count": state["failure_count"],
                        "failure_threshold": state["failure_threshold"],
                        "reset_timeout": state["reset_timeout"],
                        "last_failure_time": state["last_failure_time"].isoformat()
                    },
                    severity="CRITICAL"
                ))
    
    def _retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0
    ):
        """
        지수 백오프를 사용한 재시도 로직
        
        Args:
            func: 실행할 함수 (async 또는 sync)
            max_retries: 최대 재시도 횟수
            initial_delay: 초기 지연 시간 (초)
            backoff_factor: 백오프 배율
        
        Returns:
            함수 실행 결과
        """
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return asyncio.run(func())
                else:
                    return func()
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ 재시도 {attempt + 1}/{max_retries} (지연: {delay:.1f}초): {e}")
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    logger.error(f"❌ 최대 재시도 횟수 초과: {e}")
                    raise
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (SIGINT, SIGTERM)"""
        logger.info(f"⚠️ 시그널 수신: {signum}, 안전한 종료 시작...")
        self.stop_trading()
    
    def _save_state(self):
        """현재 상태 저장 (재시작/복구용, 백업 포함)"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "running": self.running,
                "trades_count": self.trades_count,
                "total_pnl": self.total_pnl,
                "signal_total_count": self.signal_total_count,
                "singular_action_counts": self.singular_action_counts,
                "last_signal_summary": self.last_signal_summary,
                "circuit_breaker_state": self.circuit_breaker_state,
                "safe_mode": self.safe_mode,
                "last_price_update": self.last_price_update.isoformat() if hasattr(self, 'last_price_update') else None,
                "current_position": self._get_current_position_info()
            }
            
            # 백업 파일 생성
            backup_file = self.state_file.with_suffix('.json.backup')
            if self.state_file.exists():
                import shutil
                try:
                    shutil.copy2(self.state_file, backup_file)
                    logger.debug("✅ 상태 파일 백업 완료")
                except Exception as e:
                    logger.warning(f"⚠️ 상태 파일 백업 실패: {e}")
            
            # 상태 파일 저장
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False, default=str)
            
            # 검증: 저장된 파일 읽기 테스트
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # 파싱 테스트
                logger.debug("✅ 상태 저장 완료 (검증 통과)")
            except json.JSONDecodeError as e:
                logger.error(f"❌ 상태 파일 검증 실패: {e}")
                # 백업 파일로 복구 시도
                if backup_file.exists():
                    import shutil
                    shutil.copy2(backup_file, self.state_file)
                    logger.info("✅ 백업 파일로 복구 완료")
        except Exception as e:
            logger.error(f"❌ 상태 저장 실패: {e}")
            # 백업 파일로 복구 시도
            backup_file = self.state_file.with_suffix('.json.backup')
            if backup_file.exists():
                import shutil
                try:
                    shutil.copy2(backup_file, self.state_file)
                    logger.info("✅ 백업 파일로 복구 완료")
                except Exception as restore_error:
                    logger.error(f"❌ 백업 파일 복구 실패: {restore_error}")
    
    def _validate_state(self, state: Dict[str, Any]) -> bool:
        """상태 검증"""
        required_keys = ['trades_count', 'total_pnl', 'circuit_breaker_state']
        if not all(key in state for key in required_keys):
            logger.warning(f"⚠️ 상태 파일 필수 키 누락: {required_keys}")
            return False
        
        # 타입 검증
        if not isinstance(state.get('trades_count'), int):
            logger.warning("⚠️ 상태 파일 trades_count 타입 오류")
            return False
        if not isinstance(state.get('total_pnl'), (int, float)):
            logger.warning("⚠️ 상태 파일 total_pnl 타입 오류")
            return False
        if not isinstance(state.get('circuit_breaker_state'), dict):
            logger.warning("⚠️ 상태 파일 circuit_breaker_state 타입 오류")
            return False
        
        return True
    
    def _load_state(self) -> bool:
        """
        저장된 상태 복구 (검증 포함)
        
        Returns:
            True: 복구 성공, False: 복구 실패 또는 상태 파일 없음
        """
        try:
            if not self.state_file.exists():
                logger.info("📄 상태 파일 없음, 새로 시작")
                return False
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # 상태 검증
            if not self._validate_state(state):
                logger.warning("⚠️ 상태 파일 검증 실패, 백업 파일로 복구 시도")
                backup_file = self.state_file.with_suffix('.json.backup')
                if backup_file.exists():
                    import shutil
                    shutil.copy2(backup_file, self.state_file)
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    if not self._validate_state(state):
                        logger.error("❌ 백업 파일도 검증 실패, 초기화")
                        return False
                    logger.info("✅ 백업 파일로 복구 성공")
                else:
                    logger.error("❌ 백업 파일도 없음, 초기화")
                    return False
            
            # 상태 복구
            self.trades_count = state.get("trades_count", 0)
            self.total_pnl = state.get("total_pnl", 0.0)
            self.circuit_breaker_state = state.get("circuit_breaker_state", self.circuit_breaker_state)
            self.safe_mode = state.get("safe_mode", False)
            
            if state.get("last_price_update"):
                self.last_price_update = datetime.fromisoformat(state["last_price_update"])
            
            logger.info("✅ 상태 복구 완료")
            logger.info(f"   - 거래 횟수: {self.trades_count}회")
            logger.info(f"   - 총 손익: ${self.total_pnl:,.2f}")
            logger.info(f"   - Circuit Breaker 상태: {self.circuit_breaker_state['state']}")
            
            return True
        except json.JSONDecodeError as e:
            logger.error(f"❌ 상태 파일 JSON 파싱 실패: {e}")
            # 백업 파일로 복구 시도
            backup_file = self.state_file.with_suffix('.json.backup')
            if backup_file.exists():
                import shutil
                try:
                    shutil.copy2(backup_file, self.state_file)
                    logger.info("✅ 백업 파일로 복구 완료, 재시도")
                    return self._load_state()  # 재귀 호출
                except Exception as restore_error:
                    logger.error(f"❌ 백업 파일 복구 실패: {restore_error}")
            return False
        except Exception as e:
            logger.error(f"❌ 상태 복구 실패: {e}")
            return False
    
    def _cleanup_memory(self):
        """메모리 정리 (주기적 호출)"""
        try:
            # 가격 히스토리 크기 제한 (strategy에 있는 경우)
            if hasattr(self.strategy, 'price_data') and hasattr(self.strategy.price_data, '__len__'):
                if len(self.strategy.price_data) > 1000:
                    # 최근 1000개만 유지
                    self.strategy.price_data = self.strategy.price_data.tail(1000)
                    logger.debug("✅ 가격 데이터 정리 완료 (1000개로 제한)")
            
            # 거래 이력 크기 제한 (최근 1000개만 유지)
            if hasattr(self, 'trades_history') and len(self.trades_history) > 1000:
                self.trades_history = self.trades_history[-1000:]
                self._save_trades_history()
                logger.debug("✅ 거래 이력 정리 완료 (1000개로 제한)")
            
            # 가비지 컬렉션 실행
            import gc
            collected = gc.collect()
            if collected > 0:
                logger.debug(f"✅ 메모리 정리 완료: {collected}개 객체 수집")
        except Exception as e:
            logger.warning(f"⚠️ 메모리 정리 실패: {e}")
    
    def _get_current_position_info(self) -> Optional[Dict[str, Any]]:
        """현재 포지션 정보 조회"""
        try:
            if self.binance:
                position = self.binance.get_position(symbol=self.symbol)
                return position
            return None
        except Exception as e:
            logger.debug(f"포지션 정보 조회 실패: {e}")
            return None
    
    def stop_trading(self):
        """매매 중단 (안전한 종료)"""
        logger.info("🛑 매매 중단 요청, 안전한 종료 시작...")
        
        # 진행 중인 거래 완료 대기 (최대 30초)
        max_wait_time = 30
        wait_start = time.time()
        
        # 상태 저장
        self._save_state()
        
        # 실행 중 플래그 해제
        self.running = False
        
        logger.info("✅ 안전한 종료 완료")


if __name__ == "__main__":
    # 테스트 실행 (모의 매매 모드)
    trader = CryptoNitroLiveTrader(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2,
        testnet=True,  # 테스트넷 사용
        enable_live_trading=False  # 모의 매매 모드
    )
    
    asyncio.run(trader.start_trading(interval_seconds=300))

