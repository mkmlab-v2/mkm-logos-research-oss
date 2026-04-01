#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 통합 실전 거래 모니터링 시스템 (Unified Trading Monitor)

목적: 실전 시장 모니터링 + 비트코인 자동매매 시스템 융합
- 전이 엔트로피 + 압축 분석 + 로고스-니트로 프로토콜 통합
- MKM12BitcoinStrategy와 실시간 연동
- 모니터링 경고를 거래 신호에 반영

작성일: 2026-02-05
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "src"))

# 컴포넌트 import
# 선택적 import: TransferEntropyMarketRegimeDetector
try:
    from tools.core.transfer_entropy_market_regime_detector import TransferEntropyMarketRegimeDetector
    TRANSFER_ENTROPY_AVAILABLE = True
except ImportError:
    TransferEntropyMarketRegimeDetector = None
    TRANSFER_ENTROPY_AVAILABLE = False

# 선택적 import: LogosNitroProtocol
try:
    from tools.core.logos_nitro_protocol import LogosNitroProtocol
    LOGOS_NITRO_AVAILABLE = True
except ImportError:
    LogosNitroProtocol = None
    LOGOS_NITRO_AVAILABLE = False

# 선택적 import: unified_compression_api
try:
    from tools.core.unified_compression_api import get_unified_compression_api
    COMPRESSION_API_AVAILABLE = True
except ImportError:
    get_unified_compression_api = None
    COMPRESSION_API_AVAILABLE = False

# 필수 import: MKM12BitcoinStrategy
try:
    from src.strategy.mkm12_bitcoin_strategy import MKM12BitcoinStrategy
    MKM12_STRATEGY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MKM12BitcoinStrategy 로드 실패: {e}")
    MKM12BitcoinStrategy = None
    MKM12_STRATEGY_AVAILABLE = False

# 선택적 import: ThreeYearApocalypsePredictor (예언 묵시록)
try:
    from src.analysis.three_year_apocalypse_predictor import ThreeYearApocalypsePredictor
    APOCALYPSE_PREDICTOR_AVAILABLE = True
except ImportError as e:
    ThreeYearApocalypsePredictor = None
    APOCALYPSE_PREDICTOR_AVAILABLE = False
    print(f"⚠️ ThreeYearApocalypsePredictor 로드 실패: {e}")

# 🚀 Intelligence Refinery v2.0 통합 (신뢰도 기반 최적화 + 위상 공명 팩트체크)
INTELLIGENCE_REFINERY_AVAILABLE = False
try:
    from tools.core.intelligence_refinery import IntelligenceRefinery
    INTELLIGENCE_REFINERY_AVAILABLE = True
except ImportError as e:
    IntelligenceRefinery = None
    INTELLIGENCE_REFINERY_AVAILABLE = False
    print(f"⚠️ Intelligence Refinery v2.0을 import할 수 없습니다. 뉴스 정제 기능 비활성화: {e}")

# 📊 시장 지표 모니터링 시스템 (나스닥/환율 기준선 모니터링)
try:
    from src.monitoring.market_indicator_monitor import MarketIndicatorMonitor
    MARKET_INDICATOR_MONITOR_AVAILABLE = True
except ImportError as e:
    MarketIndicatorMonitor = None
    MARKET_INDICATOR_MONITOR_AVAILABLE = False
    print(f"⚠️ MarketIndicatorMonitor를 import할 수 없습니다. 시장 지표 모니터링 비활성화: {e}")

# Public event bridge (optional): sanitized outbound feed for public dashboard.
try:
    from src.integration.public_event_bridge import PublicEventBridge, build_public_event
    PUBLIC_EVENT_BRIDGE_AVAILABLE = True
except ImportError:
    PublicEventBridge = None
    build_public_event = None
    PUBLIC_EVENT_BRIDGE_AVAILABLE = False

# COMPONENTS_AVAILABLE: MKM12BitcoinStrategy만 필수, 나머지는 선택적
COMPONENTS_AVAILABLE = MKM12_STRATEGY_AVAILABLE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PUBLIC_METRICS_SNAPSHOT_PATH = (
    WORKSPACE_ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "public"
    / "public_trading_metrics_latest.json"
)
DAEMON_STATUS_PATH = (
    WORKSPACE_ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "trading_daemon_status.json"
)
FUSED_WEEKLY_CONTRACT_PATH = (
    WORKSPACE_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "fused_paper_cycle_weekly_latest.json"
)


class UnifiedTradingMonitor:
    """
    통합 실전 거래 모니터링 시스템
    
    핵심 기능:
    1. 실전 시장 모니터링 (전이 엔트로피 + 압축 분석 + 로고스-니트로)
    2. MKM12BitcoinStrategy와 실시간 연동
    3. 모니터링 경고를 거래 신호에 반영
    4. 통합 거래 결정 시스템
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        enable_monitoring: bool = True,
        enable_trading: bool = False  # 기본값: 모니터링만
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
            enable_monitoring: 모니터링 활성화 여부
            enable_trading: 거래 활성화 여부 (실전 거래 시 True)
        """
        if not COMPONENTS_AVAILABLE:
            raise RuntimeError("필수 컴포넌트를 로드할 수 없습니다.")
        
        self.symbol = symbol
        self.enable_monitoring = enable_monitoring
        self.enable_trading = enable_trading
        self.enable_public_event_bridge = str(os.getenv("PUBLIC_EVENT_BRIDGE_ENABLED", "true")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.public_event_bridge = None
        
        # 🚀 Intelligence Refinery v2.0 초기화 (뉴스 정제용)
        self.intelligence_refinery = None
        if INTELLIGENCE_REFINERY_AVAILABLE and IntelligenceRefinery is not None:
            try:
                self.intelligence_refinery = IntelligenceRefinery(domain="bitcoin_trading")
                logger.info("✅ Intelligence Refinery v2.0 초기화 완료 (뉴스 정제 활성화)")
            except Exception as e:
                logger.warning(f"⚠️ Intelligence Refinery v2.0 초기화 실패: {e}")
                self.intelligence_refinery = None
        
        # 📊 시장 지표 모니터링 시스템 초기화 (나스닥/환율 기준선 모니터링)
        self.market_indicator_monitor = None
        if MARKET_INDICATOR_MONITOR_AVAILABLE and MarketIndicatorMonitor is not None:
            try:
                self.market_indicator_monitor = MarketIndicatorMonitor(
                    nasdaq_threshold=23500.0,
                    exchange_rate_threshold=1480.0,
                    update_interval=300  # 5분마다 업데이트
                )
                logger.info("✅ 시장 지표 모니터링 시스템 초기화 완료 (나스닥/환율 기준선 모니터링)")
            except Exception as e:
                logger.warning(f"⚠️ 시장 지표 모니터링 시스템 초기화 실패: {e}")
                self.market_indicator_monitor = None
        
        # 1. 실전 시장 모니터링 시스템
        if enable_monitoring:
            logger.info("🏛️ 실전 시장 모니터링 시스템 초기화 중...")
            if TRANSFER_ENTROPY_AVAILABLE and TransferEntropyMarketRegimeDetector is not None:
                self.te_detector = TransferEntropyMarketRegimeDetector()
            else:
                self.te_detector = None
                logger.warning("⚠️ TransferEntropyMarketRegimeDetector 비활성화 (선택적 기능)")
            
            if LOGOS_NITRO_AVAILABLE and LogosNitroProtocol is not None:
                self.logos_nitro = LogosNitroProtocol()
            else:
                self.logos_nitro = None
                logger.warning("⚠️ LogosNitroProtocol 비활성화 (선택적 기능)")
            
            if COMPRESSION_API_AVAILABLE and get_unified_compression_api is not None:
                self.compression_api = get_unified_compression_api()
            else:
                self.compression_api = None
                logger.warning("⚠️ unified_compression_api 비활성화 (선택적 기능)")
            logger.info("✅ 실전 시장 모니터링 시스템 초기화 완료")
        
        # 2. MKM12BitcoinStrategy
        logger.info("🧠 MKM12BitcoinStrategy 초기화 중...")
        self.strategy = MKM12BitcoinStrategy(
            symbol=symbol,
            use_theory_fusion=True,
            use_icd=True,
            use_mkm12=True,
            use_strategic_meeting=True
        )
        logger.info("✅ MKM12BitcoinStrategy 초기화 완료")
        
        # 📱 Telegram 알림 관리자 초기화
        try:
            from src.monitoring.alert_manager import AlertManager
            self.alert_manager = AlertManager(
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
                telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                enable_telegram=True
            )
            logger.info("✅ AlertManager 초기화 완료 (Telegram 알림 활성화)")
        except Exception as e:
            logger.warning(f"⚠️ AlertManager 초기화 실패: {e}. Telegram 알림 비활성화")
            self.alert_manager = None

        # 🌐 Public Event Bridge 초기화 (옵션)
        if self.enable_public_event_bridge and PUBLIC_EVENT_BRIDGE_AVAILABLE and PublicEventBridge is not None:
            try:
                self.public_event_bridge = PublicEventBridge()
                logger.info("✅ Public Event Bridge 초기화 완료 (sanitized public feed)")
            except Exception as e:
                logger.warning(f"⚠️ Public Event Bridge 초기화 실패: {e}")
                self.public_event_bridge = None
        
        # 🔮 예언 묵시록 예측기 초기화
        self.apocalypse_predictor = None
        self.apocalypse_scenarios = None
        self.last_apocalypse_update = None
        if APOCALYPSE_PREDICTOR_AVAILABLE and ThreeYearApocalypsePredictor is not None:
            try:
                self.apocalypse_predictor = ThreeYearApocalypsePredictor()
                logger.info("✅ 예언 묵시록 예측기 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 예언 묵시록 예측기 초기화 실패: {e}")
                self.apocalypse_predictor = None
        else:
            logger.warning("⚠️ ThreeYearApocalypsePredictor 비활성화 (선택적 기능)")
        
        # 모니터링 히스토리
        self.monitoring_history = []
        self.trading_history = []
        self.alert_history = []
        
        logger.info("✅ 통합 실전 거래 모니터링 시스템 초기화 완료")

    def _load_public_trading_metrics(self) -> Dict[str, Any]:
        """
        Best-effort public metrics loader.
        Priority:
        1) Explicit snapshot file for public broadcast fields
        2) Daemon status 24h exchange snapshot fallback
        """
        metrics: Dict[str, Any] = {}
        snapshot_path = Path(
            os.getenv(
                "PUBLIC_TRADING_METRICS_PATH",
                str(PUBLIC_METRICS_SNAPSHOT_PATH),
            )
        )
        try:
            if snapshot_path.is_file():
                payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    for k in (
                        "position_symbol",
                        "position_side",
                        "position_size",
                        "unrealized_pnl_usdt",
                        "realized_24h_usdt",
                        "pnl_24h_type",
                        "balance_total_usdt",
                        "balance_available_usdt",
                    ):
                        if k in payload:
                            metrics[k] = payload.get(k)
        except Exception as e:
            logger.debug("public metrics snapshot read skipped: %s", e)

        if "realized_24h_usdt" not in metrics:
            try:
                if DAEMON_STATUS_PATH.is_file():
                    ds = json.loads(DAEMON_STATUS_PATH.read_text(encoding="utf-8"))
                    if isinstance(ds, dict):
                        ex24 = ds.get("exchange_snapshot_24h") or {}
                        if isinstance(ex24, dict):
                            net = ex24.get("net")
                            realized = ex24.get("realized_pnl")
                            commission = ex24.get("commission")
                            funding = ex24.get("funding_fee")
                            metrics["realized_24h_usdt"] = net if net is not None else 0.0
                            if funding and not realized and not commission:
                                metrics["pnl_24h_type"] = "FUNDING_FEE"
                            elif realized:
                                metrics["pnl_24h_type"] = "REALIZED_PNL"
                            elif commission:
                                metrics["pnl_24h_type"] = "COMMISSION"
                            else:
                                metrics.setdefault("pnl_24h_type", "NONE")
                        metrics.setdefault("position_symbol", ds.get("symbol"))
            except Exception as e:
                logger.debug("daemon status metrics fallback skipped: %s", e)

        return metrics

    def _load_fused_week_contract_snapshot(self) -> Dict[str, Any]:
        """Best-effort loader for fused paper-cycle week contract."""
        try:
            if not FUSED_WEEKLY_CONTRACT_PATH.is_file():
                return {"available": False, "reason": "missing_file"}
            payload = json.loads(FUSED_WEEKLY_CONTRACT_PATH.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {"available": False, "reason": "invalid_payload"}
            week_contract = payload.get("week_contract") if isinstance(payload.get("week_contract"), dict) else {}
            signals = week_contract.get("signals") if isinstance(week_contract.get("signals"), dict) else {}
            quality = {
                name: (
                    str(sig.get("quality_flag")) if isinstance(sig, dict) else "missing"
                )
                for name, sig in signals.items()
            }
            return {
                "available": True,
                "generated_at_utc": payload.get("generated_at_utc"),
                "decision": payload.get("decision"),
                "decision_reason": payload.get("decision_reason"),
                "toe_score": payload.get("toe_score"),
                "quality_flags": quality,
            }
        except Exception as e:
            return {"available": False, "reason": f"load_error:{type(e).__name__}"}

    async def _publish_public_event(
        self,
        integrated_signal: str,
        integrated_confidence: float,
        warning_level: str,
        strategy_result: Dict[str, Any],
    ) -> None:
        if not self.public_event_bridge or not build_public_event:
            return
        try:
            if not getattr(self.public_event_bridge, "_running", False):
                await self.public_event_bridge.start()

            # Character fallback mapping for MVP.
            character_id = (
                strategy_result.get("active_character_id")
                or strategy_result.get("character_id")
                or {
                    "BUY": "dragon_quant",
                    "SELL": "tiger_shield",
                    "HOLD": "ox_guard",
                }.get(integrated_signal, "ox_guard")
            )
            public_event = build_public_event(
                signal=integrated_signal,
                confidence=integrated_confidence,
                risk_level=warning_level,
                active_character_id=str(character_id),
                metrics=self._load_public_trading_metrics(),
            )
            self.public_event_bridge.publish_nowait(public_event)
        except Exception as e:
            logger.warning(f"⚠️ Public Event 발행 실패(무시): {e}")
    
    async def analyze_with_monitoring(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        news_texts: Optional[List[str]] = None,
        bio_signals: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        모니터링 통합 시장 분석
        
        Args:
            price_data: 가격 데이터 (DataFrame)
            current_price: 현재 가격
            news_texts: 뉴스 텍스트 리스트 (선택적)
            bio_signals: 생체 신호 (선택적)
        
        Returns:
            통합 분석 결과 (모니터링 + 전략 분석)
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "strategy_analysis": None,
            "monitoring_analysis": None,
            "integrated_signal": "HOLD",
            "integrated_confidence": 0.0,
            "warning_level": "NORMAL",
            "primary_regime": None,
            "secondary_biblical_regime": None,
            "divine_distance": None,
            "fused_week_contract": None,
        }
        result["fused_week_contract"] = self._load_fused_week_contract_snapshot()
        
        # 🔮 예언 묵시록 시나리오 업데이트 (일일 1회 또는 필요 시)
        apocalypse_scenarios = self._update_apocalypse_scenarios(price_data, current_price)
        
        # 1. MKM12BitcoinStrategy 분석
        logger.info("🔍 [1단계] MKM12BitcoinStrategy 시장 분석...")
        strategy_result = self.strategy.analyze_market(
            price_data=price_data,
            current_price=current_price,
            apocalypse_scenarios=apocalypse_scenarios  # ✅ 예언 묵시록 시나리오 전달
        )
        result["strategy_analysis"] = strategy_result
        if strategy_result is not None:
            if result.get("divine_distance") is None:
                result["divine_distance"] = strategy_result.get("divine_distance")
        
        strategy_signal = strategy_result.get("signal", "HOLD")
        strategy_confidence = strategy_result.get("confidence", 0.0)
        
        logger.info(f"   전략 신호: {strategy_signal} (신뢰도: {strategy_confidence:.2%})")
        
        # 2. 실전 시장 모니터링 (활성화된 경우)
        monitoring_result = None
        if self.enable_monitoring:
            logger.info("🔍 [2단계] 실전 시장 모니터링 분석...")
            
            # 가격 수익률 계산
            if len(price_data) >= 2:
                price_returns = price_data['close'].pct_change().dropna().values[-100:]
            else:
                price_returns = np.array([0.0])
            
            # 🚀 Intelligence Refinery v2.0으로 뉴스 정제 및 센티먼트 계산
            if news_texts and self.intelligence_refinery:
                logger.info(f"🔍 Intelligence Refinery로 {len(news_texts)}개 뉴스 정제 중...")
                refined_news = []
                news_sentiment_list = []
                news_confidence_list = []
                
                for news_text in news_texts:
                    try:
                        # 신뢰도 기반 정제 (전략 신뢰도를 뉴스 정제 신뢰도로 사용)
                        strategy_confidence = strategy_result.get("confidence", 0.75)
                        logos_atom = await self.intelligence_refinery.refine_news(
                            raw_text=news_text,
                            confidence=strategy_confidence
                        )
                        
                        # 정제된 뉴스 저장
                        refined_news.append(logos_atom.refined_intelligence)
                        
                        # 위상 공명 팩트체크 결과 확인
                        quality_verification = self.intelligence_refinery.verify_logos_atom_quality(logos_atom)
                        is_hallucination = quality_verification.get("is_hallucination", False)
                        adjusted_confidence = quality_verification.get("adjusted_confidence", logos_atom.purity_score)
                        
                        # 센티먼트 계산 (순도 기반, 환각 감지 시 조정)
                        if is_hallucination:
                            logger.warning(f"   ⚠️ 뉴스 환각 감지: 신뢰도 {adjusted_confidence:.2%}로 조정")
                            news_sentiment_list.append(0.5)  # 중립 (환각 감지 시)
                            news_confidence_list.append(adjusted_confidence)
                        else:
                            # 순도 기반 센티먼트 (0.5 ~ 1.0)
                            sentiment = 0.5 + (logos_atom.purity_score - 0.5) * 0.5
                            news_sentiment_list.append(sentiment)
                            news_confidence_list.append(adjusted_confidence)
                        
                        logger.info(f"   ✅ 뉴스 정제 완료: Tier {logos_atom.tier}, 순도 {logos_atom.purity_score:.2%}, 센티먼트 {news_sentiment_list[-1]:.2f}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ 뉴스 정제 실패: {e}, 기본값 사용")
                        refined_news.append(news_text)
                        news_sentiment_list.append(0.5)
                        news_confidence_list.append(0.5)
                
                news_sentiment = np.array(news_sentiment_list)
                # 정제된 뉴스로 업데이트
                news_texts = refined_news
                
                # 평균 신뢰도 계산 (신호 신뢰도 조정에 사용)
                if news_confidence_list:
                    avg_news_confidence = sum(news_confidence_list) / len(news_confidence_list)
                    logger.info(f"   📊 평균 뉴스 신뢰도: {avg_news_confidence:.2%}")
                    # 전략 신뢰도에 뉴스 신뢰도 반영 (가중 평균)
                    strategy_confidence = strategy_result.get("confidence", 0.75)
                    combined_confidence = (strategy_confidence * 0.7) + (avg_news_confidence * 0.3)
                    strategy_result["confidence"] = combined_confidence
                    logger.info(f"   📊 통합 신뢰도: {combined_confidence:.2%} (전략 {strategy_confidence:.2%} + 뉴스 {avg_news_confidence:.2%})")
            elif news_texts:
                # Intelligence Refinery 없을 때 기본값 사용
                news_sentiment = np.array([0.5] * len(news_texts))
                logger.warning("⚠️ Intelligence Refinery 없음, 뉴스 센티먼트 기본값 사용")
            else:
                news_texts = []
                news_sentiment = np.array([0.5])
            
            # 모니터링 실행
            monitoring_result = await self._run_monitoring(
                price_returns=price_returns,
                news_sentiment=news_sentiment,
                news_texts=news_texts,
                current_date=datetime.now(),
                bio_signals=bio_signals
            )
            result["monitoring_analysis"] = monitoring_result
            
            warning_level = monitoring_result.get("integrated_warning", {}).get("level", "NORMAL")
            result["warning_level"] = warning_level
            regime_analysis = monitoring_result.get("regime_analysis", {}) if monitoring_result else {}
            regime_info = regime_analysis.get("regime", {}) if isinstance(regime_analysis, dict) else {}
            primary_regime = regime_info.get("regime_type")
            if primary_regime:
                result["primary_regime"] = primary_regime
            
            logger.info(f"   모니터링 경고 레벨: {warning_level}")
        
        # 3. 통합 신호 생성
        logger.info("🔍 [3단계] 통합 신호 생성...")
        integrated_signal, integrated_confidence = self._generate_integrated_signal(
            strategy_result=strategy_result,
            monitoring_result=monitoring_result,
            warning_level=result.get("warning_level", "NORMAL")
        )
        
        result["integrated_signal"] = integrated_signal
        result["integrated_confidence"] = integrated_confidence
        
        logger.info(f"   통합 신호: {integrated_signal} (신뢰도: {integrated_confidence:.2%})")

        # 🌐 Publish sanitized public event for dashboard/streaming surfaces.
        await self._publish_public_event(
            integrated_signal=integrated_signal,
            integrated_confidence=integrated_confidence,
            warning_level=result.get("warning_level", "WARNING"),
            strategy_result=strategy_result,
        )
        
        # 📱 Telegram 통찰 리포트 전송 (각종 지표 포함)
        if self.alert_manager:
            try:
                # 각종 지표 정보 수집
                indicators = {}
                if monitoring_result:
                    regime_analysis = monitoring_result.get("regime_analysis", {})
                    indicators["transfer_entropy"] = regime_analysis.get("transfer_entropy")
                    indicators["market_regime"] = regime_analysis.get("regime", {}).get("regime_type")
                    compression_analysis = regime_analysis.get("compression_analysis")
                    if compression_analysis:
                        indicators["compression_ratio"] = compression_analysis.get("compression_ratio")
                        indicators["sentiment"] = compression_analysis.get("sentiment_label")

                fused_contract = result.get("fused_week_contract") or {}
                if isinstance(fused_contract, dict) and fused_contract.get("available"):
                    indicators["fused_toe_score"] = fused_contract.get("toe_score")
                    indicators["fused_weekly_decision"] = fused_contract.get("decision")
                    indicators["fused_weekly_decision_reason"] = fused_contract.get("decision_reason")
                    indicators["fused_quality_flags"] = fused_contract.get("quality_flags")
                
                # 뉴스 신뢰도 (Intelligence Refinery 결과)
                if result.get("news_confidence") is not None:
                    indicators["news_confidence"] = result.get("news_confidence")
                
                # 🚀 해역증 지수 계산 (아테나 작전 지침 융합)
                try:
                    from src.analysis.taeyang_crisis_detector import TaeyangCrisisDetector
                    taeyang_detector = TaeyangCrisisDetector()
                    
                    # 4D 벡터 가져오기 (strategy_result에서)
                    vector_4d = strategy_result.get("vector_4d") or strategy_result.get("market_state", {}).get("vector_4d")
                    
                    if vector_4d:
                        # 해역증 감지
                        hae_yeok_result = taeyang_detector.detect_hae_yeok_symptom(
                            asset_price_inflation=0.3,  # 기본값 (실제로는 가격 데이터에서 계산)
                            market_overheating=0.5,  # 기본값 (실제로는 시장 데이터에서 계산)
                            speculation_index=0.5,  # 기본값 (실제로는 시장 데이터에서 계산)
                            vector_4d=vector_4d
                        )
                        
                        if hae_yeok_result.get("detected", False):
                            indicators["hae_yeok_index"] = hae_yeok_result.get("score", 0.0)
                            indicators["hae_yeok_severity"] = hae_yeok_result.get("severity", "low")
                            indicators["s_m_gap"] = hae_yeok_result.get("details", {}).get("s_m_gap", 0.0)
                            logger.info(f"   해역증 지수: {indicators['hae_yeok_index']:.3f} (심각도: {indicators['hae_yeok_severity']})")
                except Exception as e:
                    logger.warning(f"⚠️ 해역증 지수 계산 실패: {e}")
                
                # 🚀 점진적 청산 전략 정보 (아테나 작전 지침 융합)
                liquidation_info = None
                
                # 📊 시장 지표 모니터링 결과 확인 (나스닥/환율 기준선)
                if self.market_indicator_monitor:
                    try:
                        # 시장 지표 업데이트 (비동기)
                        asyncio.create_task(self.market_indicator_monitor.update_indicators())
                        
                        # 기준선 확인
                        threshold_check = self.market_indicator_monitor.check_thresholds()
                        if threshold_check.get("liquidation_recommended"):
                            liquidation_info = {
                                "liquidation_ratio": threshold_check.get("liquidation_ratio", 0.0),
                                "liquidation_reason": threshold_check.get("liquidation_reason", "시장 지표 기준선 돌파")
                            }
                            logger.info(
                                f"📊 점진적 청산 권고: {liquidation_info['liquidation_ratio']:.1%} "
                                f"({liquidation_info['liquidation_reason']})"
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ 시장 지표 모니터링 확인 오류: {e}")
                
                # strategy_result에서 청산 관련 정보 가져오기 (시장 지표가 없을 때만)
                if not liquidation_info and strategy_result.get("liquidation_ratio") is not None:
                    liquidation_info = {
                        "liquidation_ratio": strategy_result.get("liquidation_ratio"),
                        "liquidation_reason": strategy_result.get("liquidation_reason", "")
                    }
                
                # indicators에 청산 정보 추가
                if liquidation_info:
                    indicators["liquidation_ratio"] = liquidation_info.get("liquidation_ratio")
                    indicators["liquidation_reason"] = liquidation_info.get("liquidation_reason")
                
                # 예언 묵시록 통찰
                apocalypse_insight = None
                if self.apocalypse_scenarios and self.apocalypse_scenarios.get("bitcoin_market"):
                    bitcoin_predictions = self.apocalypse_scenarios["bitcoin_market"]["predictions"]
                    current_month = datetime.now().month
                    current_year = datetime.now().year
                    for pred in bitcoin_predictions:
                        if pred["month_in_year"] == current_month and pred["year"] == current_year:
                            apocalypse_insight = {
                                "collapse_risk": pred.get("collapse_risk", 0.0),
                                "stability": pred.get("stability", 0.0),
                                "apocalypse_signal": "SELL 강화" if pred.get("collapse_risk", 0.0) > 0.7 else None
                            }
                            break
                
                # 통찰 리포트 전송 (신호가 BUY/SELL일 때만)
                if integrated_signal in ["BUY", "SELL"]:
                    call_path_14b = None
                    try:
                        from src.config.config_loader import ConfigLoader
                        config_file = Path(__file__).resolve().parent.parent.parent / "config" / "trading_config.yaml"
                        if config_file.is_file():
                            loader = ConfigLoader(config_file)
                            loader.load()
                            call_path_14b = loader.get_14b_4d_native_call_path()
                    except Exception as e:
                        logger.debug("14B 호출 경로 로드 스킵: %s", e)
                    await self.alert_manager.alert_trading_insights(
                        signal=integrated_signal,
                        confidence=integrated_confidence,
                        current_price=current_price,
                        indicators=indicators,
                        apocalypse_insight=apocalypse_insight,
                        call_path_14b=call_path_14b,
                        gate_level=("LOW" if integrated_signal == "HOLD" or integrated_confidence < 0.6 else "MID"),
                        gate_reason=("monitor_low_confidence_or_hold" if integrated_signal == "HOLD" or integrated_confidence < 0.6 else "monitor_signal_active"),
                        price_lock=(integrated_signal == "HOLD" or integrated_confidence < 0.6),
                    )
            except Exception as e:
                logger.warning(f"⚠️ Telegram 통찰 리포트 전송 실패: {e}")
        
        # 히스토리 저장
        self.monitoring_history.append(result)
        if len(self.monitoring_history) > 1000:
            self.monitoring_history = self.monitoring_history[-1000:]
        
        # 경고 레벨이 WARNING 이상이면 알림 히스토리에 추가
        if result["warning_level"] in ["WARNING", "CRITICAL"]:
            self.alert_history.append({
                "timestamp": datetime.now().isoformat(),
                "level": result["warning_level"],
                "signal": integrated_signal,
                "confidence": integrated_confidence,
                "strategy_signal": strategy_signal,
                "strategy_confidence": strategy_confidence
            })
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-100:]
        
        return result
    
    async def _run_monitoring(
        self,
        price_returns: np.ndarray,
        news_sentiment: np.ndarray,
        news_texts: List[str],
        current_date: datetime,
        bio_signals: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """실전 시장 모니터링 실행"""
        result = {}
        
        # 1. 전이 엔트로피 분석 (압축 엔진 연동)
        if self.te_detector is not None:
            regime_result = await self.te_detector.detect_market_regime(
                price_returns=price_returns,
                news_sentiment=news_sentiment,
                news_texts=news_texts,
                current_date=current_date,
                sp500_level=None
            )
            result["regime_analysis"] = regime_result
        else:
            # te_detector가 없을 때 기본값
            regime_result = {
                "transfer_entropy": 0.0,
                "sigma_deviation": 0.0,
                "regime": {"regime_type": "UNKNOWN"},
                "compression_analysis": None
            }
            result["regime_analysis"] = regime_result
        
        transfer_entropy = regime_result.get("transfer_entropy", 0.0)
        sigma_deviation = regime_result.get("sigma_deviation", 0.0)
        regime_type = regime_result.get("regime", {}).get("regime_type", "UNKNOWN")
        compression_analysis = regime_result.get("compression_analysis")
        
        logger.info(f"   전이 엔트로피: {transfer_entropy:.4f}")
        logger.info(f"   시그마 편차: {sigma_deviation:.2f}")
        logger.info(f"   시장 국면: {regime_type}")
        
        if compression_analysis:
            logger.info(f"   압축률: {compression_analysis.get('compression_ratio', 0.0)*100:.2f}%")
            logger.info(f"   경고 레벨: {compression_analysis.get('warning_level', 'NORMAL')}")
        
        # 2. 로고스-니트로 프로토콜 (생체 신호 분석)
        bio_analysis = None
        if self.logos_nitro is not None and bio_signals:
            bio_result = self.logos_nitro.step1_bio_switch(
                pilomotor_reflex=bio_signals.get("pilomotor_reflex", 0.0),
                vagal_tone=bio_signals.get("vagal_tone", 0.5)
            )
            
            bio_analysis = {
                "bio_switch_status": bio_result.get("bio_switch_status"),
                "signal_clarity": bio_result.get("signal_clarity", 0.0),
                "compression_efficient": bio_result.get("compression_efficient", False),
                "adaptive_bypass": bio_result.get("adaptive_bypass", False),
                "action": bio_result.get("action")
            }
            result["bio_analysis"] = bio_analysis
        
        # 3. 통합 경고 레벨 결정
        integrated_warning = self._determine_integrated_warning(
            regime_result,
            compression_analysis,
            bio_analysis
        )
        result["integrated_warning"] = integrated_warning
        
        return result
    
    def _determine_integrated_warning(
        self,
        regime_result: Dict[str, Any],
        compression_analysis: Optional[Dict[str, Any]],
        bio_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """통합 경고 레벨 결정"""
        reasons = []
        max_level = "NORMAL"
        
        # 1. 전이 엔트로피 기반 경고
        sigma_deviation = regime_result.get("sigma_deviation", 0.0)
        alert_level = regime_result.get("alert_level", {})
        regime_alert = alert_level.get("level", "NORMAL")
        
        if regime_alert == "CRITICAL":
            max_level = "CRITICAL"
            reasons.append(f"전이 엔트로피 CRITICAL: 시그마 편차 {sigma_deviation:.2f}")
        elif regime_alert == "WARNING":
            if max_level == "NORMAL":
                max_level = "WARNING"
            reasons.append(f"전이 엔트로피 WARNING: 시그마 편차 {sigma_deviation:.2f}")
        
        # 2. 압축 분석 기반 경고
        if compression_analysis:
            comp_warning = compression_analysis.get("warning_level", "NORMAL")
            if comp_warning == "CRITICAL":
                max_level = "CRITICAL"
                reasons.append("압축 분석 CRITICAL: 압축률 스파이크 또는 감성 공포 급변")
            elif comp_warning == "WARNING":
                if max_level == "NORMAL":
                    max_level = "WARNING"
                reasons.append("압축 분석 WARNING: 압축률 또는 감성 변화 감지")
        
        return {
            "level": max_level,
            "reasons": reasons,
            "regime_alert": regime_alert,
            "compression_alert": compression_analysis.get("warning_level", "NORMAL") if compression_analysis else "NORMAL"
        }
    
    def _generate_integrated_signal(
        self,
        strategy_result: Dict[str, Any],
        monitoring_result: Optional[Dict[str, Any]],
        warning_level: str
    ) -> tuple[str, float]:
        """
        통합 신호 생성 (예언 결과 반영)
        
        Returns:
            (신호, 신뢰도)
        """
        strategy_signal = strategy_result.get("signal", "HOLD")
        strategy_confidence = strategy_result.get("confidence", 0.0)
        
        # 🏛️ Canvas 아키텍처 예언 결과 확인
        position_size_multiplier = strategy_result.get("position_size_multiplier", 1.0)
        logos_risk_multiplier = strategy_result.get("logos_risk_multiplier", 1.0)
        asset_allocation_strategy = strategy_result.get("asset_allocation_strategy")
        divine_distance = strategy_result.get("divine_distance")
        bitcoin_target_multiplier = strategy_result.get("bitcoin_target_multiplier")
        apocalypse_confidence_boost = strategy_result.get("apocalypse_confidence_boost", 0.0)
        apocalypse_signal_adjustment = strategy_result.get("apocalypse_signal_adjustment")
        
        # 기본값: 전략 신호 사용
        integrated_signal = strategy_signal
        integrated_confidence = strategy_confidence
        
        # 🏛️ Canvas 아키텍처 예언 결과 반영
        if apocalypse_confidence_boost != 0.0:
            integrated_confidence = min(1.0, integrated_confidence + apocalypse_confidence_boost)
            logger.info(
                f"🏛️ Canvas 예언 신뢰도 보정: {apocalypse_confidence_boost:+.1%} "
                f"(보정 후: {integrated_confidence:.2%})"
            )
        
        if apocalypse_signal_adjustment in ["BUY", "SELL", "HOLD"]:
            integrated_signal = apocalypse_signal_adjustment
            logger.info(
                f"🏛️ Canvas 예언 신호 조정: {apocalypse_signal_adjustment} "
                f"(Divine Distance: {divine_distance:.4f if divine_distance else 'N/A'})"
            )
        
        # 🏛️ Canvas + Logos 필터 기반 포지션 크기 조정 (실전 투입 전, 백테스트로 충분히 검증 필요)
        effective_position_multiplier = position_size_multiplier * logos_risk_multiplier

        if effective_position_multiplier != 1.0:
            logger.info(
                "🎯 포지션 크기 조정: "
                f"Canvas 타겟 승수 계수={position_size_multiplier:.2f}x, "
                f"Logos 리스크 계수={logos_risk_multiplier:.2f}x → "
                f"통합 계수={effective_position_multiplier:.2f}x "
                f"(타겟 승수: {bitcoin_target_multiplier:.1f}x if bitcoin_target_multiplier else 'N/A')"
            )
        
        if asset_allocation_strategy:
            btc_allocation = asset_allocation_strategy.get("BTC", 0.5)
            logger.info(
                f"🏛️ Canvas 자산 배분 전략: BTC {btc_allocation:.1%} "
                f"(Divine Distance: {divine_distance:.4f if divine_distance else 'N/A'})"
            )
        
        # 모니터링 결과가 있으면 조정
        if monitoring_result:
            integrated_warning = monitoring_result.get("integrated_warning", {})
            warning_level = integrated_warning.get("level", "NORMAL")
            
            # CRITICAL 경고 시 거래 중단
            if warning_level == "CRITICAL":
                logger.warning("🚨 CRITICAL 경고: 거래 중단 (HOLD)")
                return ("HOLD", 0.0)
            
            # WARNING 경고 시 신뢰도 감소
            elif warning_level == "WARNING":
                logger.warning("⚠️ WARNING 경고: 신뢰도 감소")
                integrated_confidence = strategy_confidence * 0.7  # 30% 감소
            
            # 🚀 각종 지표를 매매 신호에 직접 반영 (P1 개선)
            regime_analysis = monitoring_result.get("regime_analysis", {})
            transfer_entropy = regime_analysis.get("transfer_entropy", 0.0)
            sigma_deviation = regime_analysis.get("sigma_deviation", 0.0)
            regime = regime_analysis.get("regime", {})
            regime_type = regime.get("regime_type", "UNKNOWN")
            compression_analysis = regime_analysis.get("compression_analysis")
            
            # 1. 전이 엔트로피 연속적 조정 (0.0 ~ 5.0 범위)
            # 전이 엔트로피가 높을수록 시장 불안정 → 신뢰도 감소
            if transfer_entropy > 0.0:
                # 연속적 조정: 0.0 → 1.0 (신뢰도 100%), 3.0 → 0.9 (신뢰도 90%), 5.0 → 0.7 (신뢰도 70%)
                entropy_adjustment = 1.0 - (transfer_entropy / 5.0) * 0.3  # 최대 30% 감소
                entropy_adjustment = max(0.7, min(1.0, entropy_adjustment))  # 0.7 ~ 1.0 범위
                integrated_confidence = integrated_confidence * entropy_adjustment
                logger.info(f"   📊 전이 엔트로피 연속적 조정: {transfer_entropy:.2f} → 신뢰도 {entropy_adjustment:.2%} 배율 적용")
            
            # 2. Market Regime 기반 신호 필터링
            # 시장 국면에 따라 신호 조정
            if regime_type != "UNKNOWN":
                regime_adjustment = 1.0
                if regime_type == "CRISIS" or regime_type == "VOLATILE":
                    # 위기/변동성 국면: 신뢰도 감소
                    regime_adjustment = 0.85  # 15% 감소
                    logger.warning(f"   ⚠️ 시장 국면 {regime_type}: 신뢰도 15% 감소")
                elif regime_type == "STABLE" or regime_type == "TRENDING":
                    # 안정/추세 국면: 신뢰도 약간 증가
                    regime_adjustment = 1.05  # 5% 증가
                    logger.info(f"   ✅ 시장 국면 {regime_type}: 신뢰도 5% 증가")
                elif regime_type == "TRANSITION":
                    # 전환 국면: 신뢰도 감소
                    regime_adjustment = 0.9  # 10% 감소
                    logger.warning(f"   ⚠️ 시장 국면 {regime_type}: 신뢰도 10% 감소")
                
                integrated_confidence = integrated_confidence * regime_adjustment
                integrated_confidence = min(1.0, integrated_confidence)  # 최대 100% 제한
            
            # 3. Compression Ratio 기반 신호 강화/약화
            if compression_analysis:
                compression_ratio = compression_analysis.get("compression_ratio", 1.0)
                sentiment_label = compression_analysis.get("sentiment_label", "")
                
                # 압축률 기반 조정 (높은 압축률 = 노이즈 제거 효과 = 신뢰도 증가)
                if compression_ratio < 0.5:  # 압축률 50% 미만 = 노이즈 많음
                    compression_adjustment = 0.95  # 5% 감소
                    logger.warning(f"   ⚠️ 압축률 낮음 ({compression_ratio:.1%}): 노이즈 많음, 신뢰도 5% 감소")
                elif compression_ratio > 0.8:  # 압축률 80% 이상 = 노이즈 적음
                    compression_adjustment = 1.03  # 3% 증가
                    logger.info(f"   ✅ 압축률 높음 ({compression_ratio:.1%}): 노이즈 적음, 신뢰도 3% 증가")
                else:
                    compression_adjustment = 1.0  # 변화 없음
                
                integrated_confidence = integrated_confidence * compression_adjustment
                integrated_confidence = min(1.0, integrated_confidence)
                
                # 감성 레이블 기반 조정
                if sentiment_label == "FEAR":
                    logger.warning("   ⚠️ 감성 공포 감지: 신뢰도 20% 감소")
                    integrated_confidence = integrated_confidence * 0.8  # 20% 감소
                elif sentiment_label == "GREED":
                    logger.info("   ⚠️ 감성 탐욕 감지: 신뢰도 10% 감소 (과열 신호)")
                    integrated_confidence = integrated_confidence * 0.9  # 10% 감소
                elif sentiment_label == "NEUTRAL" or sentiment_label == "BALANCED":
                    logger.info("   ✅ 감성 중립: 신뢰도 유지")
                    # 변화 없음
        
        # 🏛️ Canvas 아키텍처 Divine Distance 기반 최종 신호 조정
        if divine_distance is not None:
            if divine_distance >= 0.4:
                # 위기 상황: 매도 신호 강화
                if integrated_signal != "SELL":
                    integrated_signal = "SELL"
                    integrated_confidence = min(1.0, integrated_confidence + 0.05)
                    logger.warning(
                        f"🏛️ Canvas 위기 신호 최종 조정: Divine Distance {divine_distance:.4f} ≥ 0.4 → SELL"
                    )
            elif divine_distance < 0.25:
                # 안정 상황: 매수 신호 강화
                if integrated_signal != "BUY":
                    integrated_signal = "BUY"
                    integrated_confidence = min(1.0, integrated_confidence + 0.03)
                    logger.info(
                        f"🏛️ Canvas 안정 신호 최종 조정: Divine Distance {divine_distance:.4f} < 0.25 → BUY"
                    )
        
        # 신뢰도 최종 제한
        integrated_confidence = min(1.0, max(0.0, integrated_confidence))
        
        return (integrated_signal, integrated_confidence)
    
    def _update_apocalypse_scenarios(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        🔮 예언 묵시록 시나리오 업데이트 (일일 1회 또는 필요 시)
        
        Args:
            price_data: 가격 데이터
            current_price: 현재 가격
        
        Returns:
            묵시록 시나리오 딕셔너리 (없으면 None)
        """
        if not self.apocalypse_predictor:
            return None
        
        try:
            # 일일 1회 업데이트 (또는 첫 실행 시)
            current_date = datetime.now().date()
            if self.last_apocalypse_update == current_date and self.apocalypse_scenarios:
                # 이미 오늘 업데이트됨, 기존 시나리오 반환
                return self.apocalypse_scenarios
            
            logger.info("🔮 예언 묵시록 시나리오 업데이트 중...")
            
            # 변동성 계산 (최근 가격 데이터 기반)
            if len(price_data) >= 20:
                recent_prices = price_data['close'].tail(20) if 'close' in price_data.columns else pd.Series([current_price] * 20)
                volatility = recent_prices.pct_change().std() * np.sqrt(365)  # 연율 변동성
            else:
                volatility = 0.6  # 기본값 (60%)
            
            # 비트코인 시장 데이터 준비
            bitcoin_data = {
                "current_price": current_price,
                "volatility": volatility,
                "market_cap": 2e12,  # 기본값 (실제로는 API에서 가져옴)
                "transaction_volume": 3e10  # 기본값 (실제로는 API에서 가져옴)
            }
            
            # 주식 시장 데이터 (간단화: 기본값 사용)
            stock_data = {
                "current_price": 100.0,
                "volatility": 0.2
            }
            
            # 묵시록 시나리오 생성
            self.apocalypse_scenarios = self.apocalypse_predictor.generate_apocalypse_scenarios(
                stock_data=stock_data,
                bitcoin_data=bitcoin_data
            )
            
            self.last_apocalypse_update = current_date
            
            logger.info(f"✅ 예언 묵시록 시나리오 업데이트 완료 (예측 기간: {self.apocalypse_scenarios.get('prediction_period', 'N/A')})")
            
            # 🏛️ Canvas 아키텍처 상세 로깅
            if self.apocalypse_scenarios:
                # temporal_sovereignty 로깅
                temporal_sovereignty = self.apocalypse_scenarios.get("temporal_sovereignty", {})
                if temporal_sovereignty:
                    current_divine_distance = temporal_sovereignty.get("current_distance")
                    crisis_timeline = temporal_sovereignty.get("crisis_timeline", {})
                    
                    logger.info(f"🏛️ Canvas Divine Distance (현재): {current_divine_distance:.4f if current_divine_distance else 'N/A'}")
                    logger.info("📊 Canvas 위기 타임라인 (2027-2030):")
                    for year in sorted(crisis_timeline.keys()):
                        distance = crisis_timeline[year]
                        logger.info(f"   {year}년: Divine Distance {distance:.4f}")
                
                # survival_protocol 로깅
                survival_protocol = self.apocalypse_scenarios.get("survival_protocol", {})
                if survival_protocol:
                    target_multiplier = survival_protocol.get("target_multiplier")
                    asset_allocation = survival_protocol.get("asset_allocation", {})
                    yearly_targets = survival_protocol.get("yearly_targets", {})
                    
                    logger.info(f"🎯 Bitcoin 타겟 승수 (현재): {target_multiplier:.1f}x" if target_multiplier else "🎯 Bitcoin 타겟 승수 (현재): N/A")
                    logger.info("📊 Canvas 자산 배분 전략:")
                    logger.info(f"   BTC: {asset_allocation.get('BTC', 0.0):.1%}, "
                              f"GOLD: {asset_allocation.get('GOLD', 0.0):.1%}, "
                              f"CASH: {asset_allocation.get('CASH', 0.0):.1%}")
                    logger.info("📊 연도별 Bitcoin 타겟 승수:")
                    for year in sorted(yearly_targets.keys()):
                        year_data = yearly_targets[year]
                        multiplier = year_data.get("bitcoin_target_multiplier", "N/A")
                        crisis_level = year_data.get("crisis_level", "N/A")
                        logger.info(f"   {year}년: {multiplier}x (위기 레벨: {crisis_level})")
                
                # 현재 시점의 예언 정보 로깅
                bitcoin_market = self.apocalypse_scenarios.get("bitcoin_market", {})
                bitcoin_predictions = bitcoin_market.get("predictions", [])
                if bitcoin_predictions:
                    # 현재 시점의 예측 찾기 (첫 번째 예측 사용)
                    current_prediction = bitcoin_predictions[0] if bitcoin_predictions else {}
                    if current_prediction:
                        collapse_risk = current_prediction.get("collapse_risk", 0.0)
                        stability = current_prediction.get("stability", 0.0)
                        logger.info(f"   현재 붕괴 위험도: {collapse_risk:.1%}, 안정성: {stability:.1%}")
            
            return self.apocalypse_scenarios
            
        except Exception as e:
            logger.error(f"❌ 예언 묵시록 시나리오 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """최근 N시간 내 경고 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) >= cutoff_time
        ]
    
    def save_integrated_report(self, output_path: Optional[Path] = None):
        """통합 리포트 저장"""
        if output_path is None:
            output_path = WORKSPACE_ROOT / "memory" / f"unified_trading_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "symbol": self.symbol,
            "total_analyses": len(self.monitoring_history),
            "total_alerts": len(self.alert_history),
            "recent_alerts_24h": self.get_recent_alerts(24),
            "monitoring_history": self.monitoring_history[-100:],  # 최근 100개만
            "alert_history": self.alert_history
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📁 통합 리포트 저장: {output_path}")
        return output_path


async def test_unified_system():
    """통합 시스템 테스트"""
    print("🧪 통합 실전 거래 모니터링 시스템 테스트 시작\n")
    
    # 통합 모니터 초기화
    monitor = UnifiedTradingMonitor(
        symbol="BTCUSDT",
        enable_monitoring=True,
        enable_trading=False  # 테스트: 모니터링만
    )
    
    # 테스트 데이터 생성
    print("📊 테스트 데이터 생성 중...")
    
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now(),
        freq='1h'
    )
    
    np.random.seed(42)
    base_price = 90000.0
    n = len(dates)
    trend = np.linspace(0, 0.05, n)  # 5% 상승 트렌드
    volatility = 0.02
    returns = np.random.normal(0.001, volatility, n) + trend / n
    prices = base_price * np.exp(np.cumsum(returns))
    
    price_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(1000, 10000, n)
    }, index=dates)
    
    current_price = price_data['close'].iloc[-1]
    
    # 뉴스 텍스트 (테스트용)
    news_texts = [
        "비트코인이 급격히 상승하고 있습니다. 투자자들의 관심이 높아지고 있습니다.",
        "시장 변동성이 증가하고 있습니다. 신중한 접근이 필요합니다."
    ]
    
    # 생체 신호 (테스트용)
    bio_signals = {
        "pilomotor_reflex": 0.6,
        "vagal_tone": 0.7
    }
    
    # 통합 분석 실행
    print("\n" + "="*80)
    print("🚀 통합 분석 실행")
    print("="*80)
    
    result = await monitor.analyze_with_monitoring(
        price_data=price_data,
        current_price=current_price,
        news_texts=news_texts,
        bio_signals=bio_signals
    )
    
    # 결과 출력
    print("\n" + "="*80)
    print("📊 통합 분석 결과")
    print("="*80)
    print(f"전략 신호: {result['strategy_analysis'].get('signal', 'HOLD')}")
    print(f"전략 신뢰도: {result['strategy_analysis'].get('confidence', 0.0):.2%}")
    print(f"통합 신호: {result['integrated_signal']}")
    print(f"통합 신뢰도: {result['integrated_confidence']:.2%}")
    print(f"경고 레벨: {result['warning_level']}")
    
    # 리포트 저장
    report_path = monitor.save_integrated_report()
    
    print("\n✅ 통합 실전 거래 모니터링 시스템 테스트 완료")
    print(f"   리포트: {report_path}")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_unified_system())

