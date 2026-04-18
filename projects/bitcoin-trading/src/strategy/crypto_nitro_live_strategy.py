#!/usr/bin/env python3
"""
Crypto-Nitro v1.6 실전 매매 전략

가상 레버리지 기반 실전 매매 전략
- Crypto-Nitro v1.6 엔진 통합
- 거대한 줄기 추세 필터 통합
- 가상 레버리지 자동 조절
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime
import pandas as pd
import numpy as np
import logging
import yaml

# 로깅 설정 (최우선)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 경로 설정
# __file__: projects/bitcoin-trading/src/strategy/crypto_nitro_live_strategy.py
# workspace root: strategy -> src -> bitcoin-trading -> projects -> repo root (5 parents)
current_file = Path(__file__).resolve()
workspace_root = current_file.parents[4]
if not (workspace_root / "scripts").is_dir():
    _alt = os.getenv("WORKSPACE_ROOT") or os.getenv("MKM_WORKSPACE_ROOT")
    if _alt:
        workspace_root = Path(_alt).expanduser().resolve()

sys.path.insert(0, str(workspace_root))
scripts_path = workspace_root / "scripts"
if scripts_path.exists():
    sys.path.insert(0, str(scripts_path))


def _resolve_state_id_with_source(signal_data: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """Resolve a normalized state_id with deterministic source priority.

    SSOT source priority:
    1) risk_assessment.myeongni_state_id
    2) signal_data.state_id
    3) risk_assessment.state_id
    4) risk_assessment.jema12_trinity.myeongni_state_id
    5) risk_assessment.jema12_trinity.state_id
    """

    if not isinstance(signal_data, dict):
        return None, "none"

    risk_assessment = signal_data.get("risk_assessment", {})
    if not isinstance(risk_assessment, dict):
        risk_assessment = {}
    trinity_meta = risk_assessment.get("jema12_trinity", {})
    if not isinstance(trinity_meta, dict):
        trinity_meta = {}

    candidates = [
        ("risk_assessment.myeongni_state_id", risk_assessment.get("myeongni_state_id")),
        ("signal_data.state_id", signal_data.get("state_id")),
        ("risk_assessment.state_id", risk_assessment.get("state_id")),
        ("risk_assessment.jema12_trinity.myeongni_state_id", trinity_meta.get("myeongni_state_id")),
        ("risk_assessment.jema12_trinity.state_id", trinity_meta.get("state_id")),
    ]
    for source, value in candidates:
        try:
            if value is None:
                continue
            sid = int(value)
            if 1 <= sid <= 16:
                return sid, source
        except (TypeError, ValueError):
            continue
    return None, "none"


def _state_provenance_from_signal(signal_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Optional ``source_track`` for dual_regime bulkhead (Track B suppresses state clamp)."""
    if not isinstance(signal_data, dict):
        return None
    st = signal_data.get("source_track")
    if st is None:
        ra = signal_data.get("risk_assessment")
        if isinstance(ra, dict):
            st = ra.get("source_track")
    if st is None:
        return None
    return {"source_track": st}


# BTC-6 Regime Fusion adapter (risk multiplier skeleton, always-neutral 1.0 for now)
try:
    from src.integration.btc6_regime_fusion_adapter import get_btc6_risk_multiplier
    BTC6_ADAPTER_AVAILABLE = True
except ImportError:
    get_btc6_risk_multiplier = None  # type: ignore[assignment]
    BTC6_ADAPTER_AVAILABLE = False
    logger.warning("⚠️ BTC-6 Regime Fusion adapter를 import할 수 없습니다. 중립 계수 1.0을 사용합니다.")

# Dual Regime AND-condition API (성경 레짐 ∧ 실물 피처 결합용)
try:
    from src.integration.dual_regime_api import (
        evaluate_dual_regime_and_market_shock,
        DualRegimeContext,
    )
    DUAL_REGIME_API_AVAILABLE = True
except ImportError:
    evaluate_dual_regime_and_market_shock = None  # type: ignore[assignment]
    DualRegimeContext = None  # type: ignore[assignment]
    DUAL_REGIME_API_AVAILABLE = False
    logger.info("ℹ️ Dual Regime API를 import할 수 없습니다. 듀얼 레짐 AND 조건은 비활성화됩니다.")

# 🧠 TimeXer-Exog 모델 (시계열 + 외생 변수 예측용, Phase B 스켈레톤)
TIMEXER_EXOG_AVAILABLE = False
TimeXerExogModel = None  # type: ignore[assignment]
TimeXerExogConfig = None  # type: ignore[assignment]
try:
    from src.models.timexer_exog_model import TimeXerExogModel, TimeXerExogConfig

    TIMEXER_EXOG_AVAILABLE = True
    logger.info("✅ TimeXer-Exog 모델 스켈레톤 로드 완료")
except ImportError:
    TIMEXER_EXOG_AVAILABLE = False
    logger.info("ℹ️ TimeXer-Exog 모델 스켈레톤을 찾을 수 없습니다. 기존 전략만 사용합니다.")

# 🏛️ 최신 통합 모듈 import
try:
    from src.analysis.phase_resonance_fact_check import PhaseResonanceFactChecker
    from src.analysis.quaternion_finance_analyzer import QuaternionFinanceAnalyzer
    from src.analysis.sbsc_strategy_verifier import SBSCStrategyVerifier
    LATEST_MODULES_AVAILABLE = True
except ImportError:
    LATEST_MODULES_AVAILABLE = False
    PhaseResonanceFactChecker = None
    QuaternionFinanceAnalyzer = None
    SBSCStrategyVerifier = None
    logger.warning("⚠️ 최신 통합 모듈을 import할 수 없습니다.")

# 🏛️ trading_wisdom RAG/conditioning 참조 (B3)
try:
    from src.context.trading_wisdom_loader import get_cited_trading_wisdom
    TRADING_WISDOM_LOADER_AVAILABLE = True
except ImportError:
    get_cited_trading_wisdom = None
    TRADING_WISDOM_LOADER_AVAILABLE = False

# regime_strategy_routing: 횡보장 시 Mean Reversion 허용 (TRANSITION/UNKNOWN)
try:
    from .regime_strategy_routing import use_mean_reversion
except ImportError:
    use_mean_reversion = None  # type: ignore[assignment,misc]

# 🔥 화기운 감지 모듈 import
try:
    from src.analysis.phase_space_nowcaster import PhaseSpaceNowcaster
    from precision_improvement_filter import PrecisionImprovementFilter
    FIRE_ENERGY_AVAILABLE = True
except ImportError:
    try:
        # scripts 경로에서 import 시도
        import sys
        scripts_path = workspace_root / "scripts"
        if scripts_path.exists():
            sys.path.insert(0, str(scripts_path))
        from precision_improvement_filter import PrecisionImprovementFilter
        from src.analysis.phase_space_nowcaster import PhaseSpaceNowcaster
        FIRE_ENERGY_AVAILABLE = True
    except ImportError:
        FIRE_ENERGY_AVAILABLE = False
        PhaseSpaceNowcaster = None
        PrecisionImprovementFilter = None
        logger.warning("⚠️ 화기운 감지 모듈을 import할 수 없습니다.")

# 🔥 양방향 매매 전략 모듈 import
BIDIRECTIONAL_STRATEGY_AVAILABLE = False
try:
    from .bidirectional_fire_metal_strategy import BidirectionalFireMetalStrategy
    BIDIRECTIONAL_STRATEGY_AVAILABLE = True
except ImportError:
    BIDIRECTIONAL_STRATEGY_AVAILABLE = False
    BidirectionalFireMetalStrategy = None

# 🏛️ JEMA-12 Trinity: LeadingApocalypseIndex (명리 + 성경 주기 통합)
try:
    from tools.core.leading_apocalypse_index import LeadingApocalypseIndex
    LAI_AVAILABLE = True
except ImportError:
    LAI_AVAILABLE = False
    LeadingApocalypseIndex = None

# 🏛️ Bitcoin 4D Mapper / Historical Pattern: lazy import (캘리브 모드에서 무거운 로드 방지)
BITCOIN_4D_MAPPER_AVAILABLE = False
Bitcoin4DMapper = None  # type: ignore[assignment]
HISTORICAL_PATTERN_AVAILABLE = False
HistoricalPatternAnalyzer = None  # type: ignore[assignment]

# 🏛️ ProphecyStack 통합 (비트코인 통일장 레짐 뷰)
try:
    from tools.prophecy.prophecy_stack import ProphecyStack
    PROPHECY_STACK_AVAILABLE = True
except ImportError:
    ProphecyStack = None  # type: ignore[assignment]
    PROPHECY_STACK_AVAILABLE = False

# 🏛️ P1→P4 교정 레이어 (신뢰도 캘리브레이션 + 4D 평형 진단)
try:
    from src.analysis.p1_p4_calibration import calibrate_confidence, analyze_equilibrium
    P1_P4_CALIBRATION_AVAILABLE = True
except ImportError:
    try:
        from ..analysis.p1_p4_calibration import calibrate_confidence, analyze_equilibrium
        P1_P4_CALIBRATION_AVAILABLE = True
    except ImportError:
        calibrate_confidence = None  # type: ignore[assignment]
        analyze_equilibrium = None  # type: ignore[assignment]
        P1_P4_CALIBRATION_AVAILABLE = False

# 🏛️ 글로벌 유동성 피처 엔진 (Exogenous Features 준비용)
try:
    from src.analysis.global_liquidity_feature_engine import GlobalLiquidityFeatureEngine
    GLOBAL_LIQUIDITY_FEATURE_ENGINE_AVAILABLE = True
except ImportError:
    try:
        from ..analysis.global_liquidity_feature_engine import GlobalLiquidityFeatureEngine
        GLOBAL_LIQUIDITY_FEATURE_ENGINE_AVAILABLE = True
    except ImportError:
        GlobalLiquidityFeatureEngine = None  # type: ignore[assignment]
        GLOBAL_LIQUIDITY_FEATURE_ENGINE_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 시장 국면 탐지 시스템 import
try:
    from ..analysis.market_regime_detector import MarketRegimeDetector
    from ..analysis.regime_feature_engine import RegimeFeatureEngine
    REGIME_DETECTION_AVAILABLE = True
    logger.info("✅ 시장 국면 탐지 시스템 로드 완료")
except ImportError:
    try:
        from src.analysis.market_regime_detector import MarketRegimeDetector
        from src.analysis.regime_feature_engine import RegimeFeatureEngine
        REGIME_DETECTION_AVAILABLE = True
        logger.info("✅ 시장 국면 탐지 시스템 로드 완료 (상대 경로)")
    except ImportError:
        REGIME_DETECTION_AVAILABLE = False
        MarketRegimeDetector = None
        RegimeFeatureEngine = None
        logger.warning("⚠️ 시장 국면 탐지 시스템을 import할 수 없습니다.")

# Crypto-Nitro 엔진 import
CRYPTO_NITRO_AVAILABLE = False
CryptoNitroBacktest = None
GreatTrunkTrendFilter = None

# PMI-Nitro 엔진 import
PMI_NITRO_AVAILABLE = False
PMINitroEngine = None
try:
    from ..strategy.pmi_nitro_engine import PMINitroEngine
    PMI_NITRO_AVAILABLE = True
    logger.info("✅ PMI-Nitro 엔진 로드 완료")
except ImportError:
    try:
        from strategy.pmi_nitro_engine import PMINitroEngine
        PMI_NITRO_AVAILABLE = True
        logger.info("✅ PMI-Nitro 엔진 로드 완료 (상대 경로)")
    except ImportError:
        logger.warning("⚠️ PMI-Nitro 엔진을 import할 수 없습니다. PMI 기능 제한")

# Crypto-Nitro / GreatTrunk 각각 독립 로드 (한쪽만 있어도 동작)
CryptoNitroBacktest = None
GreatTrunkTrendFilter = None
CRYPTO_NITRO_AVAILABLE = False

# 1) Crypto-Nitro 엔진 로드
try:
    from crypto_nitro_backtest_v1 import CryptoNitroBacktest
    CRYPTO_NITRO_AVAILABLE = True
    logger.info("✅ Crypto-Nitro 엔진 로드 완료 (일반 import)")
except ImportError:
    try:
        from scripts.crypto_nitro_backtest_v1 import CryptoNitroBacktest
        CRYPTO_NITRO_AVAILABLE = True
        logger.info("✅ Crypto-Nitro 엔진 로드 완료 (scripts. 모듈)")
    except ImportError:
        crypto_nitro_path = scripts_path / "crypto_nitro_backtest_v1.py"
        if crypto_nitro_path.exists():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("crypto_nitro_backtest_v1", crypto_nitro_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                CryptoNitroBacktest = mod.CryptoNitroBacktest
                CRYPTO_NITRO_AVAILABLE = True
                logger.info("✅ Crypto-Nitro 엔진 로드 완료 (직접 파일 import)")
            except Exception as e:
                logger.warning(f"⚠️ Crypto-Nitro 엔진 로드 실패: {e}")
        else:
            logger.debug("   crypto_nitro_backtest_v1.py 없음, Crypto-Nitro 비활성화")

# 2) 거대한 줄기 필터 로드 (Crypto-Nitro 없어도 사용 가능)
try:
    from great_trunk_trend_filter import GreatTrunkTrendFilter
except ImportError:
    try:
        from scripts.great_trunk_trend_filter import GreatTrunkTrendFilter
    except ImportError:
        great_trunk_path = scripts_path / "great_trunk_trend_filter.py"
        if great_trunk_path.exists():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("great_trunk_trend_filter", great_trunk_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                GreatTrunkTrendFilter = mod.GreatTrunkTrendFilter
            except Exception as e:
                logger.warning(f"⚠️ 거대한 줄기 필터 로드 실패: {e}")
                GreatTrunkTrendFilter = None
        else:
            GreatTrunkTrendFilter = None


class CryptoNitroLiveStrategy:
    """
    Crypto-Nitro v1.6 실전 매매 전략
    
    핵심 기능:
    - Crypto-Nitro v1.6 엔진 통합
    - 거대한 줄기 추세 필터 통합
    - 가상 레버리지 자동 조절
    - 실시간 신호 생성
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        use_great_trunk_filter: bool = True,
        binance_client: Optional[Any] = None,  # BinanceFuturesClient (Optional, 가격 데이터 수집 및 포지션 조회용)
        backtest_calibration: bool = False,  # True: 4D/PhaseSpace/Historical/Harness 스킵(캘리브레이션용 경량)
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 기본 레버리지 (물리적 레버리지, 항상 2배로 고정)
            use_great_trunk_filter: 거대한 줄기 추세 필터 사용 여부
            binance_client: Binance API 클라이언트 (Optional, 가격 데이터 수집용)
            backtest_calibration: 백테스트 캘리브레이션용 경량 모드 (Bitcoin4DMapper/PhaseSpace/Harness/Historical 스킵)
        """
        self.backtest_calibration = backtest_calibration
        self._logos_timeline_cache: Optional[Dict[str, Any]] = None
        self._logos_timeline_cache_mtime_ns: Optional[int] = None
        self._logos_timeline_path = (
            workspace_root
            / "reports"
            / "constitution"
            / "btrack_pilot"
            / "logos_timeline_anchor_v1_latest.json"
        )
        self._logos_timeline_calibration_path = (
            workspace_root
            / "reports"
            / "constitution"
            / "btrack_pilot"
            / "logos_timeline_tradition_calibration_latest.json"
        )
        self._logos_timeline_calibration_cache: Optional[Dict[str, Any]] = None
        self._logos_timeline_calibration_cache_mtime_ns: Optional[int] = None
        self._logos_timeline_tradition = str(
            os.getenv("LOGOS_TIMELINE_TRADITION", "harmonized")
        ).strip().lower()
        if self._logos_timeline_tradition not in ("harmonized", "mt", "lxx"):
            self._logos_timeline_tradition = "harmonized"
        # Crypto-Nitro 엔진이 없어도 작동하도록 선택적 처리
        # 주의: CryptoNitroBacktest는 모듈 레벨 변수이므로 로컬 변수로 재할당하지 않음
        if not CRYPTO_NITRO_AVAILABLE:
            logger.warning("⚠️ Crypto-Nitro 엔진을 import할 수 없습니다. 기본 전략으로 Fallback합니다.")
        
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.use_great_trunk_filter = use_great_trunk_filter and CRYPTO_NITRO_AVAILABLE  # Crypto-Nitro 없으면 필터 비활성화
        self.binance_client = binance_client
        # 비트코인 통합 통일장 레짐 뷰 (선택적, 캘리브레이션 모드에서는 스킵)
        self.prophecy_stack: Optional[Any] = None
        if not self.backtest_calibration and PROPHECY_STACK_AVAILABLE and ProphecyStack is not None:
            try:
                self.prophecy_stack = ProphecyStack()
                logger.info("✅ ProphecyStack 초기화 완료 (BTC 통일장 레짐 뷰 사용 가능)")
            except Exception as e:
                logger.warning(f"⚠️ ProphecyStack 초기화 실패: {e}")
        
        # 설정 파일 로드 (YAML)
        self.config = self._load_trading_config()
        
        # 설정 파일에서 파라미터 추출
        strategy_config = self.config.get("strategy", {})
        risk_config = self.config.get("risk_management", {})
        
        self.min_confidence = strategy_config.get("min_confidence", 0.6)
        self.min_consecutive_signals = strategy_config.get("min_consecutive_signals", 2)
        # 운영 기본값 고정 옵션: True/False면 레짐 판단 대신 강제, None이면 기존 동적 로직 사용
        self.force_use_mean_reversion = strategy_config.get("force_use_mean_reversion", None)
        self.max_position_size = risk_config.get("max_position_size", 0.3)
        self.max_drawdown = risk_config.get("max_drawdown", 0.22)
        self.risk_multiplier_min = float(risk_config.get("risk_multiplier_min", 0.5))
        self.risk_multiplier_max = float(risk_config.get("risk_multiplier_max", 1.2))
        self.max_daily_loss = risk_config.get("max_daily_loss", 0.05)
        self.stop_loss_ratio = risk_config.get("stop_loss_ratio", 0.02)
        self.take_profit_ratio = risk_config.get("take_profit_ratio", 0.04)

        # 안전 운용 모드: 실전 트리거는 실물 데이터 AND 고정, 예언 레이어는 보조 가중으로 제한
        safety_mode_config = self.config.get("safety_mode", {})
        self.enforce_realworld_and_gate = bool(safety_mode_config.get("enforce_realworld_and_gate", True))
        self.prophecy_search_quality_cap = float(safety_mode_config.get("prophecy_search_quality_cap", 0.4))
        self.require_realworld_confirmation_for_bidirectional = bool(
            safety_mode_config.get("require_realworld_confirmation_for_bidirectional", True)
        )
        # 보조 레이어(성경/명리/사상/PMI/Reasoning)는 직접 BUY/SELL 트리거가 아닌
        # 리스크 배율(leverage_multiplier) 보정 용도로만 사용한다.
        self.auxiliary_layers_risk_only = bool(safety_mode_config.get("auxiliary_layers_risk_only", True))

        _pf = strategy_config.get("prophecy_phase1_fusion") or {}
        self.prophecy_phase1_fusion_enabled = bool(_pf.get("enabled", False))
        self.prophecy_phase1_fusion = {
            "w_macro": float(_pf.get("w_macro", 0.5)),
            "w_micro": float(_pf.get("w_micro", 0.5)),
            "score_threshold_buy": float(_pf.get("score_threshold_buy", 0.12)),
            "score_threshold_sell": float(_pf.get("score_threshold_sell", -0.12)),
        }
        _ig = strategy_config.get("insight_observation_gate") or {}
        self.insight_observation_gate_enabled = bool(_ig.get("enabled", False))
        self.insight_observation_gate_mode = str(_ig.get("mode", "observe")).strip().lower()
        if self.insight_observation_gate_mode not in ("observe", "block"):
            self.insight_observation_gate_mode = "observe"
        _logp = (_ig.get("log_path") or "").strip()
        self.insight_observation_log_path = Path(_logp) if _logp else (workspace_root / "data" / "myeongni" / "insight_observation_log.jsonl")
        _ap = (_ig.get("regime_alias_path") or "").strip()
        if _ap:
            self.insight_regime_alias_path: Path = Path(_ap)
        else:
            # Gate 모듈이 없는 환경에서도 기본 비활성 경로로 안전하게 부팅한다.
            fallback_alias_path = workspace_root / "data" / "myeongni" / "regime_aliases.json"
            if self.insight_observation_gate_enabled:
                try:
                    from .insight_observation_gate import default_alias_path

                    self.insight_regime_alias_path = default_alias_path(workspace_root)
                except ImportError:
                    logger.warning(
                        "⚠️ insight_observation_gate 모듈 없음: fallback alias path 사용 (%s)",
                        fallback_alias_path,
                    )
                    self.insight_regime_alias_path = fallback_alias_path
            else:
                self.insight_regime_alias_path = fallback_alias_path
        self._insight_regime_aliases: Dict[str, str] = {}
        self._insight_filter_rules: List[Dict[str, Any]] = []
        
        logger.info(
            f"✅ 설정 파일 로드 완료: min_confidence={self.min_confidence:.2f}, "
            f"min_consecutive_signals={self.min_consecutive_signals}, max_position_size={self.max_position_size:.2%}, "
            f"enforce_realworld_and_gate={self.enforce_realworld_and_gate}, "
            f"prophecy_search_quality_cap={self.prophecy_search_quality_cap:.2f}, "
            f"auxiliary_layers_risk_only={self.auxiliary_layers_risk_only}, "
            f"risk_multiplier_range=({self.risk_multiplier_min:.2f},{self.risk_multiplier_max:.2f})"
        )

        # 4h 최적화 프리셋 로드 (있을 때만 적용)
        self.bcl_4h_optimizer_enabled = False
        self.bcl_4h_best_params: Dict[str, Any] = {}
        bcl_4h_cfg = self.config.get("bcl_v2_4h_optimizer", {}) if isinstance(self.config, dict) else {}
        if isinstance(bcl_4h_cfg, dict):
            best_params = bcl_4h_cfg.get("best_params", {})
            if isinstance(best_params, dict) and best_params:
                self.bcl_4h_optimizer_enabled = True
                self.bcl_4h_best_params = best_params
                logger.info(
                    "✅ bcl_v2_4h_optimizer 적용: min=%.3f, max=%.3f, lag_bars=%s, slope=%.3f, ma_bars=%s, vol_target=%s",
                    float(best_params.get("bcl_min", 0.0)),
                    float(best_params.get("bcl_max", 0.0)),
                    best_params.get("lag_bars"),
                    float(best_params.get("scaling_slope", 1.0)),
                    best_params.get("momentum_ma_bars"),
                    best_params.get("vol_target"),
                )
        
        # Crypto-Nitro 백테스트 엔진 초기화 (신호 생성용) - 선택적
        if CRYPTO_NITRO_AVAILABLE and CryptoNitroBacktest is not None:
            logger.info("🚀 Crypto-Nitro v1.6 엔진 초기화 중...")
            try:
                self.crypto_nitro = CryptoNitroBacktest(
                    initial_capital=initial_capital,
                    leverage=leverage,
                    use_great_trunk_filter=use_great_trunk_filter
                )
                logger.info("✅ Crypto-Nitro 엔진 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Crypto-Nitro 엔진 초기화 실패: {e}")
                self.crypto_nitro = None
        else:
            logger.warning("⚠️ Crypto-Nitro 엔진 사용 불가, 기본 전략으로 Fallback")
            self.crypto_nitro = None
        
        # 거대한 줄기 추세 필터 (GreatTrunkTrendFilter 로드된 경우에만 사용)
        if use_great_trunk_filter and GreatTrunkTrendFilter is not None:
            try:
                self.great_trunk_filter = GreatTrunkTrendFilter()
                logger.info("✅ 거대한 줄기 추세 필터 로드 완료")
            except Exception as e:
                logger.warning(f"⚠️ 거대한 줄기 추세 필터 로드 실패: {e}")
                self.great_trunk_filter = None
                self.use_great_trunk_filter = False
        else:
            self.great_trunk_filter = None
            if use_great_trunk_filter and GreatTrunkTrendFilter is None:
                self.use_great_trunk_filter = False
        
        # 가격 데이터 (최근 100개 캔들)
        self.price_data = pd.DataFrame()
        
        # 🔴 다중 확인 로직: 연속 신호 추적 (설정에서 min_consecutive_signals 로드됨)
        self.signal_history = []  # 최근 신호 히스토리 (최대 5개)
        
        # 🎯 시장 국면 탐지 시스템 초기화
        self.regime_detector = None
        self.current_regime = None
        self.regime_history = []  # 국면 변화 추적
        if REGIME_DETECTION_AVAILABLE and MarketRegimeDetector is not None:
            try:
                self.regime_detector = MarketRegimeDetector(n_states=6, n_iter=100)
                logger.info("✅ 시장 국면 탐지 시스템 초기화 완료 (HMM 6상태)")
            except Exception as e:
                logger.warning(f"⚠️ 시장 국면 탐지 시스템 초기화 실패: {e}")
                self.regime_detector = None
        else:
            logger.warning("⚠️ 시장 국면 탐지 시스템 사용 불가 (import 실패)")
        
        # 🏛️ 최신 통합 모듈 초기화
        if LATEST_MODULES_AVAILABLE:
            self.phase_resonance_checker = PhaseResonanceFactChecker()
            self.quaternion_analyzer = QuaternionFinanceAnalyzer()
            self.sbsc_verifier = SBSCStrategyVerifier(domain="finance")
            logger.info("✅ 최신 통합 모듈 초기화 완료 (위상 공명 팩트체크, 사원수 분석, SBSC 검증)")
        else:
            self.phase_resonance_checker = None
            self.quaternion_analyzer = None
            self.sbsc_verifier = None
        
        # 🔥 화기운 감지 모듈 초기화 (캘리브레이션 모드에서는 스킵)
        if self.backtest_calibration:
            self.nowcaster = None
            self.precision_filter = None
        elif FIRE_ENERGY_AVAILABLE:
            try:
                self.nowcaster = PhaseSpaceNowcaster(enable_unified_engine=True)
                self.precision_filter = PrecisionImprovementFilter()
                logger.info("✅ 화기운 감지 모듈 초기화 완료 (PhaseSpaceNowcaster, Precision 필터)")
            except Exception as e:
                logger.warning(f"⚠️ 화기운 감지 모듈 초기화 실패: {e}")
                self.nowcaster = None
                self.precision_filter = None
        else:
            self.nowcaster = None
            self.precision_filter = None
        
        # 🔥 양방향 매매 전략 초기화
        if BIDIRECTIONAL_STRATEGY_AVAILABLE:
            try:
                self.bidirectional_strategy = BidirectionalFireMetalStrategy()
                logger.info("✅ 양방향 매매 전략 초기화 완료 (2026 Fire Crash + 2028 Metal Reset)")
            except Exception as e:
                logger.warning(f"⚠️ 양방향 매매 전략 초기화 실패: {e}")
                self.bidirectional_strategy = None
        else:
            self.bidirectional_strategy = None
        
        # 🏛️ PMI-Nitro 엔진 초기화 (예언적 주기성 + 비선형 카오스)
        self.pmi_engine = None
        self.constitution = "SE"  # 기본값: 소음인 (방어형, 안전)
        
        # 🚀 Phase 1 GPU 훈련 모델 초기화 (선택적)
        self.phase1_model = None
        self.use_phase1_model = True  # Phase 1 모델 사용 여부
        try:
            from .phase1_model_predictor import Phase1ModelPredictor
            self.phase1_model = Phase1ModelPredictor()
            if self.phase1_model.is_available():
                logger.info("✅ Phase 1 GPU 훈련 모델 로드 완료")
            else:
                logger.warning("⚠️ Phase 1 모델 로드 실패, 기존 전략만 사용")
                self.phase1_model = None
        except ImportError as e:
            logger.warning(f"⚠️ Phase 1 모델 import 실패: {e}")
            self.phase1_model = None
        except Exception as e:
            logger.warning(f"⚠️ Phase 1 모델 초기화 실패: {e}")
            self.phase1_model = None
        if self.insight_observation_gate_enabled:
            try:
                from .insight_observation_gate import load_filter_rules, load_regime_aliases

                self._insight_regime_aliases = load_regime_aliases(self.insight_regime_alias_path)
                self._insight_filter_rules = load_filter_rules(self.insight_observation_log_path)
                logger.info(
                    "✅ insight_observation_gate: %s 규칙, 별칭 %s개 (%s, alias=%s)",
                    len(self._insight_filter_rules),
                    len(self._insight_regime_aliases),
                    self.insight_observation_log_path,
                    self.insight_regime_alias_path,
                )
            except Exception as e:
                logger.warning("⚠️ insight_observation_gate 로드 실패: %s", e)
        if PMI_NITRO_AVAILABLE:
            try:
                # 체질은 환경 변수나 설정에서 가져올 수 있음 (기본값: SE)
                constitution = "SE"  # TODO: 환경 변수에서 가져오기
                self.pmi_engine = PMINitroEngine(
                    constitution=constitution,
                    enable_prophetic_cycles=True
                )
                self.constitution = constitution
                
                # 🔧 설정 파일에서 PMI 임계값 읽어오기
                if self.pmi_engine:
                    optimal_params = self.config.get("optimal_parameters", {})
                    ipe_threshold = optimal_params.get("ipe_threshold", 1.5)  # 기본값 1.5
                    self.pmi_engine.ipe_threshold = ipe_threshold
                    logger.info(f"✅ PMI-Nitro 엔진 초기화 완료 (체질: {constitution}, IPE 임계값: {ipe_threshold})")
            except Exception as e:
                logger.warning(f"⚠️ PMI-Nitro 엔진 초기화 실패: {e}")
                self.pmi_engine = None
        else:
            logger.warning("⚠️ PMI-Nitro 엔진 사용 불가 (import 실패)")
        
        # 🏛️ JEMA-12 Trinity: LeadingApocalypseIndex (명리 + 성경 주기 통합)
        if LAI_AVAILABLE:
            try:
                self.lai = LeadingApocalypseIndex()
                logger.info("✅ JEMA-12 Trinity (LeadingApocalypseIndex) 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ LeadingApocalypseIndex 초기화 실패: {e}")
                self.lai = None
        else:
            self.lai = None
        
        # 🏛️ JEMA-12 Reasoning Engine (System 2 Thinking)
        try:
            from tools.core.jema12_reasoning_engine import JEMA12ReasoningEngine
            self.reasoning_engine = JEMA12ReasoningEngine()
            logger.info("✅ JEMA-12 Reasoning Engine 초기화 완료 (System 2 Thinking)")
        except ImportError:
            logger.warning("⚠️ JEMA-12 Reasoning Engine을 찾을 수 없습니다. System 2 Thinking 비활성화")
            self.reasoning_engine = None
        
        # 🧠 TradingAthenaRouter 초기화 (MKM-Sovereign-Core 통합, 캘리브레이션 모드에서는 스킵)
        self.athena_router = None
        if not self.backtest_calibration:
            try:
                from src.integration.athena_router_integration import TradingAthenaRouter
                self.athena_router = TradingAthenaRouter(use_codebook_router=True)
                logger.info("✅ TradingAthenaRouter 초기화 완료 (MoE 코드북 라우팅 활성화)")
            except Exception as e:
                logger.warning(f"⚠️ TradingAthenaRouter 초기화 실패: {e}")
                self.athena_router = None
        
        # 🏛️ Financial Sovereign Harness 초기화 (캘리브레이션 모드에서는 스킵)
        self.harness = None
        if not self.backtest_calibration:
            try:
                from tools.core.financial_sovereign_harness import FinancialSovereignHarness
                codebook_path = workspace_root / "projects" / "bitcoin-trading" / "data" / "signal_codebook.json"
                codebook_path.parent.mkdir(parents=True, exist_ok=True)
                self.harness = FinancialSovereignHarness(codebook_path=str(codebook_path))
                logger.info("✅ Financial Sovereign Harness 초기화 완료 (헌법 제3조: 100% Literal Restoration)")
            except Exception as e:
                logger.warning(f"⚠️ Financial Sovereign Harness 초기화 실패: {e}")
                self.harness = None
        
        # 🏛️ Bitcoin 4D Mapper 초기화 (캘리브레이션 모드에서는 스킵, lazy import로 무거운 로드 방지)
        self.bitcoin_4d_mapper = None
        if not self.backtest_calibration:
            try:
                try:
                    from src.data.bitcoin_4d_mapper import Bitcoin4DMapper as _Bitcoin4DMapper
                except ImportError:
                    from ..data.bitcoin_4d_mapper import Bitcoin4DMapper as _Bitcoin4DMapper
                self.bitcoin_4d_mapper = _Bitcoin4DMapper(
                    binance_client=binance_client,
                    onchain_api_key=None,  # TODO: 환경 변수에서 로드
                    onchain_api_secret=None  # TODO: 환경 변수에서 로드
                )
                logger.info("✅ Bitcoin 4D Mapper 초기화 완료 (비트코인 특화 데이터 매핑)")
            except Exception as e:
                logger.warning(f"⚠️ Bitcoin 4D Mapper 초기화 실패: {e}")
                self.bitcoin_4d_mapper = None

        # 🏛️ Historical Pattern Analyzer 초기화 (30년 데이터 기반, lazy import)
        self.historical_pattern_analyzer = None
        if self.bitcoin_4d_mapper:
            try:
                try:
                    from src.analysis.historical_pattern_analyzer import HistoricalPatternAnalyzer as _HistoricalPatternAnalyzer
                except ImportError:
                    from ..analysis.historical_pattern_analyzer import HistoricalPatternAnalyzer as _HistoricalPatternAnalyzer
                if hasattr(self.bitcoin_4d_mapper, 'multi_layer_timeline') and self.bitcoin_4d_mapper.multi_layer_timeline:
                    self.historical_pattern_analyzer = _HistoricalPatternAnalyzer(
                        multi_layer_timeline=self.bitcoin_4d_mapper.multi_layer_timeline,
                        sovereign_data_infusion=self.bitcoin_4d_mapper.sovereign_data if hasattr(self.bitcoin_4d_mapper, 'sovereign_data') else None
                    )
                    logger.info("✅ Historical Pattern Analyzer 초기화 완료 (30년 데이터 기반)")
                else:
                    logger.warning("⚠️ Multi-Layer Timeline이 없어 Historical Pattern Analyzer 초기화 실패")
            except Exception as e:
                logger.warning(f"⚠️ Historical Pattern Analyzer 초기화 실패: {e}")
                self.historical_pattern_analyzer = None

        # 🧠 TimeXer-Exog 모델 초기화 (시계열 + 외생 변수 보조 신호, 비침투형)
        self.timexer_model = None
        self.use_timexer_model = True
        if TIMEXER_EXOG_AVAILABLE and TimeXerExogModel is not None and TimeXerExogConfig is not None:
            try:
                timexer_cfg = self.config.get("timexer_exog", {})
                input_window = int(timexer_cfg.get("input_window", 64))
                forecast_horizon = int(timexer_cfg.get("forecast_horizon", 1))
                target_col = str(timexer_cfg.get("target_col", "future_return"))

                timexer_enabled = bool(timexer_cfg.get("enabled", True))
                self.use_timexer_model = timexer_enabled

                cfg = TimeXerExogConfig(
                    input_window=input_window,
                    forecast_horizon=forecast_horizon,
                    target_col=target_col,
                )
                self.timexer_model = TimeXerExogModel(config=cfg)
                logger.info(
                    "✅ TimeXer-Exog 모델 초기화 완료 (enabled=%s, input_window=%d, forecast_horizon=%d, target_col=%s)",
                    timexer_enabled,
                    input_window,
                    forecast_horizon,
                    target_col,
                )
            except Exception as e:
                logger.warning("⚠️ TimeXer-Exog 모델 초기화 실패: %s", e)
                self.timexer_model = None
                self.use_timexer_model = False
        else:
            logger.info("ℹ️ TimeXer-Exog 모델 비활성화 (모듈 없음 또는 설정상 비사용)")

        # 🏛️ 명리 컨트롤러 Phase 2 초기화 (타이밍 기반 우선순위 큐)
        self.myeongri_controller = None
        try:
            from tools.core.myeongri_controller import MyeongriController
            # 설정 파일에서 명리 데이터 읽기 (선택적)
            myeongri_config = self.config.get("myeongri", {})
            if myeongri_config.get("enabled", False):
                birth_year = myeongri_config.get("birth_year")
                birth_month = myeongri_config.get("birth_month")
                birth_day = myeongri_config.get("birth_day")
                birth_hour = myeongri_config.get("birth_hour", 0)
                is_solar = myeongri_config.get("is_solar", False)
                is_male = myeongri_config.get("is_male", True)
                
                if birth_year and birth_month and birth_day:
                    self.myeongri_controller = MyeongriController(
                        birth_year=birth_year,
                        birth_month=birth_month,
                        birth_day=birth_day,
                        birth_hour=birth_hour,
                        is_solar=is_solar,
                        is_male=is_male
                    )
                    logger.info("✅ 명리 컨트롤러 Phase 2 초기화 완료 (타이밍 기반 우선순위 큐)")
                else:
                    logger.warning("⚠️ 명리 컨트롤러 설정 불완전 (생년월일 필요), 비활성화")
            else:
                logger.info("ℹ️ 명리 컨트롤러 비활성화 (설정 파일에서 enabled: false)")
        except ImportError as e:
            logger.warning(f"⚠️ 명리 컨트롤러 import 실패: {e}, 비활성화")
            self.myeongri_controller = None
        except Exception as e:
            logger.warning(f"⚠️ 명리 컨트롤러 초기화 실패: {e}, 비활성화")
            self.myeongri_controller = None
    
    def _load_trading_config(self) -> Dict[str, Any]:
        """
        거래 설정 파일 로드 (YAML)
        
        Returns:
            설정 딕셔너리
        """
        try:
            candidates = [
                workspace_root / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml",
                Path("C:/workspace/projects/bitcoin-trading/config/trading_config.yaml"),
                Path(__file__).resolve().parents[2] / "config" / "trading_config.yaml",
            ]

            config_path = next((p for p in candidates if p.exists()), None)
            if config_path is None:
                logger.warning(f"⚠️ 설정 파일이 없습니다. 후보 경로: {[str(p) for p in candidates]}. 기본값 사용.")
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            logger.info(f"✅ 거래 설정 파일 로드 완료: {config_path}")
            return config
            
        except Exception as e:
            logger.warning(f"⚠️ 설정 파일 로드 실패: {e}. 기본값 사용.")
            return {}
    
    def apply_jema12_trinity_validation(
        self,
        current_date: datetime,
        vector_4d: Dict[str, float],
        fire_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🏛️ JEMA-12 Trinity Cross-Validation 적용
        
        명리(시간) + 이제마(필터) + 성경(방향) 3축 통합 검증
        
        Args:
            current_date: 현재 날짜
            vector_4d: 4D 벡터
            fire_analysis: 화기운 분석 결과
        
        Returns:
            {
                "cross_validation_confidence": float,  # Cross-Validation 신뢰도 (0.0~1.0)
                "myungri_fire_intensity": float,  # 명리 화기 농도
                "sasang_filter_intensity": float,  # 이제마 필터 강도
                "biblical_risk": float,  # 성경 주기 위험도
                "agreement_scores": {
                    "myungri_sasang": float,  # 명리-이제마 일치도
                    "sasang_biblical": float,  # 이제마-성경 일치도
                    "myungri_biblical": float  # 명리-성경 일치도
                }
            }
        """
        # 기본값 반환 (LAI가 없을 경우)
        default_result = {
            "cross_validation_confidence": 0.5,  # 기본 신뢰도
            "myungri_fire_intensity": 1.0,
            "sasang_filter_intensity": 0.0,
            "biblical_risk": 1.0,
            "agreement_scores": {
                "myungri_sasang": 0.5,
                "sasang_biblical": 0.5,
                "myungri_biblical": 0.5
            }
        }
        
        if not self.lai:
            return default_result
        
        try:
            # 1. 명리(시간) 정보
            manser_data = self.lai.get_manser_data(current_date)
            ganji_risk = {"risk_level": "NORMAL", "weight_multiplier": 1.0}
            
            if manser_data:
                ganji = manser_data.get("ganji", {})
                ganji_year = ganji.get("year", "")
                ganji_risk = self.lai.analyze_ganji_risk(ganji_year)
            
            myungri_fire_intensity = ganji_risk.get("weight_multiplier", 1.0)
            
            # 2. 이제마(필터) 정보 - 태양인 소수성 발산 감지
            # VIX 값 계산 (변동성 기반)
            if len(self.price_data) >= 20:
                volatility = self.price_data['close'].pct_change().std()
                vix_value = volatility * 100.0 if volatility > 0 else 20.0
            else:
                vix_value = 20.0
            
            hydrophobic_result = self.lai.calculate_taeyangin_hydrophobic_divergence(
                vector_4d=vector_4d,
                vix_value=vix_value,
                domain="stock_volatile"
            )
            sasang_filter_intensity = hydrophobic_result.get("hydrophobic_intensity", 0.0)
            
            # 3. 성경(방향) 정보
            cycle_info = self.lai.calculate_biblical_cycle_position(current_date)
            biblical_risk = 0.0
            
            if cycle_info.get("is_sabbath_year_before"):
                biblical_risk = 1.5  # 안식년 직전
            elif cycle_info.get("is_sabbath_year"):
                biblical_risk = 2.0  # 안식년
            elif cycle_info.get("is_critical_period"):
                biblical_risk = 1.2  # 1260일 임계점
            else:
                biblical_risk = 1.0  # 정상
            
            # 4. Cross-Validation: 3축 예측값 정규화 (0.0 ~ 1.0)
            myungri_pred = min(1.0, myungri_fire_intensity / 2.0)  # 최대 2.0 기준
            sasang_pred = min(1.0, sasang_filter_intensity / 2.0)  # 최대 2.0 기준
            biblical_pred = min(1.0, biblical_risk / 2.0)  # 최대 2.0 기준
            
            # 일치도 계산 함수
            def calculate_agreement(pred1: float, pred2: float) -> float:
                """두 예측값의 일치도 계산"""
                diff = abs(pred1 - pred2)
                max_val = max(pred1, pred2, 0.1)  # 0으로 나누기 방지
                return 1.0 - (diff / max_val)
            
            agreement_myungri_sasang = calculate_agreement(myungri_pred, sasang_pred)
            agreement_sasang_biblical = calculate_agreement(sasang_pred, biblical_pred)
            agreement_myungri_biblical = calculate_agreement(myungri_pred, biblical_pred)
            
            # 최종 Cross-Validation 신뢰도 계산
            cross_validation_confidence = (
                0.4 * agreement_myungri_sasang +
                0.3 * agreement_sasang_biblical +
                0.3 * agreement_myungri_biblical
            )
            
            return {
                "cross_validation_confidence": float(cross_validation_confidence),
                "myungri_fire_intensity": float(myungri_fire_intensity),
                "sasang_filter_intensity": float(sasang_filter_intensity),
                "biblical_risk": float(biblical_risk),
                "agreement_scores": {
                    "myungri_sasang": float(agreement_myungri_sasang),
                    "sasang_biblical": float(agreement_sasang_biblical),
                    "myungri_biblical": float(agreement_myungri_biblical)
                }
            }
            
        except Exception as e:
            logger.warning(f"⚠️ JEMA-12 Trinity 검증 중 오류: {e}")
            return default_result

    def _apply_btc6_regime_multiplier(
        self,
        vector_4d: Dict[str, float],
        psi_score: float,
        base_multiplier: float,
    ) -> float:
        """
        BTC-6 Regime Fusion adapter를 통한 추가 리스크 계수 적용.

        1차 레짐(regime_map) + 2차 레짐(biblical, 보조) 융합 후 0.2~1.5 구간 계수를 반환하며,
        실전 레버리지/포지션 크기에 직접 반영된다 (signal_data["leverage_multiplier"] → live_trader).
        """
        if not BTC6_ADAPTER_AVAILABLE or get_btc6_risk_multiplier is None:
            return base_multiplier

        try:
            btc6_mul = float(
                get_btc6_risk_multiplier(
                    vector_4d=vector_4d,
                    psi_score=psi_score,
                )
            )
            if btc6_mul <= 0:
                return base_multiplier
            return base_multiplier * btc6_mul
        except Exception as e:
            logger.debug(f"BTC-6 Regime Fusion multiplier 적용 중 오류(무시): {e}")
            return base_multiplier

    def _apply_dual_regime_protection(
        self,
        current_time: datetime,
        vector_4d: Dict[str, float],
        psi_score: float,
        biblical_risk: float,
        base_multiplier: float,
        signal_data: Dict[str, Any],
    ) -> float:
        """
        성경 레짐 리스크(biblical_risk)와 실물 피처(글로벌 유동성)를 AND 조건으로 결합하여
        극단적 위기 구간에서만 레버리지 축소 및 신규 진입 차단 플래그를 설정한다.

        설계 원칙 (Phase A1):
        - Dual Regime API 또는 정책 파일이 없으면 기존 레버리지와 신호를 그대로 유지한다.
        - bible_risk_score는 JEMA-12 Trinity 스케일(1.0=정상, >1.0=위험 상승)을 그대로 사용한다.
        - 듀얼 레짐 트리거가 True일 때만 레버리지 상한을 0.5 배수 이내로 줄이고,
          야간(23시~07시) 신규 진입 차단 플래그를 세팅한다.
        """
        if (
            not DUAL_REGIME_API_AVAILABLE
            or evaluate_dual_regime_and_market_shock is None
            or not isinstance(vector_4d, dict)
            or not vector_4d
        ):
            return base_multiplier

        state_id, state_id_source = _resolve_state_id_with_source(signal_data)
        gate_profile = str(os.getenv("DUAL_REGIME_GATE_PROFILE", "")).strip().lower() or None

        try:
            ctx: DualRegimeContext = evaluate_dual_regime_and_market_shock(
                as_of=current_time,
                vector_4d=vector_4d,
                psi_score=float(psi_score),
                bible_risk_score=float(biblical_risk),
                workspace_root=workspace_root,
                state_id=state_id,
                state_provenance=_state_provenance_from_signal(signal_data),
                gate_profile=gate_profile,
            )
        except Exception as e:  # pragma: no cover - 방어적 처리
            logger.debug("dual_regime_protection: evaluate_dual_regime_and_market_shock 오류(무시): %s", e)
            return base_multiplier

        dual_trigger = bool(ctx.market_shock_confirmed and float(biblical_risk) >= 1.0)
        signal_data.setdefault("risk_assessment", {})
        signal_data["risk_assessment"]["dual_regime_context"] = {
            "market_shock_confirmed": ctx.market_shock_confirmed,
            "resonance_count": getattr(ctx, "resonance_count", 0),
            "veto_triggered": getattr(ctx, "veto_triggered", False),
            "risk_multiplier_cap": getattr(ctx, "risk_multiplier_cap", 1.0),
            "interpretation": getattr(ctx, "interpretation", "none"),
            "state_id": state_id,
            "state_id_source": state_id_source,
            "gate_profile": gate_profile or "balanced",
        }

        # 공명 또는 실물 우선 veto가 있으면 즉시 하향 캡 적용 (증폭 금지)
        dynamic_cap = float(getattr(ctx, "risk_multiplier_cap", 1.0) or 1.0)
        if dynamic_cap < 1.0:
            protected_mul = float(min(base_multiplier, dynamic_cap))
            signal_data["risk_assessment"]["signal_registry_clamped"] = True
            signal_data["risk_assessment"]["signal_registry_cap"] = dynamic_cap
            return protected_mul

        if not dual_trigger:
            return base_multiplier

        # 듀얼 레짐 트리거가 켜진 경우: 레버리지 상한 0.5 배수 이내로 강제 축소
        protected_mul = float(min(base_multiplier, 0.5))
        signal_data["risk_assessment"]["dual_regime_triggered"] = True
        signal_data["risk_assessment"]["dual_regime_leverage_before"] = base_multiplier
        signal_data["risk_assessment"]["dual_regime_leverage_after"] = protected_mul

        # 야간(23시~07시) 신규 진입 차단 플래그: 실제 포지션 엔진에서 해석
        hour = current_time.hour
        night_block = hour >= 23 or hour < 7
        if night_block:
            signal_data["risk_assessment"]["dual_regime_night_block"] = True

        logger.info(
            "🔐 Dual Regime Protection 발동: market_shock=%s mul=%.3f→%.3f night_block=%s",
            ctx.market_shock_confirmed,
            base_multiplier,
            protected_mul,
            night_block,
        )
        return protected_mul
    
    def fetch_price_data(self, limit: int = 100) -> pd.DataFrame:
        """
        가격 데이터 수집 (최근 N개 캔들)
        
        Args:
            limit: 캔들 개수
        
        Returns:
            가격 데이터 DataFrame (columns: timestamp, open, high, low, close, volume 등)
        """
        try:
            # Binance API 클라이언트가 있으면 사용
            if self.binance_client:
                raw_klines = self.binance_client.get_klines(
                    symbol=self.symbol,
                    interval="1d",
                    limit=limit
                )
                
                # raw_klines: list of lists → DataFrame 변환
                if raw_klines and isinstance(raw_klines[0], (list, tuple)):
                    first = raw_klines[0]
                    if len(first) >= 12:
                        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                                'taker_buy_quote', 'ignore']
                    else:
                        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    df = pd.DataFrame(raw_klines, columns=cols[:len(first)])
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('date', inplace=True)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = df[col].astype(float)
                elif raw_klines and isinstance(raw_klines, pd.DataFrame):
                    df = raw_klines
                else:
                    df = pd.DataFrame()
                
                if df is not None and len(df) > 0:
                    # 변동성 계산 (30일 롤링, 연율화)
                    df['volatility'] = df['close'].pct_change().rolling(30).std() * np.sqrt(365)
                    df['volatility'] = df['volatility'].fillna(0.485)  # 기본값
                    
                    # NVT Ratio 계산 (실제 계산)
                    df['nvt_ratio'] = df.apply(
                        lambda row: self.calculate_nvt_ratio(row.get('close', 0), row.get('volume', 0)),
                        axis=1
                    )
                    df['nvt_ratio'] = df['nvt_ratio'].fillna(50.0)  # 계산 실패 시 기본값
                    
                    # price_data 업데이트
                    self.price_data = df
                    logger.info(f"✅ 가격 데이터 수집 완료: {len(df)}개 캔들")
                    return df
                else:
                    logger.warning("⚠️ Binance API로 가격 데이터를 가져올 수 없습니다.")
                    return pd.DataFrame()
            else:
                # Binance API 클라이언트가 없으면 공개 API Fallback 시도
                logger.warning("⚠️ Binance API 클라이언트가 없습니다. 공개 API로 시도합니다.")
                return self._fetch_price_data_public_api(limit)
        
        except Exception as e:
            logger.error(f"❌ 가격 데이터 수집 실패: {e}")
            # Fallback: 공개 API
            return self._fetch_price_data_public_api(limit)
    
    def _fetch_price_data_public_api(self, limit: int = 100) -> pd.DataFrame:
        """
        Binance 공개 API로 가격 데이터 수집 (Fallback, API 키 불필요)
        
        Args:
            limit: 캔들 개수
        
        Returns:
            가격 데이터 DataFrame
        """
        try:
            import requests
            
            # Binance 공개 API 엔드포인트 (API 키 불필요)
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': self.symbol,
                'interval': '1d',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                logger.warning("⚠️ 공개 API에서 데이터를 가져올 수 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('date', inplace=True)
            
            # 숫자 형식 변환
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            # 변동성 계산 (30일 롤링, 연율화)
            df['volatility'] = df['close'].pct_change().rolling(30).std() * np.sqrt(365)
            df['volatility'] = df['volatility'].fillna(0.485)  # 기본값
            
            # NVT Ratio 계산 (실제 계산)
            df['nvt_ratio'] = df.apply(
                lambda row: self.calculate_nvt_ratio(row.get('close', 0), row.get('volume', 0)),
                axis=1
            )
            df['nvt_ratio'] = df['nvt_ratio'].fillna(50.0)  # 계산 실패 시 기본값
            
            # price_data 업데이트
            self.price_data = df
            
            logger.info(f"✅ 공개 API로 가격 데이터 수집 완료: {len(df)}개 캔들")
            return df
            
        except Exception as e:
            logger.error(f"❌ 공개 API 가격 데이터 수집 실패: {e}")
            return pd.DataFrame()
    
    def calculate_nvt_ratio(
        self,
        price: float,
        daily_volume: float
    ) -> float:
        """
        NVT Ratio 계산
        
        NVT = Market Cap / Daily Transaction Volume
        
        Args:
            price: 현재 가격
            daily_volume: 일일 거래량 (USDT)
        
        Returns:
            NVT Ratio (기본값: 50.0)
        """
        try:
            # 시가총액 계산 (현재 가격 × 총 공급량)
            # Bitcoin 총 공급량: 약 21,000,000 BTC (하드코딩, 실제로는 API에서 가져와야 함)
            TOTAL_SUPPLY = 21000000.0
            market_cap = price * TOTAL_SUPPLY
            
            # 일일 거래량이 없으면 기본값 반환
            if daily_volume == 0 or daily_volume is None:
                return 50.0
            
            # NVT Ratio 계산
            nvt_ratio = market_cap / daily_volume
            
            # 비정상적인 값 필터링 (0.1 ~ 1000 범위)
            if nvt_ratio < 0.1 or nvt_ratio > 1000:
                logger.warning(f"⚠️ 비정상적인 NVT Ratio: {nvt_ratio:.2f}, 기본값 사용")
                return 50.0
            
            return float(nvt_ratio)
        
        except Exception as e:
            logger.error(f"❌ NVT Ratio 계산 실패: {e}")
            return 50.0  # 기본값

    def _load_logos_timeline_cache(self) -> Optional[Dict[str, Any]]:
        """Load timeline anchor JSON with file-change auto-reload."""
        try:
            if not self._logos_timeline_path.is_file():
                return None
            stat = self._logos_timeline_path.stat()
            mtime_ns = int(stat.st_mtime_ns)
            if (
                self._logos_timeline_cache is not None
                and self._logos_timeline_cache_mtime_ns == mtime_ns
            ):
                return self._logos_timeline_cache
            self._logos_timeline_cache = json.loads(
                self._logos_timeline_path.read_text(encoding="utf-8")
            )
            self._logos_timeline_cache_mtime_ns = mtime_ns
            return self._logos_timeline_cache
        except Exception as e:
            logger.debug("logos timeline cache load 실패(무시): %s", e)
            return None

    @staticmethod
    def _bce_to_astronomical_year(year_bce: int) -> int:
        # BCE to astronomical year conversion: 1 BCE => 0, 2 BCE => -1
        return 1 - int(year_bce)

    def _load_logos_timeline_calibration(self) -> Optional[Dict[str, Any]]:
        try:
            if not self._logos_timeline_calibration_path.is_file():
                return None
            stat = self._logos_timeline_calibration_path.stat()
            mtime_ns = int(stat.st_mtime_ns)
            if (
                self._logos_timeline_calibration_cache is not None
                and self._logos_timeline_calibration_cache_mtime_ns == mtime_ns
            ):
                return self._logos_timeline_calibration_cache
            self._logos_timeline_calibration_cache = json.loads(
                self._logos_timeline_calibration_path.read_text(encoding="utf-8")
            )
            self._logos_timeline_calibration_cache_mtime_ns = mtime_ns
            return self._logos_timeline_calibration_cache
        except Exception as e:
            logger.debug("logos timeline calibration load 실패(무시): %s", e)
            return None

    def _logos_timeline_calibration_multiplier(self, regime_id: str) -> float:
        doc = self._load_logos_timeline_calibration()
        if not doc:
            return 1.0
        try:
            multipliers = doc.get("multipliers", {})
            base = multipliers.get("base_by_tradition", {})
            by_regime = multipliers.get("by_tradition_regime", {})
            trad = self._logos_timeline_tradition
            m_base = float(base.get(trad, 1.0) or 1.0)
            m_regime = float(
                ((by_regime.get(trad, {}) if isinstance(by_regime.get(trad, {}), dict) else {})).get(
                    regime_id or "unknown", 1.0
                )
                or 1.0
            )
            return max(0.85, min(1.15, m_base * m_regime))
        except Exception:
            return 1.0

    def _build_logos_timeline_overlay(
        self,
        *,
        as_of: datetime,
        regime_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Build non-blocking, risk-neutral timeline context for logging/reporting only."""
        doc = self._load_logos_timeline_cache()
        if not doc:
            return None
        anchors = doc.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            return None

        current_year = int(as_of.year)
        candidates = []
        calibration_multiplier = self._logos_timeline_calibration_multiplier(regime_id)
        for a in anchors:
            try:
                y0_bce = int(a.get("window_start_year_bce"))
                y1_bce = int(a.get("window_end_year_bce"))
                start_astro = self._bce_to_astronomical_year(y0_bce)
                end_astro = self._bce_to_astronomical_year(y1_bce)
                center = int((start_astro + end_astro) / 2)
                width = abs(start_astro - end_astro)
                base_conf = float(a.get("confidence", 0.5) or 0.5)
                profiles = a.get("tradition_profiles", {})
                if isinstance(profiles, dict):
                    base_conf = float(
                        profiles.get(self._logos_timeline_tradition, base_conf) or base_conf
                    )

                # 70y macro resonance proxy: smaller phase distance => stronger overlap score.
                phase = abs((current_year - center) % 70)
                phase_dist = min(phase, 70 - phase)
                phase_score = max(0.0, 1.0 - (phase_dist / 35.0))
                raw_overlap = max(0.0, min(1.0, base_conf * 0.7 + phase_score * 0.3))
                overlap = round(max(0.0, min(1.0, raw_overlap * calibration_multiplier)), 4)

                candidates.append(
                    {
                        "anchor_id": a.get("anchor_id"),
                        "label": a.get("label"),
                        "event_type": a.get("event_type"),
                        "cycle_tags": a.get("cycle_tags", []),
                        "window_width_years": width,
                        "phase_distance_y70": int(phase_dist),
                        "overlap_score": overlap,
                    }
                )
            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(
            key=lambda x: (-float(x.get("overlap_score", 0.0)), int(x.get("phase_distance_y70", 999)))
        )
        top3 = candidates[:3]
        return {
            "schema": doc.get("schema", "logos_timeline_anchor_v1"),
            "method": "read_only_overlap_proxy",
            "risk_mode": "no_trade_impact",
            "tradition_profile": self._logos_timeline_tradition,
            "calibration_multiplier": round(calibration_multiplier, 4),
            "as_of_year_ce": current_year,
            "regime_id": regime_id or "unknown",
            "top_overlaps": top3,
        }
    
    def calculate_trading_signal(
        self,
        current_price: float,
        current_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Phase 3.4 (v1.6): 실시간 매매 신호 생성
        
        Args:
            current_price: 현재 가격
            current_time: 현재 시간 (None이면 자동)
        
        Returns:
            매매 신호 정보 (signal, confidence, leverage_multiplier 등)
        """
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # 가격 데이터가 충분하지 않으면 HOLD
            if len(self.price_data) < 20:
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "leverage_multiplier": 1.0,
                    "reason": "가격 데이터 부족"
                }
            
            # 최신 가격 데이터로 행 생성
            latest_row = self.price_data.iloc[-1].copy()
            latest_row['close'] = current_price
            
            # 🏛️ 비트코인 통일장 레짐 뷰 (λ + 4D 기반 상위 리스크 필터)
            btc_regime_summary = None
            current_regime_id_result: Dict[str, Any] = {"regime_id": "unknown", "distance": float("inf"), "fingerprint": None}
            try:
                if self.prophecy_stack is not None:
                    # 시장 요인 실데이터: price_data 기반 0~1 스코어 (athena_router 여부와 무관)
                    _vol = (
                        float(self.price_data["close"].pct_change().std())
                        if len(self.price_data) > 1
                        else 0.0
                    )
                    vol_score = float(min(max(_vol / 0.1, 0.0), 1.0))
                    # 모멘텀: 최근 14봉 수익률을 -0.1~0.1 구간에서 0~1로 매핑
                    if len(self.price_data) >= 14:
                        ret_14 = (self.price_data["close"].iloc[-1] / self.price_data["close"].iloc[-14]) - 1.0
                        momentum_score = float(min(max((ret_14 + 0.1) / 0.2, 0.0), 1.0))
                    else:
                        momentum_score = 0.5
                    # 거래량 스코어: 최근 거래량 / 20봉 평균, 상한 1.0
                    if "volume" in self.price_data.columns and len(self.price_data) >= 20:
                        vol_mean = float(self.price_data["volume"].iloc[-20:].mean())
                        cur_vol = float(self.price_data["volume"].iloc[-1])
                        volume_score = float(min(cur_vol / vol_mean, 1.0)) if vol_mean > 0 else 0.5
                    else:
                        volume_score = 0.5
                    market_factors = {
                        "realized_vol": vol_score,
                        "momentum_score": momentum_score,
                        "volume_score": volume_score,
                    }
                    btc_regime_summary = self.prophecy_stack.get_bitcoin_unified_field_summary(
                        as_of=current_time,
                        pathology_vector=None,
                        biblical_text=None,
                        myeongri_gapja=None,
                        domain_hint="btc_spot",
                        market_factors=market_factors,
                    )
                    # 🏛️ 현재 레짐(imf/it_bubble/lehman/covid) 판별 — codebook_ref·레짐별 파라미터용
                    try:
                        vec_4d = (
                            getattr(btc_regime_summary, "unified_vector_4d", None)
                            if btc_regime_summary else None
                        )
                        current_regime_id_result = self.prophecy_stack.get_current_regime(
                            vector_4d=vec_4d if isinstance(vec_4d, dict) else None
                        )
                        rid = current_regime_id_result.get("regime_id", "unknown")
                        if rid != "unknown":
                            logger.debug(
                                "현재 레짐: %s (거리: %s)",
                                rid,
                                current_regime_id_result.get("distance"),
                            )
                    except Exception as reg_e:
                        logger.debug("get_current_regime 실패: %s", reg_e)
            except Exception as e:
                logger.warning(f"⚠️ 비트코인 통일장 레짐 뷰 계산 실패: {e}")
                btc_regime_summary = None

            # 🧠 use_mean_reversion: 이론 선택 전 계산 → context 전달 (권장안 B)
            _regime_id_for_ctx = current_regime_id_result.get("regime_id", "unknown")
            _regime_id_to_type = {"unknown": "UNKNOWN", "lehman": "CRISIS", "covid": "CRISIS", "imf": "TRANSITION", "it_bubble": "TRANSITION"}
            _rt = _regime_id_to_type.get(_regime_id_for_ctx, "UNKNOWN")
            use_mean_reversion_flag = use_mean_reversion(_rt, None) if use_mean_reversion is not None else False
            if self.force_use_mean_reversion is not None:
                use_mean_reversion_flag = bool(self.force_use_mean_reversion)

            # 🧪 calibration_mode: 복잡 PMI/게이트/헌법 경로가 한쪽 신호로 쏠릴 때가 있어
            # 스윕용으로는 10/40 봉 MA 추세 기반 간단 신호만 사용 (즉시 리턴)
            if self.backtest_calibration:
                try:
                    if len(self.price_data) < 80:
                        return {
                            "signal": "HOLD",
                            "confidence": 0.0,
                            "leverage_multiplier": 1.0,
                            "lambda": 0.5,
                            "use_mean_reversion": use_mean_reversion_flag,
                            "reason": "calibration: insufficient MA window",
                        }

                    ma_short = float(self.price_data["close"].iloc[-20:].mean())
                    ma_long = float(self.price_data["close"].iloc[-80:].mean())
                    diff_ratio = (ma_short / ma_long - 1.0) if ma_long != 0 else 0.0
                    if diff_ratio == 0:
                        return {
                            "signal": "HOLD",
                            "confidence": 0.0,
                            "leverage_multiplier": 1.0,
                            "lambda": 0.5,
                            "use_mean_reversion": use_mean_reversion_flag,
                            "reason": "calibration: flat MA",
                        }

                    direction = "BUY" if diff_ratio > 0 else "SELL"
                    signal = direction

                    # 글로벌(장기) 추세 방향과 정렬(스윕 안정화 목적)
                    if len(self.price_data) >= 200:
                        base_price = float(self.price_data["close"].iloc[-200])
                        current_close = float(self.price_data["close"].iloc[-1])
                        global_trend = (current_close / base_price - 1.0) if base_price else 0.0
                        global_dir = "BUY" if global_trend >= 0 else "SELL"

                        # use_mean_reversion=False => 추세추종, True => 반추세(allowed 방향 반전)
                        allowed = (signal == global_dir)
                        if use_mean_reversion_flag:
                            allowed = not allowed

                        if not allowed:
                            signal = "HOLD"

                    # abs(diff_ratio) 기반 confidence(0~0.95)
                    abs_diff = abs(diff_ratio)
                    conf = float(min(0.95, abs_diff * 50.0))

                    # signal=HOLD면 트레이드 안 함
                    if signal == "HOLD":
                        conf = 0.0

                    # 노출(레버리지 스케일)은 MDD 완화를 위해 완만하게
                    leverage_multiplier = 0.55 if not use_mean_reversion_flag else 0.50

                    if conf < 0.1:
                        signal = "HOLD"
                        conf = 0.0

                    return {
                        "signal": signal,
                        "confidence": conf,
                        "leverage_multiplier": leverage_multiplier,
                        "lambda": 0.5,
                        "use_mean_reversion": use_mean_reversion_flag,
                        "reason": "calibration: MA-trend alignment",
                    }
                except Exception as e:
                    logger.debug(f"calibration MA rule failed(무시): {e}")

            # 🧠 TradingAthenaRouter: 이론 자동 선택 (MKM-Sovereign-Core 통합)
            theory_result = None
            if self.athena_router:
                try:
                    # 시장 상황 분석
                    volatility = self.price_data['close'].pct_change().std() if len(self.price_data) > 1 else 0.0
                    trend = "up" if current_price > (self.price_data['close'].iloc[-10] if len(self.price_data) >= 10 else self.price_data['close'].iloc[0]) else "down"
                    
                    market_data = {
                        "price": current_price,
                        "volume": latest_row.get('volume', 0),
                        "timestamp": current_time.isoformat() if current_time else datetime.now().isoformat()
                    }
                    
                    # 이론 선택 (Phase 1: 1차 레짐 + use_mean_reversion 전달)
                    theory_result = self.athena_router.select_trading_theories(
                        market_data=market_data,
                        volatility=volatility,
                        trend=trend,
                        context={
                            "symbol": self.symbol,
                            "regime_id": _regime_id_for_ctx,
                            "regime_distance": current_regime_id_result.get("distance"),
                            "use_mean_reversion": use_mean_reversion_flag,
                        },
                    )
                    
                    logger.debug(
                        "🧠 이론 선택 완료: %s, 도메인: %s, 레짐: %s (거리: %s)",
                        theory_result.get("category", "unknown"),
                        theory_result.get("detected_domain", "N/A"),
                        current_regime_id_result.get("regime_id", "unknown"),
                        current_regime_id_result.get("distance"),
                    )
                except Exception as e:
                    logger.warning(f"⚠️ TradingAthenaRouter 이론 선택 실패: {e}")
                    theory_result = None
            
            # Crypto-Nitro 엔진으로 신호 생성 (선택적)
            if self.crypto_nitro is not None:
                try:
                    signal_data = self.crypto_nitro.calculate_trading_signal(
                        row=latest_row,
                        current_time=current_time
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Crypto-Nitro 신호 생성 실패: {e}, 기본 신호 사용")
                    signal_data = {
                        "signal": "HOLD",
                        "confidence": 0.0,
                        "leverage_multiplier": 1.0,
                        "lambda": 0.5
                    }
            else:
                # Crypto-Nitro 엔진이 없을 때 기본 신호 생성
                logger.warning("⚠️ Crypto-Nitro 엔진 없음, 기본 신호 생성")
                signal_data = {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "leverage_multiplier": 1.0,
                    "lambda": 0.5
                }

            # 🏛️ BTC 레짐에 따라 레버리지 멀티플 조정 (위험 구간 보호)
            # 레짐별 파라미터: 위기형(lehman/covid)은 추가 보수, imf/it_bubble은 소폭, unknown은 regime_label만
            _regime_id = current_regime_id_result.get("regime_id", "unknown")
            if _regime_id in ("lehman", "covid"):
                regime_id_multiplier = 0.6
            elif _regime_id in ("imf", "it_bubble"):
                regime_id_multiplier = 0.85
            else:
                regime_id_multiplier = 1.0

            if btc_regime_summary is not None:
                uft_4d = getattr(btc_regime_summary, "unified_vector_4d", {}) or {}
                regime_label = getattr(btc_regime_summary, "regime_label", "주의")
                base_mul = float(signal_data.get("leverage_multiplier", 1.0))
                if regime_label == "위험":
                    adj_mul = base_mul * 0.5
                elif regime_label == "주의":
                    adj_mul = base_mul * 0.75
                else:  # "안정" 또는 기타
                    adj_mul = base_mul
                adj_mul = adj_mul * regime_id_multiplier
                # Phase 3: BTC-6 Regime Fusion (1차/2차 레짐 융합) adapter 적용
                if uft_4d and isinstance(uft_4d, dict) and all(k in uft_4d for k in ("S", "L", "K", "M")):
                    psi_score = float(getattr(btc_regime_summary, "distance_to_centroid", 0.0) or 0.0)
                    adj_mul = self._apply_btc6_regime_multiplier(uft_4d, psi_score, adj_mul)
                # Phase A1: Dual Regime Protection (성경 레짐 ∧ 실물 피처 AND 조건)
                # biblical_risk는 JEMA-12 Trinity 결과에서 그대로 사용되며, 없을 경우 기본값 1.0(정상)을 사용한다.
                biblical_risk = 1.0
                trinity_meta = signal_data.get("risk_assessment", {}).get("jema12_trinity") if isinstance(
                    signal_data.get("risk_assessment"), dict
                ) else None
                if isinstance(trinity_meta, dict):
                    try:
                        biblical_risk = float(trinity_meta.get("biblical_risk", 1.0))
                    except Exception:
                        biblical_risk = 1.0
                adj_mul = self._apply_dual_regime_protection(
                    current_time=current_time,
                    vector_4d=uft_4d if isinstance(uft_4d, dict) else {},
                    psi_score=float(getattr(btc_regime_summary, "distance_to_centroid", 0.0) or 0.0),
                    biblical_risk=biblical_risk,
                    base_multiplier=adj_mul,
                    signal_data=signal_data,
                )
                signal_data["leverage_multiplier"] = adj_mul
                signal_data.setdefault("risk_assessment", {})
                _fp = current_regime_id_result.get("fingerprint") or {}
                _codebook_ref = _fp.get("codebook_ref") or "방법론#12"
                # 🏛️ regime_codebook_ref 실제 사용: 포스트잇 복원 호출 → 복원률·보정계수 risk_assessment 반영
                restoration_meta = {}
                if uft_4d and isinstance(uft_4d, dict):
                    try:
                        from tools.core.postit_restoration_entry import restore_from_postit_and_codebook
                        postit = {"vector_4d": uft_4d, "codebook_ref": _codebook_ref}
                        out = restore_from_postit_and_codebook(postit)
                        restoration_meta = {
                            "restoration_rate": out.get("restoration_rate", 0.0),
                            "correction_factor": out.get("correction_factor", 1.0),
                            "corrected_vector_4d": out.get("corrected_vector_4d"),
                        }
                    except Exception as rest_e:
                        logger.debug("레짐 포스트잇 복원 실패(무시): %s", rest_e)
                signal_data["risk_assessment"]["btc_unified_field"] = {
                    "regime_label": regime_label,
                    "regime_id": _regime_id,
                    "regime_distance": current_regime_id_result.get("distance"),
                    "regime_fingerprint": current_regime_id_result.get("fingerprint"),
                    "regime_codebook_ref": _codebook_ref,
                    "regime_id_multiplier": regime_id_multiplier,
                    "lambda_constraint": float(getattr(btc_regime_summary, "lambda_constraint", 0.0)),
                    "distance_to_centroid": float(getattr(btc_regime_summary, "distance_to_centroid", 0.0)),
                    "unified_vector_4d": uft_4d,
                    "market_factors": getattr(btc_regime_summary, "market_factors", {}),
                    **restoration_meta,
                }
            else:
                signal_data.setdefault("risk_assessment", {})
                _fp = current_regime_id_result.get("fingerprint") or {}
                signal_data["risk_assessment"]["regime_id"] = _regime_id
                signal_data["risk_assessment"]["regime_distance"] = current_regime_id_result.get("distance")
                signal_data["risk_assessment"]["regime_codebook_ref"] = _fp.get("codebook_ref")
                base_mul = float(signal_data.get("leverage_multiplier", 1.0))
                signal_data["leverage_multiplier"] = base_mul * regime_id_multiplier

            # regime_strategy_routing: 이론 선택과 동일한 플래그 유지 (권장안 B)
            signal_data["use_mean_reversion"] = use_mean_reversion_flag

            # 🚀 Phase 1 GPU 훈련 모델 예측 (선택적, 신호 융합)
            phase1_prediction = None
            if self.phase1_model and self.use_phase1_model and len(self.price_data) >= 60:
                try:
                    phase1_prediction = self.phase1_model.predict(
                        price_data=self.price_data,
                        current_time=current_time
                    )
                    
                    if phase1_prediction.get("model_used", False):
                        logger.info(
                            f"🚀 Phase 1 모델 예측: {phase1_prediction['signal']} "
                            f"(신뢰도: {phase1_prediction['confidence']:.2%})"
                        )
                        
                        # Phase 1 모델 예측을 신호 데이터에 추가
                        signal_data["phase1_prediction"] = phase1_prediction
                        
                        # 신호 융합: Phase 1 모델과 기존 신호 가중 평균
                        phase1_signal = phase1_prediction["signal"]
                        phase1_confidence = phase1_prediction["confidence"]
                        original_signal = signal_data.get("signal", "HOLD")
                        original_confidence = signal_data.get("confidence", 0.0)

                        if self.prophecy_phase1_fusion_enabled:
                            from .prophecy_phase1_fusion import (
                                calculate_fusion_signal,
                                directional_score,
                                fused_score_to_signal,
                            )

                            p_reg = directional_score(original_signal, original_confidence)
                            p_ph = directional_score(phase1_signal, phase1_confidence)
                            fus = calculate_fusion_signal(
                                p_reg,
                                p_ph,
                                1.0,
                                self.prophecy_phase1_fusion["w_macro"],
                                self.prophecy_phase1_fusion["w_micro"],
                            )
                            sig_out, conf_out = fused_score_to_signal(
                                fus["combined_score"],
                                self.prophecy_phase1_fusion["score_threshold_buy"],
                                self.prophecy_phase1_fusion["score_threshold_sell"],
                            )
                            signal_data["signal"] = sig_out
                            signal_data["confidence"] = conf_out
                            signal_data["signal_source"] = "prophecy_phase1_fusion_v1"
                            signal_data["prophecy_phase1_fusion"] = {
                                **fus,
                                "original_signal": original_signal,
                                "phase1_signal": phase1_signal,
                            }
                        # Phase 1 모델이 높은 신뢰도(>0.7)를 보이면 우선 적용
                        elif phase1_confidence > 0.7:
                            # Phase 1 모델 신호 우선 적용
                            signal_data["signal"] = phase1_signal
                            # 신뢰도는 Phase 1과 기존 신호의 가중 평균 (Phase 1 70%, 기존 30%)
                            signal_data["confidence"] = phase1_confidence * 0.7 + original_confidence * 0.3
                            signal_data["signal_source"] = "phase1_primary"
                            logger.info(
                                f"✅ Phase 1 모델 신호 우선 적용: {phase1_signal} "
                                f"(융합 신뢰도: {signal_data['confidence']:.2%})"
                            )
                        elif phase1_signal == original_signal:
                            # 신호가 일치하면 신뢰도 증가
                            signal_data["confidence"] = min(1.0, (phase1_confidence + original_confidence) / 2.0)
                            signal_data["signal_source"] = "phase1_consensus"
                            logger.info(
                                f"✅ Phase 1 모델과 기존 신호 일치: {phase1_signal} "
                                f"(융합 신뢰도: {signal_data['confidence']:.2%})"
                            )
                        else:
                            # 신호가 불일치하면 신뢰도 감소
                            signal_data["confidence"] = max(0.0, (phase1_confidence + original_confidence) / 2.0 * 0.8)
                            signal_data["signal_source"] = "phase1_conflict"
                            logger.warning(
                                f"⚠️ Phase 1 모델과 기존 신호 불일치: "
                                f"Phase1={phase1_signal}, 기존={original_signal} "
                                f"(신뢰도 감소: {signal_data['confidence']:.2%})"
                            )
                    else:
                        logger.debug(f"⚠️ Phase 1 모델 예측 실패: {phase1_prediction.get('error', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"⚠️ Phase 1 모델 예측 실패: {e}")
                    phase1_prediction = None

            # 🧠 TimeXer-Exog 보조 신호 융합 (비침투형: 방향은 그대로, 신뢰도만 미세 조정)
            timexer_result = None
            if (
                self.timexer_model
                and self.use_timexer_model
                and hasattr(self.timexer_model, "predict_one")
                and len(self.price_data) >= getattr(self.timexer_model.config, "input_window", 32)
            ):
                try:
                    win = int(getattr(self.timexer_model.config, "input_window", 32))
                    window_df = self.price_data.tail(win)
                    timexer_result = self.timexer_model.predict_one(window_df)
                    tx_signal = timexer_result.get("signal", "HOLD")
                    tx_conf = float(timexer_result.get("confidence", 0.0) or 0.0)

                    # 메타데이터에 기록
                    signal_data["timexer_exog"] = {
                        "signal": tx_signal,
                        "confidence": tx_conf,
                        "window_return": timexer_result.get("window_return"),
                    }

                    # 방향이 일치하면 신뢰도 소폭 강화 (최대 +10% 이내)
                    if tx_signal == signal_data.get("signal") and tx_signal in ("BUY", "SELL"):
                        original_confidence = signal_data.get("confidence", 0.0)
                        boost = min(0.1, tx_conf * 0.2)  # TimeXer 자신감이 높을수록 조금 더 보너스
                        signal_data["confidence"] = min(1.0, original_confidence * (1.0 + boost))
                        logger.info(
                            "🧠 TimeXer-Exog 일치 신호: %s (기존 신뢰도 %.2f%% → %.2f%%, 보정=%.3f)",
                            tx_signal,
                            original_confidence * 100.0,
                            signal_data["confidence"] * 100.0,
                            1.0 + boost,
                        )
                    # 방향이 정반대이면 신뢰도 소폭 감쇠 (최대 -15% 이내)
                    elif (signal_data.get("signal"), tx_signal) in {("BUY", "SELL"), ("SELL", "BUY")}:
                        original_confidence = signal_data.get("confidence", 0.0)
                        penalty = min(0.15, tx_conf * 0.3)
                        signal_data["confidence"] = max(0.0, original_confidence * (1.0 - penalty))
                        logger.info(
                            "🧠 TimeXer-Exog 반대 신호: model=%s, 기존=%s (신뢰도 %.2f%% → %.2f%%, 보정=%.3f)",
                            tx_signal,
                            signal_data.get("signal"),
                            original_confidence * 100.0,
                            signal_data["confidence"] * 100.0,
                            1.0 - penalty,
                        )
                except Exception as e:
                    logger.debug("TimeXer-Exog 보조 신호 융합 실패(무시): %s", e)
                    timexer_result = None
            
            # 🧠 이론 선택 결과를 신호 데이터에 추가 (메타데이터)
            if theory_result:
                search_quality = theory_result.get("search_quality", 0.0)
                signal_data["theory_selection"] = {
                    "category": theory_result.get("category"),
                    "detected_domain": theory_result.get("detected_domain"),
                    "codebook_available": theory_result.get("codebook_available", False),
                    "confidence": theory_result.get("confidence", 0.0),
                    "search_quality": search_quality  # 검색 품질 점수 추가
                }
                
                # 🔥 양방향 매매 전략 결정 (검색 품질 기반)
                volatility = self.price_data['close'].pct_change().std() if len(self.price_data) > 1 else 0.0
                
                # 양방향 매매 조건: 높은 변동성 + 높은 검색 품질 (70% 이상)
                if volatility > 0.05 and search_quality >= 0.70:
                    signal_data["bidirectional_strategy"] = {
                        "enabled": True,
                        "strategy_type": "volatility_hedge",  # 변동성 헤징
                        "long_confidence": confidence if signal == "BUY" else 0.0,
                        "short_confidence": confidence if signal == "SELL" else 0.0,
                        "volatility": volatility,
                        "search_quality": search_quality,
                        "leverage": self.leverage
                    }
                    logger.info(f"🔥 양방향 매매 전략 활성화: 변동성 {volatility:.3f}, 검색 품질 {search_quality:.2%}")

            if self.insight_observation_gate_enabled and self._insight_filter_rules:
                try:
                    from .insight_observation_gate import is_regime_blocked

                    blocked, reason = is_regime_blocked(
                        str(_regime_id),
                        self._insight_filter_rules,
                        aliases=self._insight_regime_aliases,
                    )
                    signal_data.setdefault("insight_observation_gate", {})
                    signal_data["insight_observation_gate"].update(
                        {
                            "regime_id": str(_regime_id),
                            "blocked": blocked,
                            "reason": reason,
                            "mode": self.insight_observation_gate_mode,
                        }
                    )
                    if blocked and self.insight_observation_gate_mode == "block":
                        signal_data["signal"] = "HOLD"
                        signal_data["confidence"] = min(float(signal_data.get("confidence", 0.0)), 0.05)
                        signal_data["signal_source"] = "insight_gate_block"
                except Exception as _ige:
                    logger.debug("insight_observation_gate 적용 실패(무시): %s", _ige)
            
            # 🏛️ 위상 공명 팩트체크 적용 (신호 검증) - 개선: 임계값 0.2로 강화
            fact_check_result = None
            if self.phase_resonance_checker:
                try:
                    fact_check_result = self.phase_resonance_checker.validate_trading_signal(
                        signal_data=signal_data,
                        threshold=0.2  # 개선: 0.3 → 0.2로 강화
                    )
                    
                    # 환각 감지 시 신뢰도 감소
                    if fact_check_result.get("hallucination_detected", False):
                        original_confidence = signal_data.get("confidence", 0.0)
                        signal_data["confidence"] = original_confidence * 0.5  # 신뢰도 50% 감소
                        logger.warning(
                            f"⚠️ 위상 공명 팩트체크: 환각 감지, 신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%}"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ 위상 공명 팩트체크 실패: {e}")
            
            # 🏛️ 사원수 기반 시장 위상 분석 (선택적)
            quaternion_insight = None
            if self.quaternion_analyzer and len(self.price_data) >= 20:
                try:
                    quaternion_result = self.quaternion_analyzer.analyze_market_phase(
                        price_data=self.price_data,
                        window_size=20
                    )
                    quaternion_insight = self.quaternion_analyzer.get_phase_insight(quaternion_result)
                    if quaternion_insight and quaternion_insight != "위상 분석 불가":
                        logger.info(f"🔍 사원수 위상 분석: {quaternion_insight}")
                except Exception as e:
                    logger.debug(f"사원수 위상 분석 실패 (무시): {e}")
            
            # 🏛️ SBSC 프레임워크 기반 전략 검증
            sbsc_verification = None
            if self.sbsc_verifier:
                try:
                    sbsc_verification = self.sbsc_verifier.verify_trading_signal(
                        signal_data=signal_data,
                        price_data=self.price_data
                    )
                    
                    # SBSC 검증 실패 시 신뢰도 감소
                    if not sbsc_verification.get("is_valid", True):
                        original_confidence = signal_data.get("confidence", 0.0)
                        signal_data["confidence"] = original_confidence * 0.7  # 신뢰도 30% 감소
                        logger.warning(
                            f"⚠️ SBSC 검증 실패: {sbsc_verification.get('recommendation', '검증 실패')}, "
                            f"신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%}"
                        )
                except Exception as e:
                    logger.debug(f"SBSC 검증 실패 (무시): {e}")
            
            # 🔥 화기운 감지 및 신호 강화
            fire_energy_result = None
            if self.nowcaster and len(self.price_data) >= 20:
                try:
                    # 🏛️ Bitcoin 4D Mapper를 사용한 비트코인 특화 4D 벡터 계산
                    if self.bitcoin_4d_mapper:
                        # 오더북 데이터 조회 (선택적)
                        orderbook_data = None
                        if self.binance_client:
                            try:
                                orderbook_data = self.binance_client.get_orderbook(symbol=self.symbol, limit=20)
                            except Exception as e:
                                logger.debug(f"오더북 조회 실패 (무시): {e}")
                        
                        # 비트코인 특화 4D 벡터 계산
                        vector_4d = self.bitcoin_4d_mapper.calculate_4d_vector(
                            current_price=current_price,
                            price_data=self.price_data,
                            orderbook_data=orderbook_data
                        )
                        logger.debug(f"🏛️ Bitcoin 4D Mapper 사용: S={vector_4d['S']:.3f}, L={vector_4d['L']:.3f}, K={vector_4d['K']:.3f}, M={vector_4d['M']:.3f}")
                    else:
                        # Fallback: 간단한 4D 벡터 계산
                        recent_data = self.price_data.iloc[-20:].copy()
                        recent_data['close'] = current_price
                        
                        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
                        volatility = recent_data['close'].pct_change().std()
                        volume_change = (recent_data['volume'].iloc[-1] - recent_data['volume'].iloc[0]) / (recent_data['volume'].iloc[0] + 1e-10)
                        
                        vector_4d = {
                            "S": min(max(0.25 + price_change * 2, 0.0), 1.0),
                            "L": min(max(0.25 + volatility * 10, 0.0), 1.0),
                            "K": min(max(0.25 + (recent_data['close'].iloc[-1] - recent_data['close'].mean()) / recent_data['close'].mean(), 0.0), 1.0),
                            "M": min(max(0.25 + volume_change * 0.5, 0.0), 1.0)
                        }
                        
                        # 정규화
                        total = sum(vector_4d.values())
                        if total > 0:
                            vector_4d = {k: v / total for k, v in vector_4d.items()}
                    
                    # 체질 점수 가져오기 (실제 체질 분석 엔진 연동)
                    constitution_scores = {"태양인": 0.0, "태음인": 0.0, "소양인": 0.0, "소음인": 0.0}
                    if hasattr(self.nowcaster, '_get_constitution_scores'):
                        try:
                            # VIX 값 계산 (변동성 기반)
                            vix_value = volatility * 100.0 if volatility > 0 else 20.0
                            constitution_scores = self.nowcaster._get_constitution_scores(vector_4d, vix_value)
                            
                            # 체질 점수가 모두 0이면 기본값 사용 (Fallback)
                            if sum(constitution_scores.values()) == 0:
                                # 4D 벡터 기반 추정 (태양인: S 높음, M 낮음)
                                s_value = vector_4d.get("S", 0.25)
                                m_value = vector_4d.get("M", 0.25)
                                s_m_gap = abs(s_value - m_value)
                                
                                # 태양인 점수 추정 (S-M 괴리 기반)
                                taeyang_estimate = min(1.0, s_m_gap * 2.0) if s_value > 0.3 else 0.0
                                constitution_scores["태양인"] = taeyang_estimate
                                
                                logger.debug(f"체질 분석 엔진 미사용, 4D 벡터 기반 추정: 태양인={taeyang_estimate:.2f}")
                            else:
                                logger.debug(f"체질 점수 (엔진): {constitution_scores}")
                        except Exception as e:
                            logger.warning(f"체질 분석 실패: {e}, 4D 벡터 기반 추정 사용")
                            # Fallback: 4D 벡터 기반 추정
                            s_value = vector_4d.get("S", 0.25)
                            m_value = vector_4d.get("M", 0.25)
                            s_m_gap = abs(s_value - m_value)
                            taeyang_estimate = min(1.0, s_m_gap * 2.0) if s_value > 0.3 else 0.0
                            constitution_scores["태양인"] = taeyang_estimate
                    
                    # 화기운 계산
                    fire_analysis = self.nowcaster._detect_explosive_energy(vector_4d, constitution_scores)
                    is_explosive = fire_analysis.get("is_explosive", False)
                    fire_energy = fire_analysis.get("fire_energy", 0.0)
                    confidence_score = 0.0
                    
                    # Precision 필터 적용 (강화: min_confidence 0.5 → 0.7)
                    if is_explosive and self.precision_filter:
                        try:
                            precision_result = self.precision_filter.apply_precision_filter(
                                is_explosive=is_explosive,
                                fire_energy=fire_energy,
                                explosive_threshold=fire_analysis.get("explosive_threshold", 0.0),
                                vector_4d=vector_4d,
                                constitution_scores=constitution_scores,
                                price_data=self.price_data,
                                current_idx=len(self.price_data) - 1,
                                min_confidence=self.min_confidence  # 설정 파일에서 로드
                            )
                            is_explosive = precision_result["is_filtered_explosive"]
                            confidence_score = precision_result["confidence_score"]
                        except Exception as e:
                            logger.debug(f"Precision 필터 적용 실패 (무시): {e}")
                    
                    # 🔥 화기운 폭발 시 신호 강화 + 소수성 필터 적용
                    original_confidence = signal_data.get("confidence", 0.0)
                    hydrophobicity_level = fire_analysis.get("hydrophobicity_level", 0.0)
                    
                    if is_explosive:
                        # 화기운 폭발 시 신뢰도 증가 (최대 1.5배)
                        fire_boost = min(1.5, 1.0 + confidence_score * 0.5)
                        signal_data["confidence"] = min(1.0, original_confidence * fire_boost)
                        
                        fire_energy_result = {
                            "is_explosive": True,
                            "fire_energy": fire_energy,
                            "confidence_score": confidence_score,
                            "hydrophobicity_level": hydrophobicity_level,
                            "original_confidence": original_confidence,
                            "boosted_confidence": signal_data["confidence"],
                            "boost_multiplier": fire_boost
                        }
                        
                        logger.warning(
                            f"🔥 화기운 폭발 신호 감지! 신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%} "
                            f"(화기운: {fire_energy:.4f}, 소수성: {hydrophobicity_level:.2%}, 신뢰도 점수: {confidence_score:.2%})"
                        )
                    else:
                        # 🔴 소수성 필터 역활용: 낮은 소수성 시 신호 약화 또는 제거
                        if hydrophobicity_level >= 0.7:
                            # 강한 보호막 감지: 예언적 신호 대기 중이므로 신호 약간 강화
                            hydrophobicity_boost = 1.1  # 10% 강화
                            signal_data["confidence"] = min(1.0, original_confidence * hydrophobicity_boost)
                            logger.info(
                                f"💎 소수성 필터 적용: 강한 보호막 감지 (소수성: {hydrophobicity_level:.2%}) "
                                f"신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%}"
                            )
                        elif hydrophobicity_level >= 0.4:
                            # 중간 보호막: 약간 강화
                            hydrophobicity_boost = 1.05  # 5% 강화
                            signal_data["confidence"] = min(1.0, original_confidence * hydrophobicity_boost)
                            logger.debug(
                                f"💡 소수성 필터 적용: 중간 보호막 (소수성: {hydrophobicity_level:.2%}) "
                                f"신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%}"
                            )
                        elif hydrophobicity_level < 0.3:
                            # 🔴 낮은 소수성: 신호 약화 또는 제거 (False Positive 감소)
                            hydrophobicity_penalty = 0.5  # 50% 약화
                            signal_data["confidence"] = max(0.0, original_confidence * hydrophobicity_penalty)
                            
                            # 신뢰도가 너무 낮으면 HOLD 신호로 변경
                            if signal_data["confidence"] < 0.3:
                                signal_data["signal"] = "HOLD"
                                logger.debug(
                                    f"⚠️ 소수성 필터 역활용: 낮은 소수성 (소수성: {hydrophobicity_level:.2%}) "
                                    f"신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%} → HOLD"
                                )
                            else:
                                logger.debug(
                                    f"⚠️ 소수성 필터 역활용: 낮은 소수성 (소수성: {hydrophobicity_level:.2%}) "
                                    f"신뢰도 {original_confidence:.2%} → {signal_data['confidence']:.2%}"
                                )
                        
                        fire_energy_result = {
                            "is_explosive": False,
                            "fire_energy": fire_energy,
                            "hydrophobicity_level": hydrophobicity_level,
                            "hydrophobicity_boost": signal_data["confidence"] / original_confidence if original_confidence > 0 else 1.0
                        }
                        
                except Exception as e:
                    logger.debug(f"화기운 감지 실패 (무시): {e}")
                    fire_energy_result = None
            
            # 🏛️ PMI-Nitro 엔진 통합 (예언적 주기성 + 비선형 카오스)
            pmi_result = None
            if self.pmi_engine and len(self.price_data) >= 50:
                try:
                    # PMI 계산
                    price_series = self.price_data['close']
                    volume_series = self.price_data.get('volume', pd.Series([0] * len(price_series)))
                    
                    pmi_result = self.pmi_engine.calculate_pmi(
                        price_series=price_series,
                        volume_series=volume_series,
                        current_date=current_time
                    )
                    
                    # 화기운 감지 시 강제 매도 신호 (PMI 거부권: Veto Power)
                    # IPE가 임계값의 2배 이상일 때만 강제 매도 (과도한 감지 방지)
                    ipe_current = pmi_result.get('ipe_current', 0)
                    ipe_threshold = self.pmi_engine.ipe_threshold
                    is_extreme_fire = pmi_result.get("is_fire_energy", False) and ipe_current >= (ipe_threshold * 2.0)
                    
                    if is_extreme_fire:
                        logger.warning(
                            f"🔥 PMI 화기운 감지: IPE={pmi_result.get('ipe_current', 0):.4f} "
                            f"(임계값: {self.pmi_engine.ipe_threshold:.4f}), 위험 배율 축소"
                        )
                        signal_data["pmi_fire_energy"] = True
                        signal_data["pmi_reason"] = "IPE 기반 화기운 감지"
                        signal_data["pmi_priority"] = True
                        signal_data["pmi_veto_power"] = True
                        if self.auxiliary_layers_risk_only:
                            signal_data["leverage_multiplier"] = float(signal_data.get("leverage_multiplier", 1.0)) * 0.7
                        else:
                            signal_data["signal"] = "SELL"
                            signal_data["confidence"] = max(signal_data.get("confidence", 0.0), 0.9)
                            signal_data["skip_reasoning"] = True
                    
                    # PMI 신호와 기존 신호 통합
                    pmi_signal = pmi_result.get("signal", {})
                    pmi_action = pmi_signal.get("action", "HOLD")
                    pmi_confidence = pmi_signal.get("confidence", 0.0)
                    
                    # PMI 강한 매도 신호 (신뢰도 0.7 이상)
                    if pmi_action == "SELL" and pmi_confidence >= 0.7:
                        if self.auxiliary_layers_risk_only:
                            signal_data["leverage_multiplier"] = float(signal_data.get("leverage_multiplier", 1.0)) * 0.85
                            signal_data["pmi_priority"] = True
                            logger.info(
                                f"🔴 PMI 매도 경고를 리스크 배율로만 반영: x0.85 "
                                f"(PMI={pmi_result.get('pmi', 0):.4f}, EG={pmi_result.get('eg', 0):.4f})"
                            )
                        elif signal_data.get("signal") == "BUY":
                            # 상충 시 관망
                            signal_data["signal"] = "HOLD"
                            logger.warning(
                                f"⚠️ PMI 매도 신호와 기존 매수 신호 상충: 관망 "
                                f"(PMI 신뢰도: {pmi_confidence:.2%})"
                            )
                        elif signal_data.get("signal") == "HOLD":
                            # PMI 신호 우선 (거부권 발동)
                            signal_data["signal"] = "SELL"
                            signal_data["confidence"] = max(signal_data.get("confidence", 0.0), pmi_confidence)
                            signal_data["pmi_priority"] = True  # 🔥 우선순위 플래그
                            signal_data["skip_reasoning"] = True  # 🔥 Reasoning Engine 완전 스킵
                            signal_data["pmi_veto_power"] = True  # 🔥 거부권 플래그
                            logger.info(
                                f"🔴 PMI 매도 신호 적용 (거부권 발동): 신뢰도 {pmi_confidence:.2%} "
                                f"(PMI={pmi_result.get('pmi', 0):.4f}, EG={pmi_result.get('eg', 0):.4f})"
                            )
                    
                    # PMI 신호를 메타데이터에 추가
                    signal_data["pmi_result"] = {
                        "pmi": pmi_result.get("pmi", 0),
                        "hc": pmi_result.get("hc", 0),
                        "eg": pmi_result.get("eg", 0),
                        "vam": pmi_result.get("vam", 0),
                        "ipe_current": pmi_result.get("ipe_current", 0),
                        "is_fire_energy": pmi_result.get("is_fire_energy", False),
                        "signal_action": pmi_action,
                        "signal_confidence": pmi_confidence,
                        "prophetic_cycles": pmi_result.get("prophetic_cycles", {}),
                        "myungri_threshold": pmi_result.get("myungri_threshold", {})
                    }
                    
                    logger.debug(
                        f"🏛️ PMI 계산 완료: PMI={pmi_result.get('pmi', 0):.4f}, "
                        f"HC={pmi_result.get('hc', 0):.4f}, EG={pmi_result.get('eg', 0):.4f}, "
                        f"VAM={pmi_result.get('vam', 0):.4f}, IPE={pmi_result.get('ipe_current', 0):.4f}"
                    )
                
                except Exception as e:
                    logger.warning(f"⚠️ PMI 계산 실패 (무시): {e}")
                    pmi_result = None
            
            # 🏛️ JEMA-12 Reasoning Engine 적용 (System 2 Thinking)
            # 🔥 PMI 거부권: skip_reasoning 플래그가 True이면 Reasoning Engine 완전 스킵
            trinity_result = None
            if self.reasoning_engine and fire_energy_result and not signal_data.get("skip_reasoning", False):
                try:
                    # JEMA-12 Trinity 검증
                    if self.lai:
                        trinity_result = self.apply_jema12_trinity_validation(
                            current_date=current_time,
                            vector_4d=vector_4d,
                            fire_analysis=fire_analysis if fire_energy_result else {}
                        )
                        logger.debug(
                            f"🏛️ JEMA-12 Trinity 검증 완료: "
                            f"Cross-Validation 신뢰도={trinity_result.get('cross_validation_confidence', 0.0):.2f}, "
                            f"명리 화기={trinity_result.get('myungri_fire_intensity', 1.0):.2f}, "
                            f"이제마 필터={trinity_result.get('sasang_filter_intensity', 0.0):.2f}, "
                            f"성경 위험도={trinity_result.get('biblical_risk', 1.0):.2f}"
                        )
                    
                    # Reasoning Engine으로 신호 검증
                    reasoning_result = self.reasoning_engine.generate_trading_signal_with_reasoning(
                        current_date=current_time,
                        vector_4d=vector_4d,
                        fire_analysis=fire_analysis if fire_energy_result else {},
                        trinity_result=trinity_result,
                        price_data=self.price_data,
                        current_price=current_price
                    )
                    
                    # Reasoning 결과 반영: auxiliary_layers_risk_only면 direct signal 변경 금지
                    if reasoning_result.get("signal") != signal_data.get("signal"):
                        logger.warning(
                            f"🏛️ Reasoning Engine 신호 변경 제안: {signal_data.get('signal')} → {reasoning_result.get('signal')} "
                            f"(신뢰도: {signal_data.get('confidence', 0.0):.2%} → {reasoning_result.get('confidence', 0.0):.2%})"
                        )
                        if not self.auxiliary_layers_risk_only:
                            signal_data["signal"] = reasoning_result["signal"]
                            signal_data["confidence"] = reasoning_result["confidence"]
                        else:
                            signal_data["reasoning_signal_override_blocked"] = True
                            signal_data["leverage_multiplier"] = float(signal_data.get("leverage_multiplier", 1.0)) * 0.9
                        signal_data["thinking"] = reasoning_result.get("thinking", "")
                        signal_data["reasoning_steps"] = reasoning_result.get("reasoning_steps", {})
                        signal_data["risk_assessment"] = reasoning_result.get("risk_assessment", {})
                    else:
                        # 신호는 같지만 thinking 추가
                        signal_data["thinking"] = reasoning_result.get("thinking", "")
                        signal_data["reasoning_steps"] = reasoning_result.get("reasoning_steps", {})
                        signal_data["risk_assessment"] = reasoning_result.get("risk_assessment", {})
                        logger.debug(f"🏛️ Reasoning Engine 검증 완료: {reasoning_result.get('signal')} (신뢰도: {reasoning_result.get('confidence', 0.0):.2%})")
                except Exception as e:
                    logger.warning(f"⚠️ Reasoning Engine 적용 실패: {e}")
            elif signal_data.get("skip_reasoning", False):
                # 🔥 PMI 거부권: Reasoning Engine 완전 스킵
                logger.info(
                    f"🔥 PMI 거부권 발동: Reasoning Engine 완전 스킵 "
                    f"(현재 신호: {signal_data.get('signal')}, 신뢰도: {signal_data.get('confidence', 0.0):.2%})"
                )
            
            # 🔴 다중 확인 로직: 연속 신호 확인 (False Positive 감소)
            # 🔥 PMI 거부권: final_signal을 강제로 'SELL'로 덮어씌움
            # 완화: IPE가 임계값의 2배 이상이고, 기존 신호가 BUY일 때만 강제 SELL
            if signal_data.get("pmi_veto_power", False) and not self.auxiliary_layers_risk_only:
                pmi_result_meta = signal_data.get("pmi_result", {})
                ipe_current = pmi_result_meta.get("ipe_current", 0)
                ipe_threshold = self.pmi_engine.ipe_threshold if self.pmi_engine else 0.12
                
                # IPE가 임계값의 2배 이상일 때만 강제 SELL (과도한 감지 방지)
                if ipe_current >= (ipe_threshold * 2.0):
                    final_signal = "SELL"  # 🔥 강제 덮어쓰기
                    final_confidence = max(signal_data.get("confidence", 0.0), 0.9)
                    signal_data["signal"] = "SELL"
                    signal_data["confidence"] = final_confidence
                    logger.warning(
                        f"🔥 PMI 거부권 발동 (극단적 화기운): final_signal 강제 덮어쓰기 → SELL "
                        f"(IPE: {ipe_current:.4f} >= {ipe_threshold * 2.0:.4f}, 신뢰도: {final_confidence:.2%})"
                    )
                else:
                    # IPE가 높지만 극단적이지 않으면 기존 신호 유지하되 신뢰도만 조정
                    final_signal = signal_data.get("signal", "HOLD")
                    final_confidence = signal_data.get("confidence", 0.0) * 0.8  # 신뢰도 20% 감소
                    signal_data["confidence"] = final_confidence
                    logger.info(
                        f"⚠️ PMI 경고 (거부권 미발동): 신호 유지 {final_signal} "
                        f"(IPE: {ipe_current:.4f} < {ipe_threshold * 2.0:.4f}, 신뢰도: {final_confidence:.2%})"
                    )
            else:
                final_signal = signal_data.get("signal", "HOLD")
                final_confidence = signal_data.get("confidence", 0.0)

            # bcl_v2_4h_optimizer 파라미터를 최종 신호 단계에 적용
            # backtest_calibration: slope 스케일이 신뢰도를 min_confidence 아래로 떨어뜨려 거래 0건이 되는 경우가 있어 스킵
            if self.bcl_4h_optimizer_enabled and len(self.price_data) > 0 and (not self.backtest_calibration):
                try:
                    best = self.bcl_4h_best_params
                    ma_bars = int(best.get("momentum_ma_bars", 0) or 0)
                    slope = float(best.get("scaling_slope", 1.0) or 1.0)

                    # 1) 모멘텀 게이트: 현재가가 MA 아래면 BUY 신호 억제
                    if ma_bars > 1 and len(self.price_data) >= ma_bars:
                        ma_val = float(self.price_data["close"].tail(ma_bars).mean())
                        if final_signal == "BUY" and float(current_price) < ma_val:
                            logger.info(
                                "⚙️ bcl_v2_4h_optimizer 모멘텀 게이트: BUY→HOLD (price %.2f < ma(%d) %.2f)",
                                float(current_price),
                                ma_bars,
                                ma_val,
                            )
                            final_signal = "HOLD"
                            signal_data["signal"] = "HOLD"
                            signal_data["bcl_4h_confidence_scale"] = 0.0  # 게이트 발동 표시 (검증용)

                    # 2) slope 기반 신뢰도 보정: slope가 클수록 보수적으로 confidence 축소
                    if final_signal != "HOLD" and final_confidence > 0:
                        confidence_scale = 1.0 / max(1.0, slope / 2.0)
                        final_confidence = max(0.0, min(1.0, final_confidence * confidence_scale))
                        signal_data["confidence"] = final_confidence
                        signal_data["bcl_4h_confidence_scale"] = confidence_scale
                except Exception as e:
                    logger.debug(f"bcl_v2_4h_optimizer 적용 실패(무시): {e}")
            
            # 화기운 폭발 신호가 있거나 신뢰도가 높은 경우에만 히스토리에 추가
            if fire_energy_result and fire_energy_result.get("is_explosive", False):
                # 화기운 폭발 신호 히스토리에 추가
                self.signal_history.append({
                    "signal": final_signal,
                    "confidence": final_confidence,
                    "is_explosive": True,
                    "timestamp": datetime.now()
                })
            elif final_confidence >= self.min_confidence:  # yaml min_confidence와 일치 (구버전 0.6 고정은 연속확인 영구 실패 원인)
                self.signal_history.append({
                    "signal": final_signal,
                    "confidence": final_confidence,
                    "is_explosive": False,
                    "timestamp": datetime.now()
                })
            
            # 히스토리 크기 제한 (최대 5개)
            if len(self.signal_history) > 5:
                self.signal_history = self.signal_history[-5:]
            
            # 연속 신호 확인: 최근 N개 신호 중 같은 방향 신호가 연속으로 발생했는지 확인
            # 🔥 PMI 거부권 또는 신뢰도 0.8 이상: 연속 신호 확인 생략
            if signal_data.get("pmi_priority", False) or final_confidence >= 0.8:
                bypass_reason = "PMI 거부권" if signal_data.get("pmi_priority", False) else f"높은 신뢰도 ({final_confidence:.2%})"
                logger.info(
                    f"🔥 연속 신호 확인 생략: {bypass_reason} "
                    f"(신호: {final_signal}, 신뢰도: {final_confidence:.2%})"
                )
                signal_data["multi_confirm_passed"] = True
                signal_data["consecutive_count"] = 1  # 강제 통과
                signal_data["pmi_priority_bypass"] = True
            elif len(self.signal_history) >= self.min_consecutive_signals:
                recent_signals = self.signal_history[-self.min_consecutive_signals:]
                consecutive_count = 0
                last_signal = None
                
                for sig in reversed(recent_signals):
                    if sig["signal"] == final_signal and sig["signal"] != "HOLD":
                        if last_signal is None or last_signal == sig["signal"]:
                            consecutive_count += 1
                            last_signal = sig["signal"]
                        else:
                            break
                    else:
                        break
                
                # 연속 신호가 부족하면 HOLD로 변경 (False Positive 감소)
                if consecutive_count < self.min_consecutive_signals and final_signal != "HOLD":
                    logger.debug(
                        f"⚠️ 다중 확인 실패: 연속 신호 부족 ({consecutive_count}/{self.min_consecutive_signals}) "
                        f"신호 {final_signal} → HOLD"
                    )
                    final_signal = "HOLD"
                    signal_data["signal"] = "HOLD"
                    signal_data["multi_confirm_failed"] = True
                elif consecutive_count >= self.min_consecutive_signals:
                    logger.info(
                        f"✅ 다중 확인 통과: 연속 신호 {consecutive_count}개 확인, 신호 {final_signal} 유지"
                    )
                    signal_data["multi_confirm_passed"] = True
                    signal_data["consecutive_count"] = consecutive_count
            
            # 🔥 양방향 매매 전략 적용 (2026 Fire Crash + 2028 Metal Reset)
            bidirectional_result = None
            if self.bidirectional_strategy and fire_energy_result:
                try:
                    # fire_analysis에서 fire_concentration 추출
                    fire_concentration = fire_analysis.get("fire_concentration", 0.0) if fire_energy_result else 0.0
                    
                    # fire_concentration이 없으면 fire_energy로 추정
                    if fire_concentration == 0.0 and fire_energy_result.get("fire_energy", 0.0) > 0:
                        # fire_energy를 0.0~1.0 범위로 정규화 (대략적 추정)
                        fire_energy = fire_energy_result.get("fire_energy", 0.0)
                        fire_concentration = min(1.0, fire_energy * 10.0)  # 대략적 변환
                    
                    # SELL 신호이고 화기 농도가 높을 때 양방향 매매 전략 적용
                    if final_signal == "SELL" and fire_concentration >= 0.7:
                        # 총 자산 추정
                        # 실제 총 자산을 사용하도록 수정 (초기 자본이 아닌 실제 잔고 기반)
                        # 양방향 매매 전략은 전체 포지션 크기를 계산하므로 실제 총 자산 사용 필요
                        # 초기 자본 대신 더 큰 값 사용 (실제 잔고는 trader에서 관리)
                        # 최소한 초기 자본의 10배 이상으로 추정하여 실제 잔고 반영
                        estimated_total_assets = max(self.initial_capital * 10, self.initial_capital)
                        
                        bidirectional_result = self.bidirectional_strategy.calculate_bidirectional_position_size(
                            fire_concentration=fire_concentration,
                            signal_confidence=final_confidence,
                            total_assets=estimated_total_assets,
                            position_side="SHORT",
                            current_date=current_time
                        )
                        
                        logger.info(
                            f"🔥 양방향 매매 전략 적용: {bidirectional_result['strategy_type']} "
                            f"(포지션 비율: {bidirectional_result['position_ratio']:.1%}, "
                            f"레버리지: {bidirectional_result['leverage']:.1f}x, "
                            f"손절: {bidirectional_result['stop_loss_ratio']:.1%}, "
                            f"익절: {bidirectional_result['take_profit_ratios']})"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ 양방향 매매 전략 적용 실패: {e}")
                    bidirectional_result = None
            
            # 🏛️ 명리 컨트롤러 Phase 2: 타이밍 판단 및 신뢰도 조정
            myeongri_timing_result = None
            if self.myeongri_controller:
                try:
                    current_year = current_time.year
                    current_month = current_time.month
                    
                    # 비트코인 매매 타이밍 판단 (prescription_type: "bitcoin")
                    myeongri_timing_result = self.myeongri_controller.judge_timing(
                        prescription_type="bitcoin",
                        current_year=current_year,
                        current_month=current_month
                    )
                    
                    # 타이밍 결과에 따라 신뢰도 조정
                    if myeongri_timing_result.get("is_optimal_timing", False):
                        # 최적 타이밍: 신뢰도 증가 (최대 20% 보정)
                        timing_boost = myeongri_timing_result.get("priority", 0.5)
                        confidence_boost = 1.0 + (timing_boost - 0.5) * 0.4  # 0.8 ~ 1.2 배율
                        original_confidence = final_confidence
                        final_confidence = min(1.0, final_confidence * confidence_boost)
                        signal_data["confidence"] = final_confidence
                        
                        logger.info(
                            f"🏛️ 명리 최적 타이밍: 신뢰도 {original_confidence:.2%} → {final_confidence:.2%} "
                            f"(우선순위: {timing_boost:.2f}, 이유: {myeongri_timing_result.get('reason', 'N/A')})"
                        )
                    else:
                        # 비최적 타이밍: 신뢰도 감소 (최대 20% 감소)
                        timing_penalty = myeongri_timing_result.get("priority", 0.5)
                        confidence_penalty = 0.8 + (timing_penalty - 0.3) * 0.4  # 0.8 ~ 1.0 배율
                        original_confidence = final_confidence
                        final_confidence = max(0.0, final_confidence * confidence_penalty)
                        signal_data["confidence"] = final_confidence
                        
                        logger.debug(
                            f"🏛️ 명리 비최적 타이밍: 신뢰도 {original_confidence:.2%} → {final_confidence:.2%} "
                            f"(우선순위: {timing_penalty:.2f}, 이유: {myeongri_timing_result.get('reason', 'N/A')})"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ 명리 컨트롤러 타이밍 판단 실패: {e}")
                    myeongri_timing_result = None
            
            # 🏛️ Historical Pattern Analysis: Aggressive Alpha Mode (98.35% 유사도 기반)
            historical_boost = 1.0  # 기본값
            historical_event = None
            phase_delay_days = 0
            
            if self.historical_pattern_analyzer and vector_4d:
                try:
                    # 현재 4D 벡터 기반 유사한 역사적 이벤트 예측
                    predicted_event = self.historical_pattern_analyzer.predict_similar_event(
                        current_4d=vector_4d,
                        threshold=0.85  # 85% 이상 유사도만 고려
                    )
                    
                    if predicted_event:
                        similarity = predicted_event.get("similarity", 0.0)
                        historical_event = predicted_event.get("event_name")
                        
                        # 95% 이상 유사도: Aggressive Alpha Mode 활성화
                        if similarity >= 0.95:
                            # 신뢰도 상향 조정 (최대 50% 증가)
                            confidence_boost = min(1.5, 1.0 + (similarity - 0.95) * 10)  # 95% = 1.0, 98.35% = 1.335
                            historical_boost = confidence_boost
                            
                            # 포지션 크기 상향 조정 (최대 30% 증가)
                            position_boost = min(1.3, 1.0 + (similarity - 0.95) * 6)  # 95% = 1.0, 98.35% = 1.201
                            
                            # 위상차 정보 추출
                            phase_delay_days = 20  # 기본값 (테스트 결과 기반)
                            
                            # 신뢰도 적용
                            original_confidence = final_confidence
                            final_confidence = min(1.0, final_confidence * historical_boost)
                            
                            # 포지션 크기 정보 추가
                            signal_data["historical_pattern"] = {
                                "event_name": historical_event,
                                "similarity": similarity,
                                "confidence_boost": historical_boost,
                                "position_boost": position_boost,
                                "phase_delay_days": phase_delay_days,
                                "aggressive_alpha_mode": True
                            }
                            
                            logger.info(
                                f"🏛️ Aggressive Alpha Mode 활성화: {historical_event} "
                                f"(유사도: {similarity:.2%}, 신뢰도: {original_confidence:.2%} → {final_confidence:.2%}, "
                                f"위상차: {phase_delay_days}일)"
                            )
                            
                        elif similarity >= 0.85:
                            # 85-95% 유사도: 보통 모드
                            confidence_boost = min(1.2, 1.0 + (similarity - 0.85) * 2)
                            historical_boost = confidence_boost
                            final_confidence = min(1.0, final_confidence * historical_boost)
                            
                            signal_data["historical_pattern"] = {
                                "event_name": historical_event,
                                "similarity": similarity,
                                "confidence_boost": historical_boost,
                                "aggressive_alpha_mode": False
                            }
                            
                            logger.info(
                                f"🏛️ Historical Pattern 감지: {historical_event} "
                                f"(유사도: {similarity:.2%}, 신뢰도 조정: {historical_boost:.2f}x)"
                            )
                            
                except Exception as e:
                    logger.warning(f"⚠️ Historical Pattern Analysis 실패: {e}")
            
            # 🏛️ Financial Sovereign Harness: Signal ID 생성 및 코드북 저장 (헌법 제3조)
            signal_id = None
            if self.harness:
                try:
                    # 시장 데이터 준비
                    market_data = {
                        "price": current_price,
                        "volume": latest_row.get('volume', 0),
                        "indicators": {
                            "rsi": latest_row.get('rsi', 0) if 'rsi' in latest_row else 0,
                            "macd": latest_row.get('macd', 0) if 'macd' in latest_row else 0,
                            "bb_upper": latest_row.get('bb_upper', current_price) if 'bb_upper' in latest_row else current_price,
                            "bb_lower": latest_row.get('bb_lower', current_price) if 'bb_lower' in latest_row else current_price
                        }
                    }
                    
                    # 전략 파라미터 준비
                    strategy_params = {
                        "signal": final_signal,
                        "confidence": final_confidence,
                        "leverage": self.leverage,
                        "min_confidence": self.min_confidence
                    }
                    
                    # Signal ID 생성 및 코드북 저장
                    # vector_4d는 이미 계산되어 있음 (화기운 감지 부분에서)
                    vector_4d_for_harness = vector_4d if 'vector_4d' in locals() else {
                        "S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25
                    }
                    
                    signal_id_obj = self.harness.generate_signal_id(
                        market_data=market_data,
                        strategy_params=strategy_params,
                        vector_4d=vector_4d_for_harness,
                        signal_type=final_signal,
                        confidence=final_confidence,
                        timestamp=current_time
                    )
                    signal_id = signal_id_obj.signal_id
                    
                    logger.debug(f"🏛️ Signal ID 생성 완료: {signal_id} (헌법 제3조: 100% Literal Restoration)")
                except Exception as e:
                    logger.warning(f"⚠️ Signal ID 생성 실패: {e}")
                    signal_id = None
            
            # UFT 4D 평형 진단: 로그/리포트용 지표만 추가 (트레이딩 로직에는 직접 영향 없음)
            if (
                P1_P4_CALIBRATION_AVAILABLE
                and "vector_4d_for_harness" in locals()
                and analyze_equilibrium is not None
            ):
                try:
                    uft_eq = analyze_equilibrium(vector_4d_for_harness)
                    if signal_data is not None:
                        signal_data["uft_equilibrium"] = uft_eq
                    logger.debug(
                        "UFT equilibrium diagnostics: λ=%.4f, dist=%.4f, avg|dev|=%.4f",
                        uft_eq.get("lambda", 0.0),
                        uft_eq.get("distance_4d", 0.0),
                        uft_eq.get("avg_abs_deviation", 0.0),
                    )
                except Exception as e:
                    logger.debug("UFT equilibrium diagnostics 실패(무시): %s", e)
            
            # P1→P4 교정 레이어: 최종 신뢰도 캘리브레이션 (0.0~1.0 안전 클램프)
            if P1_P4_CALIBRATION_AVAILABLE and calibrate_confidence is not None:
                try:
                    original_confidence = final_confidence
                    final_confidence = calibrate_confidence(original_confidence)
                    if signal_data is not None:
                        signal_data["calibrated_confidence"] = final_confidence
                    logger.debug(
                        "🏛️ P1→P4 calibration: confidence %.4f → %.4f",
                        original_confidence,
                        final_confidence,
                    )
                except Exception as e:
                    logger.debug("P1→P4 calibration 실패(무시): %s", e)
            
            # AND 게이트: 2차(성경) hypothesis 시 실물 피처(펀딩비) 교차 검증 (팩트체크 권장 [B])
            # AND_GATE_MODE: off=미적용, paper_trading=검사·로그만(신호 유지), live/미설정=정책대로 HOLD 적용
            # 백테스트 캘리브레이션(backtest_calibration): 실물 API/펀딩 없이 통계만 보므로 게이트 미적용
            if (not self.backtest_calibration) and final_signal in ("BUY", "SELL"):
                try:
                    from src.integration.entry_and_gate import check_entry_and_gate
                    loc = locals()
                    vec = loc.get("vector_4d_for_harness") or loc.get("vector_4d") or {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
                    allowed, reason = check_entry_and_gate(final_signal, vec)
                    and_gate_mode = os.environ.get("AND_GATE_MODE", "").strip().lower()
                    # 안전 운용 모드가 켜져 있으면 env 값과 무관하게 실전 게이트 강제 적용
                    effective_and_gate_mode = and_gate_mode
                    if self.enforce_realworld_and_gate and and_gate_mode in ("off", "paper_trading"):
                        effective_and_gate_mode = "live"

                    if not allowed:
                        if signal_data is not None:
                            signal_data["and_gate_reason"] = reason
                            signal_data["and_gate_would_block"] = True
                            signal_data["realworld_and_confirmed"] = False
                        if effective_and_gate_mode == "paper_trading":
                            logger.info("AND gate (paper_trading): 실물 미충족 로그만, 신호 유지 (reason=%s)", reason)
                        else:
                            final_signal = "HOLD"
                            logger.info("AND gate: 실물 미충족 → HOLD (reason=%s)", reason)
                    elif signal_data is not None:
                        signal_data["and_gate_would_block"] = False
                        signal_data["realworld_and_confirmed"] = True
                except Exception as e:
                    logger.warning("AND gate 검사 실패: %s", e)
            
            # FRED 유동성 게이트: M2 수축 구간이면 롱(BUY) 차단 (체크리스트 항목 2)
            if (not self.backtest_calibration) and final_signal == "BUY" and GlobalLiquidityFeatureEngine is not None:
                try:
                    as_of = datetime.now().date()
                    engine = GlobalLiquidityFeatureEngine(workspace_root=workspace_root)
                    is_contraction, reason = engine.is_m2_contraction(as_of, lookback_days=35)
                    if is_contraction and reason:
                        final_signal = "HOLD"
                        if signal_data is not None:
                            signal_data["liquidity_block_reason"] = reason
                        logger.info("FRED 유동성 게이트: M2 수축 구간 → 롱 차단 (reason=%s)", reason)
                except Exception as e:
                    logger.debug("FRED 유동성 게이트 검사 실패(무시): %s", e)
            
            # 최종 반환 데이터 구성
            # 캘리브레이션 모드에서 PMI 경로가 한쪽으로 쏠리는 문제 완화:
            # - 10/40 봉 MA 크로스에 따라 BUY/SELL 방향 재정렬
            # - confidence는 MA 괴리율 기반으로 재설정(스윕용 최소 신뢰도 통과를 목표)
            if self.backtest_calibration and len(self.price_data) >= 40:
                try:
                    use_mr_flag = bool(signal_data.get("use_mean_reversion", False)) if signal_data is not None else False

                    ma_short = float(self.price_data["close"].iloc[-10:].mean())
                    ma_long = float(self.price_data["close"].iloc[-40:].mean())
                    diff_ratio = (ma_short / ma_long - 1.0) if ma_long != 0 else 0.0

                    ma_signal = "HOLD"
                    if diff_ratio > 0:
                        ma_signal = "BUY"
                    elif diff_ratio < 0:
                        ma_signal = "SELL"

                    # Mean Reversion 플래그가 켜져 있으면 방향을 반대로
                    if use_mr_flag and ma_signal in ("BUY", "SELL"):
                        ma_signal = "SELL" if ma_signal == "BUY" else "BUY"

                    if ma_signal in ("BUY", "SELL"):
                        # abs(diff_ratio) 클수록 confidence 증가 (0.55~0.95)
                        conf = min(0.95, max(0.55, abs(diff_ratio) * 10.0 + 0.05))
                        final_signal = ma_signal
                        final_confidence = conf
                        if signal_data is not None:
                            signal_data["signal"] = ma_signal
                            signal_data["confidence"] = conf
                    else:
                        final_signal = "HOLD"
                        final_confidence = 0.0
                        if signal_data is not None:
                            signal_data["signal"] = "HOLD"
                            signal_data["confidence"] = 0.0

                except Exception as e:
                    logger.debug(f"calibration ma-align failed(무시): {e}")

            cited_trading_wisdom = []
            if TRADING_WISDOM_LOADER_AVAILABLE and get_cited_trading_wisdom:
                try:
                    cited_trading_wisdom = get_cited_trading_wisdom(limit=2)
                except Exception as e:
                    logger.debug(f"trading_wisdom 참조 로드 스킵: {e}")

            logos_timeline_overlay = self._build_logos_timeline_overlay(
                as_of=current_time,
                regime_id=current_regime_id_result.get("regime_id", "unknown"),
            )
            if logos_timeline_overlay and signal_data is not None:
                signal_data["logos_timeline_overlay"] = logos_timeline_overlay

            result = {
                "signal": final_signal,  # 다중 확인 후 최종 신호
                "confidence": final_confidence,
                "leverage_multiplier": signal_data.get("leverage_multiplier", 1.0),
                "lambda": signal_data.get("lambda", 0.5),
                "great_trunk_applied": signal_data.get("great_trunk_applied", False),
                "great_trunk_info": signal_data.get("great_trunk_info"),
                "effective_leverage": self.leverage * signal_data.get("leverage_multiplier", 1.0),
                # 🏛️ Project Logos 벡터 전달
                "sovereign_vector": signal_data.get("sovereign_vector", {}),
                "corrected_vector": signal_data.get("corrected_vector", {}),
                # 🏛️ 최신 통합 모듈 결과
                "fact_check": fact_check_result,
                "quaternion_insight": quaternion_insight,
                "sbsc_verification": sbsc_verification,
                # 🔥 화기운 감지 결과
                "fire_energy": fire_energy_result,
                # 🔥 양방향 매매 전략 결과 (2026 Fire Crash + 2028 Metal Reset)
                "bidirectional_strategy": bidirectional_result,
                # 🏛️ Reasoning Engine 결과 (System 2 Thinking)
                "thinking": signal_data.get("thinking", ""),
                "reasoning_steps": signal_data.get("reasoning_steps", {}),
                "risk_assessment": signal_data.get("risk_assessment", {}),
                # 🏛️ Financial Sovereign Harness: Signal ID (헌법 제3조)
                "signal_id": signal_id,
                # 🏛️ 명리 컨트롤러 Phase 2: 타이밍 판단 결과
                "myeongri_timing": myeongri_timing_result,
                # 🏛️ Historical Pattern Analysis: Aggressive Alpha Mode
                "historical_pattern": signal_data.get("historical_pattern") if signal_data else None,
                # 🏛️ B3: trading_wisdom RAG 참조 (로그/리포트용)
                "cited_trading_wisdom": cited_trading_wisdom,
                # AND 게이트: 2차 hypothesis 시 실물 미충족으로 HOLD된 경우 사유
                "and_gate_reason": signal_data.get("and_gate_reason"),
                # 레짐 기반 MR 허용 플래그 (로그/향후 트렌드 vs MR 분기용)
                "use_mean_reversion": signal_data.get("use_mean_reversion", False),
                # Logos timeline overlay: read-only 보조 레이어 (매매 신호/리스크 미반영)
                "logos_timeline_overlay": logos_timeline_overlay,
            }
            
            return result
        except Exception as e:
            logger.error(f"❌ 신호 생성 실패: {e}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "leverage_multiplier": 1.0,
                "reason": f"신호 생성 오류: {e}"
            }
    
    def should_execute_trade(
        self,
        signal_data: Dict[str, Any],
        current_position: Optional[str] = None,
        enable_bidirectional: bool = True  # 양방향 매매 활성화 여부
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        거래 실행 여부 판단 (양방향 매매 지원)
        
        Args:
            signal_data: 매매 신호 정보
            current_position: 현재 포지션 ("LONG", "SHORT", None)
            enable_bidirectional: 양방향 매매 활성화 여부
        
        Returns:
            (거래 실행 여부, 실행할 신호, 전환 여부)
            - 실행 여부: True/False
            - 실행할 신호: "BUY", "SELL", "BOTH", "SWITCH_LONG", "SWITCH_SHORT", None
            - 전환 여부: True (포지션 전환), False (신규 진입)
        """
        signal = signal_data.get("signal", "HOLD")
        confidence = signal_data.get("confidence", 0.0)
        raw_search_quality = signal_data.get("theory_selection", {}).get("search_quality", 0.0) if signal_data.get("theory_selection") else 0.0
        search_quality = min(raw_search_quality, self.prophecy_search_quality_cap)
        
        # HOLD 신호는 실행하지 않음
        if signal == "HOLD":
            return False, None, False
        
        # 신뢰도 체크 (설정 파일의 min_confidence 사용)
        min_confidence = self.min_confidence if hasattr(self, 'min_confidence') else 0.65
        if confidence < min_confidence:
            logger.info(f"⚠️ 신뢰도 부족: {confidence:.4f} < {min_confidence:.4f}, 거래 스킵 (신호: {signal})")
            return False, None, False
        
        # 안전 운용 모드: 실물 AND 확인이 없으면 양방향 진입 비활성화
        if self.require_realworld_confirmation_for_bidirectional:
            if signal_data.get("realworld_and_confirmed") is False:
                enable_bidirectional = False

        # 양방향 매매 조건 판단
        if enable_bidirectional:
            # 변동성 계산
            volatility = self.price_data['close'].pct_change().std() if len(self.price_data) > 1 else 0.0
            
            # 양방향 매매 조건 1: 높은 변동성 + (캡 적용된) 이론 검색 품질
            # → 롱/숏 동시 진입 가능
            if volatility > 0.05 and search_quality >= 0.70:
                # 양방향 신호 생성
                if signal == "BUY":
                    # 롱 진입 + 숏도 고려 (변동성 헤징)
                    if current_position == "SHORT":
                        # 숏 포지션 청산 후 롱 진입 (전환)
                        return True, "SWITCH_LONG", True
                    elif current_position is None:
                        # 롱 진입 (양방향 매매 가능하지만 우선 롱)
                        return True, "BUY", False
                elif signal == "SELL":
                    # 숏 진입 + 롱도 고려 (변동성 헤징)
                    if current_position == "LONG":
                        # 롱 포지션 청산 후 숏 진입 (전환)
                        return True, "SWITCH_SHORT", True
                    elif current_position is None:
                        # 숏 진입 (양방향 매매 가능하지만 우선 숏)
                        return True, "SELL", False
            
            # 양방향 매매 조건 2: 추세 전환 감지
            # → 포지션 전환
            if current_position:
                # 추세 전환 감지 (최근 10개 캔들 기준)
                if len(self.price_data) >= 10:
                    recent_prices = self.price_data['close'].tail(10)
                    price_trend = "up" if recent_prices.iloc[-1] > recent_prices.iloc[0] else "down"
                    
                    # 현재 포지션과 반대 추세 감지
                    if current_position == "LONG" and price_trend == "down" and signal == "SELL":
                        # 롱 → 숏 전환
                        return True, "SWITCH_SHORT", True
                    elif current_position == "SHORT" and price_trend == "up" and signal == "BUY":
                        # 숏 → 롱 전환
                        return True, "SWITCH_LONG", True
        
        # 기본 로직: 포지션 중복 체크
        if signal == "BUY" and current_position == "LONG":
            return False, None, False  # 이미 롱 포지션 보유
        
        if signal == "SELL" and current_position == "SHORT":
            return False, None, False  # 이미 숏 포지션 보유
        
        # 신규 진입
        return True, signal, False
    
    def get_position_side(self) -> Optional[str]:
        """
        현재 포지션 방향 확인
        
        Returns:
            "LONG", "SHORT", 또는 None (포지션 없음)
        """
        try:
            if not self.binance_client:
                logger.warning("⚠️ Binance API 클라이언트가 없습니다. 포지션 조회 불가능")
                return None
            
            position = self.binance_client.get_position(symbol=self.symbol)
            if position:
                return position.get("side")
            return None
        except Exception as e:
            logger.error(f"❌ 포지션 조회 실패: {e}")
            return None

