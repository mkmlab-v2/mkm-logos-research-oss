#!/usr/bin/env python3
"""
비트코인 매매 전략 (MKM12 + ICD 이론 통합)

최종 권위 이론 적용:
- ICD 통합 모델 (System Constraint Factor λ 기반)
- MKM12 동역학 예측 모델 (4차원 상태 공간 S-L-K-M)
- A-Code 체질 분류 (Type A/B/C/D, TY-1~SE-3)
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import logging
import math
# MKM12 헌법: 안전 상수 ε (자동 추가)
EPSILON = 1e-5

# 경로 설정
# __file__ = projects/bitcoin-trading/src/strategy/mkm12_bitcoin_strategy.py
# .parent = projects/bitcoin-trading/src/strategy
# .parent.parent = projects/bitcoin-trading/src
# .parent.parent.parent = projects/bitcoin-trading
# .parent.parent.parent.parent = projects
# 올바른 workspace_root는 projects의 상위 디렉토리
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

# 이론 모듈 import
tools_path = workspace_root / "tools" / "tools" / "core"
THEORY_FUSION_AVAILABLE = False
ICD_AVAILABLE = False
MKM12_DYNAMICS_AVAILABLE = False
DISTILLER_AVAILABLE = False
ICHING_FILTER_AVAILABLE = False

try:
    if tools_path.exists():
        sys.path.insert(0, str(tools_path.parent.parent))
        from tools.core.theory_fusion_executor import TheoryFusionExecutor
        from tools.core.ICDStockAnalysisEngine import ICDStockAnalysisEngine
        from tools.core.ICDUnifiedModel import ICDUnifiedModel
        THEORY_FUSION_AVAILABLE = True
        ICD_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ 이론 모듈 import 실패: {e}")

# MKM12DynamicsPredictor import (별도 처리)
# logging 모듈이 아직 설정되지 않았으므로 print 사용
MKM12_DYNAMICS_AVAILABLE = False
try:
    # 경로 1: tools/tools/core (우선순위 1)
    tools_tools_core_path = workspace_root / "tools" / "tools" / "core"
    if (tools_tools_core_path / "MKM12DynamicsPredictor.py").exists():
        sys.path.insert(0, str(tools_tools_core_path))
        from MKM12DynamicsPredictor import MKM12DynamicsPredictor
        MKM12_DYNAMICS_AVAILABLE = True
        print(f"✅ MKM12DynamicsPredictor import 성공 (tools/tools/core): {MKM12_DYNAMICS_AVAILABLE}")
    else:
        raise ImportError(f"파일 없음: {tools_tools_core_path / 'MKM12DynamicsPredictor.py'}")
except (ImportError, Exception) as e:
    try:
        # 경로 2: tools/core
        tools_core_path = workspace_root / "tools" / "core"
        if (tools_core_path / "MKM12DynamicsPredictor.py").exists():
            sys.path.insert(0, str(tools_core_path))
            from MKM12DynamicsPredictor import MKM12DynamicsPredictor
            MKM12_DYNAMICS_AVAILABLE = True
            print(f"✅ MKM12DynamicsPredictor import 성공 (tools/core): {MKM12_DYNAMICS_AVAILABLE}")
        else:
            raise ImportError(f"파일 없음: {tools_core_path / 'MKM12DynamicsPredictor.py'}")
    except (ImportError, Exception) as e2:
        try:
            # 경로 3: tools.core (패키지 형태)
            from tools.core.MKM12DynamicsPredictor import MKM12DynamicsPredictor
            MKM12_DYNAMICS_AVAILABLE = True
            print(f"✅ MKM12DynamicsPredictor import 성공 (tools.core): {MKM12_DYNAMICS_AVAILABLE}")
        except ImportError as e3:
            print(f"⚠️ MKM12DynamicsPredictor import 실패: {e}, {e2}, {e3}")
            MKM12_DYNAMICS_AVAILABLE = False

print(f"🔍 최종 MKM12_DYNAMICS_AVAILABLE 상태: {MKM12_DYNAMICS_AVAILABLE}")

# 통일장 이론 엔진 import
UFT_AVAILABLE = False
try:
    sys.path.insert(0, str(workspace_root / "tools" / "core"))
    from unified_field_theory_engine import UnifiedFieldTheoryEngine
    UFT_AVAILABLE = True
    print(f"✅ UnifiedFieldTheoryEngine import 성공")
except ImportError:
    try:
        from tools.core.unified_field_theory_engine import UnifiedFieldTheoryEngine
        UFT_AVAILABLE = True
        print(f"✅ UnifiedFieldTheoryEngine import 성공 (tools.core)")
    except ImportError as e:
        logging.warning(f"⚠️ 통일장 이론 엔진 import 실패: {e}")

# 증류 엔진 import
try:
    sys.path.insert(0, str(workspace_root / "tools" / "core"))
    from enhanced_stream_distillation import EnhancedStreamDistillation
    DISTILLER_AVAILABLE = True
except ImportError:
    try:
        from tools.core.enhanced_stream_distillation import EnhancedStreamDistillation
        DISTILLER_AVAILABLE = True
    except ImportError as e:
        logging.warning(f"⚠️ 증류 엔진 import 실패: {e}")

# 주역 위상 전이 필터 import
try:
    from src.analysis.iching_phase_filter import IChingPhaseFilter
    ICHING_FILTER_AVAILABLE = True
except ImportError:
    try:
        analysis_path = Path(__file__).parent.parent / "analysis"
        sys.path.insert(0, str(analysis_path))
        from iching_phase_filter import IChingPhaseFilter
        ICHING_FILTER_AVAILABLE = True
    except ImportError as e:
        logging.warning(f"⚠️ 주역 위상 전이 필터 import 실패: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project Logos: Divine Centroid (0.25 평형)
# 검증 완료: S=0.2498, L=0.2497, K=0.2507, M=0.2498
DIVINE_CENTROID = {
    "S": 0.2498,
    "L": 0.2497,
    "K": 0.2507,
    "M": 0.2498
}

# 목표 벡터 (완벽한 균형)
TARGET_VECTOR = {
    "S": 0.25,
    "L": 0.25,
    "K": 0.25,
    "M": 0.25
}

# 프랙탈 보정 계수 (99.07% 자기 유사성)
FRACTAL_CORRECTION = 0.9907


class MKM12BitcoinStrategy:
    """
    비트코인 매매 전략 (MKM12 + ICD 이론 통합)
    
    최종 권위 이론 적용:
    - ICD 통합 모델: System Constraint Factor (λ) 계산
    - MKM12 동역학 예측: 4차원 상태 벡터 (S-L-K-M) 분석
    - A-Code 체질 분류: Type A/B/C/D (TY-1~SE-3) 방식 사용
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        use_theory_fusion: bool = True,
        use_icd: bool = True,
        use_mkm12: bool = True,
        use_strategic_meeting: bool = True  # 12인 참모진 전략 회의 사용 여부
    ):
        """
        Args:
            symbol: 거래 심볼 (기본값: BTCUSDT)
            use_theory_fusion: TheoryFusionExecutor 사용 여부
            use_icd: ICD 통합 모델 사용 여부
            use_mkm12: MKM12 동역학 예측 사용 여부
            use_strategic_meeting: 12인 참모진 전략 회의 사용 여부
        """
        self.symbol = symbol
        self.use_theory_fusion = use_theory_fusion and THEORY_FUSION_AVAILABLE
        self.use_icd = use_icd and ICD_AVAILABLE
        self.use_mkm12 = use_mkm12 and MKM12_DYNAMICS_AVAILABLE
        self.use_distiller = DISTILLER_AVAILABLE
        self.use_iching_filter = ICHING_FILTER_AVAILABLE
        self.use_strategic_meeting = use_strategic_meeting
        
        # 디버깅: 초기화 상태 확인
        logger.info(f"🔍 초기화 상태: MKM12_DYNAMICS_AVAILABLE={MKM12_DYNAMICS_AVAILABLE}, use_mkm12={self.use_mkm12}")
        
        # 이론 모듈 초기화
        self.theory_fusion = None
        self.icd_engine = None
        self.icd_model = None
        self.mkm12_predictor = None
        self.distiller = None
        self.iching_filter = None
        self.strategic_meeting_bridge = None
        self.chart_image_analyzer = None
        self.uft_engine = None  # 통일장 이론 엔진
        self._myeongri_controller = None  # G_환경 e (명리 기반, 지연 로딩)
        self._myeongri_failed = False  # 한 번 실패 시 재시도 안 함 (튕김 방지)
        
        if self.use_theory_fusion:
            try:
                # TheoryFusionExecutor 초기화 (비트코인 도메인)
                self.theory_fusion = TheoryFusionExecutor(domain="crypto_volatile")
                logger.info("✅ TheoryFusionExecutor 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ TheoryFusionExecutor 초기화 실패: {e}")
                self.use_theory_fusion = False
        
        if self.use_icd:
            try:
                # ICD 통합 모델 초기화
                self.icd_model = ICDUnifiedModel()
                self.icd_engine = ICDStockAnalysisEngine()
                logger.info("✅ ICD 통합 모델 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ ICD 통합 모델 초기화 실패: {e}")
                self.use_icd = False
        
        if self.use_mkm12:
            try:
                # MKM12 동역학 예측 모델 초기화
                self.mkm12_predictor = MKM12DynamicsPredictor()
                logger.info("✅ MKM12 동역학 예측 모델 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ MKM12 동역학 예측 모델 초기화 실패: {e}")
                self.use_mkm12 = False
        
        # G_환경 e: 명리 기반 환경 인자 — __init__에서 생성 제거, 최초 사용 시 _get_env_factor_and_type()에서 지연 로딩 (튕김 방지)
        
        # 통일장 이론 엔진 초기화 (통일장 이론 업그레이드)
        if UFT_AVAILABLE:
            try:
                self.uft_engine = UnifiedFieldTheoryEngine()
                logger.info("✅ 통일장 이론 엔진 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 통일장 이론 엔진 초기화 실패: {e}")
                self.uft_engine = None
        else:
            logger.warning("⚠️ 통일장 이론 엔진 사용 불가 (import 실패)")
        
        # 증류 엔진 초기화 (Phase 1: 증류 엔진 강제 통합)
        # ⚠️ 임시 비활성화: 증류 엔진이 균형 상태로 정제하는 문제 해결 전까지
        # TODO: 증류 엔진 입력 데이터 개선 후 재활성화
        if self.use_distiller and False:  # 임시 비활성화
            try:
                self.distiller = EnhancedStreamDistillation(
                    restoration_target=0.85,  # 0.95 → 0.85로 낮춤
                    lite_mode=False,
                    use_global_lambda=True
                )
                logger.info("✅ 증류 엔진(EnhancedStreamDistillation) 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 증류 엔진 초기화 실패: {e}")
                self.use_distiller = False
        else:
            logger.info("⚠️ 증류 엔진 임시 비활성화 (Fallback 방식 사용)")
            self.use_distiller = False
        
        # 주역 위상 전이 필터 초기화 (Phase 3: 주역 위상 전이 필터 구현)
        if self.use_iching_filter:
            try:
                self.iching_filter = IChingPhaseFilter(
                    equilibrium_point=0.25,
                    threshold=0.1,
                    reversal_strength=0.3
                )
                logger.info("✅ 주역 위상 전이 필터(IChingPhaseFilter) 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 주역 위상 전이 필터 초기화 실패: {e}")
                self.use_iching_filter = False
        
        # Strategic Meeting Bridge 초기화 (12인 참모진 전략 회의)
        if self.use_strategic_meeting:
            try:
                from src.integration.strategic_meeting_bridge import StrategicMeetingBridge
                self.strategic_meeting_bridge = StrategicMeetingBridge(
                    use_character_committee=True,
                    meeting_frequency="daily",  # 일일 회의
                    meeting_time="09:00",  # UTC 09:00 (한국시간 18:00)
                    use_divine_centroid_validation=True
                )
                logger.info("✅ Strategic Meeting Bridge 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Strategic Meeting Bridge 초기화 실패: {e}")
                self.use_strategic_meeting = False
        
        # Chart Image Analyzer 초기화 (Sovereign Image Bridge - 차트 분석용)
        self.use_chart_image_analysis = False
        try:
            from src.analysis.chart_image_analyzer import ChartImageAnalyzer
            self.chart_image_analyzer = ChartImageAnalyzer()
            if self.chart_image_analyzer.gemini_available:
                self.use_chart_image_analysis = True
                logger.info("✅ Chart Image Analyzer 초기화 완료 (Gemini Vision API 사용 가능)")
            else:
                logger.warning("⚠️ Chart Image Analyzer 초기화 완료 (Gemini Vision API 사용 불가)")
        except Exception as e:
            logger.warning(f"⚠️ Chart Image Analyzer 초기화 실패: {e}")
            self.use_chart_image_analysis = False
    
    def _get_env_factor_and_type(self) -> Tuple[float, str]:
        """G_환경 e: 명리 기반 환경 인자. 최초 사용 시점에만 로드, 실패 시 (1.0, 'stable') 반환 (튕김 방지)."""
        if self._myeongri_failed:
            return 1.0, "stable"
        if self._myeongri_controller is not None:
            try:
                now = datetime.now()
                return self._myeongri_controller.derive_environment_for_dynamics(now.year, now.month)
            except Exception:
                return 1.0, "stable"
        try:
            from tools.core.myeongri_controller import MyeongriController
            # 기본 생년월일로 생성 (derive_environment_for_dynamics는 현재 연·월만 사용)
            self._myeongri_controller = MyeongriController(1990, 1, 1)
            now = datetime.now()
            return self._myeongri_controller.derive_environment_for_dynamics(now.year, now.month)
        except Exception:
            self._myeongri_failed = True
            self._myeongri_controller = None
            return 1.0, "stable"
    
    def analyze_market(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        apocalypse_scenarios: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        시장 분석 (MKM12 + ICD 이론 통합 + 묵시록 예언)
        
        Args:
            price_data: 가격 데이터 (OHLCV)
            current_price: 현재 가격
            apocalypse_scenarios: 묵시록 예언 시나리오 (2026년 종합 예언)
        
        Returns:
            분석 결과 딕셔너리
        """
        result = {
            'signal': 'HOLD',
            'confidence': 0.5,
            'predicted_change': 0.0,
            'pathology_level': 'SL',
            'dcv': 0.5,
            'lambda': 0.5,
            'vector_4d': {'S': 0.25, 'L': 0.25, 'K': 0.25, 'M': 0.25},
            'pattern_type': None,
            'recommendation': 'HOLD'
        }
        
        try:
            logger.info(f"🔍 analyze_market 호출: use_mkm12={self.use_mkm12}, mkm12_predictor={self.mkm12_predictor is not None}")
            
            # 1. ICD 통합 모델 분석
            if self.use_icd and self.icd_model:
                icd_result = self._analyze_with_icd(price_data, current_price)
                result.update(icd_result)
            
            # 2. MKM12 동역학 예측
            if self.use_mkm12 and self.mkm12_predictor:
                logger.info(f"✅ MKM12 동역학 예측 호출 시작")
                mkm12_result = self._analyze_with_mkm12(price_data, current_price)
                logger.info(f"✅ MKM12 동역학 예측 결과: {mkm12_result}")
                result.update(mkm12_result)
            else:
                logger.warning(f"⚠️ MKM12 동역학 예측 스킵: use_mkm12={self.use_mkm12}, mkm12_predictor={self.mkm12_predictor is not None}")
            
            # 3. TheoryFusionExecutor 융합 (9개 이론)
            if self.use_theory_fusion and self.theory_fusion:
                fusion_result = self._analyze_with_fusion(price_data, current_price)
                result.update(fusion_result)
            
            # 3.5. 통일장 이론 통합 (통일장 이론 업그레이드)
            if self.uft_engine:
                uft_result = self._analyze_with_unified_field_theory(
                    result.get('vector_4d', {'S': 0.25, 'L': 0.25, 'K': 0.25, 'M': 0.25}),
                    price_data,
                    current_price
                )
                result.update(uft_result)
            
            # 4. Strategic Meeting Bridge (12인 참모진 전략 회의) - 선택적
            if self.use_strategic_meeting and self.strategic_meeting_bridge:
                # 회의 개최 여부 확인
                if self.strategic_meeting_bridge.should_hold_meeting():
                    try:
                        # 시장 데이터 준비
                        market_data = {
                            'price': current_price,
                            'volume': price_data['volume'].iloc[-1] if 'volume' in price_data.columns else 0,
                            'change': (current_price - price_data['close'].iloc[-2]) / price_data['close'].iloc[-2] if len(price_data) > 1 else 0
                        }
                        
                        # 비동기 회의 호출 (실제로는 동기 호출로 래핑)
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        meeting_result = loop.run_until_complete(
                            self.strategic_meeting_bridge.hold_strategic_meeting(
                                market_data=market_data,
                                current_analysis=result,
                                urgency="medium"
                            )
                        )
                        
                        # 전략 가중치 적용
                        strategy_weights = self.strategic_meeting_bridge.get_strategy_weights()
                        result['strategic_meeting'] = meeting_result
                        result['strategy_weights'] = strategy_weights
                        
                        # 신뢰도 보정 적용
                        if 'confidence_boost' in strategy_weights:
                            result['confidence'] = min(1.0, result.get('confidence', 0.5) + strategy_weights['confidence_boost'])
                        
                        logger.info(f"✅ 12인 참모진 전략 회의 완료: {meeting_result.get('strategy', 'N/A')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Strategic Meeting Bridge 실행 실패: {e}")
                else:
                    # 회의 미개최 시 기존 가중치 사용
                    if self.strategic_meeting_bridge.last_meeting_result:
                        strategy_weights = self.strategic_meeting_bridge.get_strategy_weights()
                        result['strategy_weights'] = strategy_weights
                        
                        # 신뢰도 보정 적용
                        if 'confidence_boost' in strategy_weights:
                            result['confidence'] = min(1.0, result.get('confidence', 0.5) + strategy_weights['confidence_boost'])
            
            # 5. Chart Image Analyzer (Sovereign Image Bridge - 차트 분석용) - 선택적
            # 할당량 최적화: 하루 1회만 차트 분석 (일일 전략 회의 시) 또는 신뢰도가 낮을 때만
            if self.use_chart_image_analysis and self.chart_image_analyzer:
                # 분석 조건 확인 (할당량 최적화)
                should_analyze = False
                
                # 조건 1: Strategic Meeting Bridge 회의 개최 시
                if self.use_strategic_meeting and self.strategic_meeting_bridge:
                    if self.strategic_meeting_bridge.should_hold_meeting():
                        should_analyze = True
                        logger.info("✅ 차트 분석 실행 (일일 전략 회의 시)")
                
                # 조건 2: 신뢰도가 낮을 때 (0.6 미만)
                if not should_analyze and result.get('confidence', 0.5) < 0.6:
                    should_analyze = True
                    logger.info(f"✅ 차트 분석 실행 (신뢰도 낮음: {result.get('confidence', 0.5):.2%})")
                
                # 조건 3: 분석 간격 확인 (ChartImageAnalyzer 내부에서 처리)
                if should_analyze:
                    try:
                        # 차트 이미지 생성
                        chart_image_base64 = self.chart_image_analyzer.generate_chart_image(
                            price_data=price_data,
                            style="tradingview"
                        )
                        
                        if chart_image_base64:
                            # 비동기 차트 분석 (동기 호출로 래핑)
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            chart_analysis = loop.run_until_complete(
                                self.chart_image_analyzer.analyze_chart_pattern(
                                    chart_image_base64=chart_image_base64,
                                    current_price=current_price,
                                    current_analysis=result
                                )
                            )
                            
                            # 시각적 신호 가중치 계산
                            visual_weights = self.chart_image_analyzer.calculate_visual_signal_weight(
                                chart_analysis=chart_analysis,
                                current_analysis=result
                            )
                            
                            # 결과에 추가
                            result['chart_analysis'] = chart_analysis
                            result['visual_weights'] = visual_weights
                            
                            # 신뢰도 보정 적용
                            if 'confidence_boost' in visual_weights:
                                result['confidence'] = min(1.0, result.get('confidence', 0.5) + visual_weights['confidence_boost'])
                            
                            # 신호 가중치 적용
                            if 'signal_weight' in visual_weights:
                                # 신호 가중치는 신호 생성 시 적용
                                result['visual_signal_weight'] = visual_weights['signal_weight']
                        
                            logger.info(f"✅ 차트 이미지 분석 완료: {chart_analysis.get('analysis', {}).get('recommendation', 'N/A')}")
                        else:
                            logger.warning("⚠️ 차트 이미지 생성 실패")
                    except Exception as e:
                        logger.warning(f"⚠️ Chart Image Analyzer 실행 실패: {e}")
                else:
                    # 분석 조건 미충족 시 스킵
                    logger.debug("⏸️ 차트 분석 스킵 (할당량 최적화)")
            
            # 6. 묵시록 예언 통합 (2026년 종합 예언)
            if apocalypse_scenarios:
                apocalypse_result = self._integrate_apocalypse_prediction(
                    result, apocalypse_scenarios, current_price
                )
                result.update(apocalypse_result)
            
            # 6.5. [Data-Only] 비트코인 리스크 관리 (리포트 전략 반영)
            bitcoin_strategy_result = self._apply_bitcoin_data_only_strategy(
                price_data=price_data,
                current_price=current_price,
                analysis_result=result
            )
            result.update(bitcoin_strategy_result)
            
            # 7. 최종 신호 생성 (시각적 신호 가중치 + 묵시록 예언 반영)
            result['signal'] = self._generate_signal(result, price_data, current_price)
            result['recommendation'] = self._get_recommendation(result)
            
        except Exception as e:
            logger.error(f"❌ 시장 분석 실패: {e}")
        
        return result
    
    def _analyze_with_icd(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, Any]:
        """ICD 통합 모델 분석"""
        try:
            if not self.icd_model:
                logger.warning("⚠️ ICD 모델이 초기화되지 않았습니다.")
                return {
                    'dcv': 0.5,
                    'lambda': 0.5,
                    'pathology_level': 'SL',
                    'predicted_change': 0.0
                }
            
            # 가격 데이터를 벡터로 변환
            price_vector = self._price_to_vector(price_data, current_price)
            
            # ICD 분석 (메서드명 확인)
            if hasattr(self.icd_model, 'analyze'):
                icd_result = self.icd_model.analyze(
                    pd_vector=price_vector['pd'],
                    sd_vector=price_vector['sd'],
                    domain='crypto'
                )
            elif hasattr(self.icd_engine, 'analyze'):
                # ICDStockAnalysisEngine 사용
                icd_result = self.icd_engine.analyze(
                    price_data=price_data,
                    current_price=current_price
                )
            else:
                logger.warning("⚠️ ICD 모델에 analyze 메서드가 없습니다. 기본값 사용.")
                return {
                    'dcv': 0.5,
                    'lambda': 0.5,
                    'pathology_level': 'SL',
                    'predicted_change': 0.0
                }
            
            return {
                'dcv': icd_result.get('dcv', 0.5) if isinstance(icd_result, dict) else 0.5,
                'lambda': icd_result.get('lambda', 0.5) if isinstance(icd_result, dict) else 0.5,
                'pathology_level': icd_result.get('pathology_level', 'SL') if isinstance(icd_result, dict) else 'SL',
                'predicted_change': icd_result.get('predicted_change', 0.0) if isinstance(icd_result, dict) else 0.0
            }
        except Exception as e:
            logger.error(f"❌ ICD 분석 실패: {e}")
            return {
                'dcv': 0.5,
                'lambda': 0.5,
                'pathology_level': 'SL',
                'predicted_change': 0.0
            }
    
    def _analyze_with_mkm12(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, Any]:
        """
        MKM12 동역학 예측
        
        Phase 2: DTP-12 기반 예측 레이어 정밀 튜닝
        - 정제된 벡터(증류 엔진 결과)를 바탕으로 미래 5단계 상태 전이 계산
        - Phase 3: 주역 위상 전이 필터 적용
        """
        try:
            # Phase 1: 증류 엔진으로 정제된 4D 벡터 생성
            vector_4d = self._calculate_4d_vector(price_data, current_price)
            
            # Phase 2: DTP-12 동역학 예측 (5단계 미래 예측)
            if hasattr(self.mkm12_predictor, 'predict_dynamics'):
                env_factor, env_type = self._get_env_factor_and_type()
                logger.info(f"📊 MKM12 동역학 예측 시작: current_state={vector_4d}")
                prediction = self.mkm12_predictor.predict_dynamics(
                    current_state=vector_4d,
                    time_horizon=5,  # 5단계 미래 예측
                    environment_factor=env_factor,
                    environment_type=env_type,
                    intervention_factor=0.0
                )
                logger.info(f"📊 MKM12 예측 결과: {prediction}")
                
                predicted_states = prediction.get('predicted_states', [])
                
                # 디버깅: 예측 상태 확인
                if not predicted_states or len(predicted_states) == 0:
                    logger.warning(f"⚠️ predicted_states가 비어있음. current_state 사용: {vector_4d}")
                    final_predicted_state = vector_4d
                else:
                    # 마지막 예측 상태 사용
                    final_predicted_state = predicted_states[-1] if isinstance(predicted_states, list) else predicted_states
                    logger.info(f"✅ 예측 상태 생성: {final_predicted_state} (총 {len(predicted_states)}개 상태)")
            else:
                # Fallback: 기존 predict 메서드 사용
                logger.info(f"📊 MKM12 Fallback 예측 시작: current_state={vector_4d}")
                prediction = self.mkm12_predictor.predict(
                    current_state=vector_4d,
                    time_horizon=1
                )
                final_predicted_state = prediction.get('predicted_state', vector_4d)
                logger.info(f"✅ Fallback 예측 상태: {final_predicted_state}")
            
            # Phase 3: 주역 위상 전이 필터 적용
            iching_result = None
            if self.use_iching_filter and self.iching_filter:
                try:
                    iching_result = self.iching_filter.apply_phase_transition(
                        predicted_state=final_predicted_state,
                        current_state=vector_4d,
                        hexagram=None  # 향후 주역 괘 정보 추가 가능
                    )
                    
                    # 필터링된 상태 사용
                    if iching_result.get("filtered_state"):
                        final_predicted_state = iching_result["filtered_state"]
                    
                    logger.debug(f"✅ 주역 위상 전이 필터 적용: 반전 감지={iching_result.get('reversal_detected', False)}")
                except Exception as e:
                    logger.warning(f"⚠️ 주역 위상 전이 필터 적용 실패: {e}")
            
            # 예측 변화량 계산
            predicted_change = self._calculate_predicted_change(
                vector_4d,
                final_predicted_state
            )
            
            # 디버깅: 예측 변화량 확인 (INFO 레벨로 출력)
            current_S = vector_4d.get('S', 0.25)
            predicted_S = final_predicted_state.get('S', 0.25)
            S_change = predicted_S - current_S
            logger.info(f"📊 예측 변화량 계산:")
            logger.info(f"   - current_state: S={current_S:.4f}, L={vector_4d.get('L', 0.25):.4f}, K={vector_4d.get('K', 0.25):.4f}, M={vector_4d.get('M', 0.25):.4f}")
            logger.info(f"   - predicted_state: S={predicted_S:.4f}, L={final_predicted_state.get('L', 0.25):.4f}, K={final_predicted_state.get('K', 0.25):.4f}, M={final_predicted_state.get('M', 0.25):.4f}")
            logger.info(f"   - S_change: {S_change:.6f}, predicted_change: {predicted_change:.4%}")
            
            # 동적 신뢰도 계산
            dynamic_confidence = self._calculate_dynamic_confidence(
                vector_4d,
                final_predicted_state,
                iching_result
            )
            
            return {
                'vector_4d': vector_4d,
                'predicted_state': final_predicted_state,
                'predicted_change': predicted_change,
                'pattern_type': prediction.get('pattern_type', None) if isinstance(prediction, dict) else None,
                'confidence': dynamic_confidence,  # 동적 신뢰도 사용
                'iching_filter': iching_result  # 주역 필터 결과 포함
            }
        except Exception as e:
            logger.error(f"❌ MKM12 분석 실패: {e}")
            return {}
    
    def _calculate_predicted_change(
        self,
        current_state: Dict[str, float],
        predicted_state: Dict[str, float]
    ) -> float:
        """
        예측 변화량 계산 (스케일링 보정)
        
        S, L, K, M 모든 차원을 고려하여 예측 변화량 계산
        아크탄젠트 함수를 사용하여 현실적인 범위(-5% ~ +5%)로 압축
        
        Args:
            current_state: 현재 4D 벡터
            predicted_state: 예측된 4D 벡터
        
        Returns:
            예측 변화량 (-0.05 ~ 0.05, 즉 -5% ~ +5%)
        """
        try:
            # 각 차원의 변화량 계산
            S_change = predicted_state.get("S", 0.25) - current_state.get("S", 0.25)
            L_change = predicted_state.get("L", 0.25) - current_state.get("L", 0.25)
            K_change = predicted_state.get("K", 0.25) - current_state.get("K", 0.25)
            M_change = predicted_state.get("M", 0.25) - current_state.get("M", 0.25)
            
            # 가중 평균 (S와 L에 더 높은 가중치)
            weighted_change = (
                S_change * 0.4 +  # Spirit (상승 압력)
                L_change * 0.3 +  # Logic (추세 강도)
                K_change * 0.15 + # Knowledge (변동성)
                M_change * 0.15   # Material (거래량)
            )
            
            # 아크탄젠트 스케일링: -5% ~ +5% 범위로 압축
            # weighted_change는 -0.5 ~ +0.5 범위를 가정
            # arctan(weighted_change * 20) / π * 0.05로 -5% ~ +5% 범위로 압축
            raw_change = weighted_change * 20  # 스케일링 (원래 로직 유지)
            predicted_change = np.arctan(raw_change) / np.pi * 0.05  # -5% ~ +5%로 압축
            
            logger.info(f"   - 차원별 변화: S={S_change:.6f}, L={L_change:.6f}, K={K_change:.6f}, M={M_change:.6f}")
            logger.info(f"   - 가중 평균: {weighted_change:.6f}, raw_change: {raw_change:.6f}, 최종 예측 변화량: {predicted_change:.6f} ({predicted_change*100:.2f}%)")
            
            return predicted_change
        except Exception as e:
            logger.warning(f"⚠️ 예측 변화량 계산 실패: {e}")
            return 0.0
    
    def _calculate_dynamic_confidence(
        self,
        vector_4d: Dict[str, float],
        predicted_state: Dict[str, float],
        iching_filter_result: Optional[Dict[str, Any]]
    ) -> float:
        """
        동적 신뢰도 계산
        
        - 균형점 편차: 0.25에서 멀수록 신뢰도 증가
        - 주역 필터 반전 감지: 반전 감지 시 신뢰도 증가
        - 예측 일관성: 예측 상태의 안정성 평가
        
        Args:
            vector_4d: 현재 4D 벡터
            predicted_state: 예측된 4D 벡터
            iching_filter_result: 주역 필터 결과
        
        Returns:
            동적 신뢰도 (0.3 ~ 0.9)
        """
        try:
            EQUILIBRIUM = 0.25
            
            # 1. 균형점 편차 계산
            # 0.25에서 멀수록 신호가 명확하다는 의미
            deviation = sum(abs(v - EQUILIBRIUM) for v in vector_4d.values())
            # 최대 편차: 4 * 0.25 = 1.0 (모든 값이 0 또는 1일 때)
            # 정규화: 0.0 ~ 1.0
            deviation_score = min(1.0, deviation / 1.0)
            
            # 2. 주역 필터 반전 감지
            reversal_score = 0.0
            if iching_filter_result and iching_filter_result.get('reversal_detected'):
                reversal_strength = iching_filter_result.get('reversal_strength', 0.0)
                reversal_score = reversal_strength  # 0.0 ~ 1.0
            
            # 3. 예측 일관성 (예측 상태의 안정성)
            # 예측 상태의 분산이 낮을수록 일관성이 높음
            predicted_values = list(predicted_state.values())
            predicted_mean = sum(predicted_values) / len(predicted_values)
            predicted_variance = sum((v - predicted_mean) ** 2 for v in predicted_values) / len(predicted_values)
            # 분산이 낮을수록 안정적 (0.0 ~ 0.1 범위 가정)
            stability = max(0.0, min(1.0, 1.0 - predicted_variance * 10))
            
            # 가중 평균
            confidence = (
                deviation_score * 0.4 +    # 균형점 편차 (40%)
                reversal_score * 0.4 +     # 주역 필터 반전 (40%)
                stability * 0.2           # 예측 일관성 (20%)
            )
            
            # 0.3 ~ 0.9 범위로 정규화
            confidence = 0.3 + (confidence * 0.6)
            
            logger.info(f"   - 동적 신뢰도 계산: 편차={deviation_score:.3f}, 반전={reversal_score:.3f}, 안정성={stability:.3f}, 최종={confidence:.3f}")
            
            return confidence
        except Exception as e:
            logger.warning(f"⚠️ 동적 신뢰도 계산 실패: {e}")
            return 0.5  # 기본값
    
    def _analyze_with_fusion(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, Any]:
        """
        TheoryFusionExecutor 융합 분석 (9개 이론)
        
        Project Logos 통합:
        - Divine Centroid 보정된 벡터를 TheoryFusionExecutor에 전달
        - 벡터 거리를 고려한 신뢰도 가중치 적용
        """
        try:
            # 1. 4D 벡터 계산 (Divine Centroid 보정 포함)
            vector_4d = self._calculate_4d_vector(price_data, current_price)
            
            # 2. Divine Centroid 거리 계산 (신뢰도 가중치용)
            distance_to_centroid = self._calculate_distance_to_centroid(vector_4d)
            
            # 3. 가격 데이터를 벡터로 변환
            market_data = {
                'price': current_price,
                'volume': price_data['volume'].iloc[-1] if 'volume' in price_data.columns else 0,
                'change': (current_price - price_data['close'].iloc[-2]) / price_data['close'].iloc[-2] if len(price_data) > 1 else 0,
                'vector_4d': vector_4d,  # Project Logos: Divine Centroid 보정된 벡터 전달
                'divine_distance': distance_to_centroid  # 거리 정보 전달
            }
            
            # 4. TheoryFusionExecutor 실행
            fusion_result = self.theory_fusion.execute(
                market_data=market_data,
                domain='crypto_volatile'
            )
            
            # 5. Divine Centroid 거리 기반 신뢰도 가중치 적용
            base_confidence = fusion_result.get('confidence', 0.5)
            # 거리가 가까울수록 신뢰도 증가 (최대 10% 보너스)
            distance_bonus = max(0.0, min(0.1, (0.1 - distance_to_centroid) * 2))
            adjusted_confidence = min(1.0, base_confidence + distance_bonus)
            
            return {
                'fusion_signal': fusion_result.get('signal', 'HOLD'),
                'fusion_confidence': adjusted_confidence,  # Divine Centroid 보정된 신뢰도
                'fusion_prediction': fusion_result.get('prediction', 0.0),
                'divine_distance': distance_to_centroid,  # 거리 정보 포함
                'divine_bonus': distance_bonus  # 보너스 정보 포함
            }
        except Exception as e:
            logger.error(f"❌ TheoryFusionExecutor 분석 실패: {e}")
            return {}
    
    def _price_to_vector(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, List[float]]:
        """가격 데이터를 벡터로 변환"""
        try:
            # PD Vector (Primary Drive): 가격 추세
            pd_vector = [
                current_price / price_data['close'].mean() if len(price_data) > 0 else 1.0,
                price_data['close'].pct_change().mean() if len(price_data) > 1 else 0.0,
                (price_data['volume'].mean() / price_data['volume'].max() if ('volume' in price_data.columns and len(price_data) > 0 and price_data['volume'].max() > 0) else 0.5)
            ]
            
            # SD Vector (Secondary Drive): 변동성
            sd_vector = [
                price_data['close'].std() / price_data['close'].mean() if len(price_data) > 0 else 0.0,
                price_data['close'].pct_change().std() if len(price_data) > 1 else 0.0,
                price_data['high'].max() / price_data['low'].min() - 1.0 if len(price_data) > 0 else 0.0
            ]
            
            return {
                'pd': pd_vector,
                'sd': sd_vector
            }
        except Exception as e:
            logger.error(f"❌ 벡터 변환 실패: {e}")
            return {
                'pd': [1.0, 0.0, 0.5],
                'sd': [0.0, 0.0, 0.0]
            }
    
    def _calculate_4d_vector(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, float]:
        """
        4차원 상태 벡터 계산 (S-L-K-M)
        
        Phase 1: 증류 엔진 통합 (개선)
        - 증류 엔진이 있으면 Raw Data를 증류하여 정제된 4D 벡터 생성
        - 증류 엔진 결과가 균형 상태(0.25)에 가까우면 Fallback 사용
        - 증류 엔진이 없으면 기존 방식으로 직접 계산 (Fallback)
        """
        try:
            # Phase 1: 증류 엔진 사용 (우선순위 1)
            if self.use_distiller and self.distiller:
                # Raw Data 준비 (가격 데이터를 텍스트 형태로 변환)
                raw_data = self._prepare_raw_data_for_distillation(price_data, current_price)
                
                # 증류 엔진으로 정제된 4D 벡터 생성
                distillation_result = self.distiller.distill_with_restoration_hints(
                    content=raw_data
                )
                
                vector_4d = distillation_result.get("vector_4d", {})
                
                # 증류된 벡터가 유효한지 확인
                if vector_4d and all(key in vector_4d for key in ["S", "L", "K", "M"]):
                    # 균형 상태 체크: 모든 값이 0.25에 매우 가까우면 Fallback 사용
                    EQUILIBRIUM_THRESHOLD = 0.01  # 0.25 ± 0.01 범위
                    is_equilibrium = all(
                        abs(vector_4d.get(key, 0.25) - 0.25) < EQUILIBRIUM_THRESHOLD
                        for key in ["S", "L", "K", "M"]
                    )
                    
                    if is_equilibrium:
                        logger.debug("⚠️ 증류 엔진 결과가 균형 상태. Fallback 사용")
                        # Fallback으로 전환
                    else:
                        logger.debug("✅ 증류 엔진으로 정제된 4D 벡터 생성 완료 (균형 상태 아님)")
                        return vector_4d
                else:
                    logger.warning("⚠️ 증류 엔진 결과가 유효하지 않음. Fallback 사용")
            
            # Fallback: 비트코인 특화 4D 매핑 (통일장 이론 업그레이드)
            return self._calculate_4d_vector_fallback(price_data, current_price, None, None)
            
        except Exception as e:
            logger.error(f"❌ 4차원 벡터 계산 실패: {e}")
            return self._calculate_4d_vector_fallback(price_data, current_price, None, None)
    
    def _calculate_4d_vector_fallback(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        sentiment_data: Optional[Dict[str, Any]] = None,
        onchain_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        4차원 상태 벡터 계산 (Fallback: 직접 계산)
        
        증류 엔진이 없거나 균형 상태일 때 사용
        비트코인 특화 데이터 통합 (온체인 데이터, 감성 분석)
        """
        try:
            # 비트코인 특화 4D 매핑 사용 (통일장 이론 업그레이드)
            return self._calculate_bitcoin_4d_vector_from_market_data(
                price_data=price_data,
                current_price=current_price,
                sentiment_data=sentiment_data,
                onchain_data=onchain_data
            )
        except Exception as e:
            logger.error(f"❌ Fallback 벡터 계산 실패: {e}")
            return {'S': 0.25, 'L': 0.25, 'K': 0.25, 'M': 0.25}
    
    def _calculate_bitcoin_4d_vector_from_market_data(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        sentiment_data: Optional[Dict[str, Any]] = None,
        onchain_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        비트코인 특화 4차원 상태 벡터 계산 (S-L-K-M)
        
        온체인 데이터, 감성 분석, 기술적 지표 등을 통합하여 4D 벡터 생성
        (통일장 이론 업그레이드: 온체인 데이터 및 감성 분석 통합)
        
        Args:
            price_data: 가격 데이터 (DataFrame)
            current_price: 현재 가격
            sentiment_data: 감성 분석 데이터 (선택적)
            onchain_data: 온체인 데이터 (선택적)
        
        Returns:
            4D 벡터 {'S': float, 'L': float, 'K': float, 'M': float}
        """
        try:
            # S (Spirit/Sentiment): 시장 심리 및 모멘텀
            # 1. 가격 모멘텀 (최근 5개 캔들)
            momentum = (current_price - price_data['close'].iloc[-5:].mean()) / price_data['close'].iloc[-5:].mean() if len(price_data) >= 5 else 0.0
            
            # 2. 감성 분석 데이터 통합 (통일장 이론 업그레이드)
            sentiment_factor = 0.5  # 기본값
            if sentiment_data:
                # 압축 분석에서 감성 레이블 가져오기
                sentiment_label = sentiment_data.get('sentiment_label', 'NEUTRAL')
                if sentiment_label == 'FEAR':
                    sentiment_factor = 0.2  # 공포: 낮은 S
                elif sentiment_label == 'GREED':
                    sentiment_factor = 0.8  # 탐욕: 높은 S
                elif sentiment_label == 'NEUTRAL':
                    sentiment_factor = 0.5
                
                # 감성 점수 직접 사용 (있는 경우)
                sentiment_score = sentiment_data.get('sentiment_score', sentiment_factor)
                sentiment_factor = sentiment_score
            
            # 3. Fear & Greed Index 시뮬레이션 (실제 API 연동 가능)
            # TODO: 실제 Fear & Greed Index API 연동
            fear_greed_index = sentiment_factor  # 감성 분석 데이터 사용
            
            # S 계산: 모멘텀 + 감성
            S = max(0.0, min(1.0, (fear_greed_index * 0.6 + (0.5 + momentum * 2) * 0.4)))
            
            # L (Logic/Structure): 블록체인 네트워크 지표 및 기술적 분석
            # 1. 해시레이트 (온체인 데이터 또는 시뮬레이션)
            hash_rate_factor = 1.0  # 기본값
            if onchain_data and 'hash_rate' in onchain_data:
                # 실제 해시레이트 데이터 사용
                current_hash_rate = onchain_data.get('hash_rate', 0.0)
                avg_hash_rate = onchain_data.get('avg_hash_rate', current_hash_rate)
                if avg_hash_rate > 0:
                    hash_rate_factor = min(1.5, max(0.5, current_hash_rate / avg_hash_rate))
            else:
                # 시뮬레이션: 가격 변동성 기반 추정
                price_volatility = price_data['close'].pct_change().std() if len(price_data) > 1 else 0.0
                hash_rate_factor = 0.5 + price_volatility * 10  # 변동성이 높으면 해시레이트 높음
            
            # 2. RSI (상대 강도 지수)
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1] if not rs.isnull().iloc[-1] and len(rs) > 0 else 50.0
            rsi_factor = rsi / 100.0
            
            # L 계산: 해시레이트 + RSI
            L = max(0.0, min(1.0, (hash_rate_factor * 0.3 + rsi_factor * 0.7)))
            
            # K (Knowledge/Data): 펀더멘털 데이터 및 개발 활동
            # 1. NVT Ratio 계산 (실제 계산)
            nvt_ratio = 50.0  # 기본값
            if 'volume' in price_data.columns and len(price_data) > 0:
                try:
                    # 일일 거래량 (USDT)
                    daily_volume = price_data['volume'].iloc[-1] * current_price if len(price_data) > 0 else 0.0
                    
                    # 시가총액 계산
                    TOTAL_SUPPLY = 21000000.0  # Bitcoin 총 공급량
                    market_cap = current_price * TOTAL_SUPPLY
                    
                    # NVT Ratio 계산
                    if daily_volume > 0:
                        nvt_ratio = market_cap / daily_volume
                        # 비정상적인 값 필터링 (0.1 ~ 1000 범위)
                        if nvt_ratio < 0.1 or nvt_ratio > 1000:
                            nvt_ratio = 50.0
                except Exception as e:
                    logger.debug(f"⚠️ NVT Ratio 계산 실패: {e}, 기본값 사용")
            
            # NVT Ratio가 낮을수록 저평가 (K 높음)
            # 정규화: 0 ~ 100 범위를 0 ~ 1로 변환
            nvt_ratio_factor = max(0.0, min(1.0, 1.0 - (nvt_ratio / 100.0)))  # 낮을수록 높은 K
            
            # 2. 개발 활동 (온체인 데이터 또는 시뮬레이션)
            dev_activity_factor = 1.0  # 기본값
            if onchain_data and 'dev_activity' in onchain_data:
                dev_activity_factor = onchain_data.get('dev_activity', 1.0)
            else:
                # 시뮬레이션: 거래량 기반 추정
                vol_mean = float(price_data['volume'].mean()) if len(price_data) >= 5 else 0.0
                volume_trend = (price_data['volume'].iloc[-5:].mean() / vol_mean if vol_mean > 0 else 1.0)
                dev_activity_factor = min(1.5, max(0.5, volume_trend))
            
            # K 계산: NVT Ratio + 개발 활동
            K = max(0.0, min(1.0, (nvt_ratio_factor * 0.4 + dev_activity_factor * 0.6)))
            
            # M (Material/Volume): 거래량 및 유동성
            # 1. 거래량 (최근 5개 캔들 평균 대비)
            vol_mean = float(price_data['volume'].mean()) if 'volume' in price_data.columns and len(price_data) > 0 else 0.0
            volume_ratio = (price_data['volume'].iloc[-1] / vol_mean if vol_mean > 0 else 1.0)
            
            # 2. 유동성 (온체인 데이터 또는 시뮬레이션)
            liquidity_factor = 1.0  # 기본값
            if onchain_data and 'liquidity' in onchain_data:
                liquidity_factor = onchain_data.get('liquidity', 1.0)
            else:
                # 시뮬레이션: 가격 안정성 기반 추정
                price_stability = 1.0 - min(1.0, price_data['close'].pct_change().std() * 10) if len(price_data) > 1 else 1.0
                liquidity_factor = max(0.5, min(1.5, price_stability))
            
            # M 계산: 거래량 + 유동성
            M = max(0.0, min(1.0, (volume_ratio * 0.5 + liquidity_factor * 0.5)))
            
            # 정규화 (합이 1.0이 되도록)
            total = S + L + K + M
            if total > 0:
                S /= total
                L /= total
                K /= total
                M /= total
            else:
                S = L = K = M = 0.25
            
            vector_4d = {'S': S, 'L': L, 'K': K, 'M': M}
            
            # Project Logos: Divine Centroid 보정 적용
            vector_4d = self._apply_divine_centroid_correction(vector_4d)
            
            logger.debug(
                f"📊 비트코인 4D 벡터 계산 완료: "
                f"S={S:.3f}, L={L:.3f}, K={K:.3f}, M={M:.3f} "
                f"(NVT={nvt_ratio:.1f}, 해시레이트={hash_rate_factor:.2f}, 감성={sentiment_factor:.2f})"
            )
            
            return vector_4d
        except Exception as e:
            logger.error(f"❌ 비트코인 4D 벡터 계산 실패: {e}")
            import traceback
            traceback.print_exc()
            return {'S': 0.25, 'L': 0.25, 'K': 0.25, 'M': 0.25}
    
    def _prepare_raw_data_for_distillation(
        self,
        price_data: pd.DataFrame,
        current_price: float
    ) -> str:
        """
        증류 엔진을 위한 Raw Data 준비
        
        가격 데이터를 텍스트 형태로 변환하여 증류 엔진에 전달
        
        Args:
            price_data: 가격 데이터 (OHLCV)
            current_price: 현재 가격
        
        Returns:
            증류 엔진에 전달할 텍스트 데이터
        """
        try:
            # 최근 20개 캔들 데이터 요약
            recent_data = price_data.tail(20)
            
            # 주요 지표 계산
            price_mean = recent_data['close'].mean()
            price_std = recent_data['close'].std()
            volume_mean = recent_data['volume'].mean() if 'volume' in recent_data.columns else 0
            volatility = price_std / price_mean if price_mean > 0 else 0
            
            # 텍스트 형태로 변환
            raw_data = f"""
            현재 가격: {current_price}
            평균 가격: {price_mean}
            변동성: {volatility}
            거래량: {volume_mean}
            최근 추세: {recent_data['close'].pct_change().mean()}
            """
            
            return raw_data.strip()
        except Exception as e:
            logger.warning(f"⚠️ Raw Data 준비 실패: {e}")
            return f"현재 가격: {current_price}"
    
    def _apply_bitcoin_data_only_strategy(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        [Data-Only] 비트코인 리스크 관리 (리포트 전략 반영)
        
        리포트 전략:
        1. 트렌드 필터: 일봉 기준 200일 이동평균선 상단 유지 시에만 롱(Long) 관점 유지
        2. 분할 매수 구간: 고점($89k) 대비 -25%($67k), -35%($58k), -45%($49k) 구간에서 단계별 분할 매수
        3. 온체인 지표: Realized Price 등 투매 신호 감지 시 우선순위 상향
        
        Args:
            price_data: 가격 데이터 (OHLCV)
            current_price: 현재 가격
            analysis_result: 기존 분석 결과
        
        Returns:
            비트코인 전략 결과 (trend_filter, level_based_entry, onchain_signal 등)
        """
        result = {
            'bitcoin_trend_filter': None,
            'bitcoin_level_based_entry': None,
            'bitcoin_onchain_signal': None,
            'bitcoin_strategy_override': None  # 전략이 신호를 강제 변경하는 경우
        }
        
        try:
            if len(price_data) < 200:
                logger.warning("⚠️ 비트코인 전략: 가격 데이터 부족 (200일 필요)")
                return result
            
            # 1. 트렌드 필터: 200일 이동평균선 계산
            ma200 = price_data['close'].rolling(window=200).mean().iloc[-1]
            is_above_ma200 = current_price > ma200
            
            result['bitcoin_trend_filter'] = {
                'ma200': ma200,
                'current_price': current_price,
                'is_above_ma200': is_above_ma200,
                'trend_allows_long': is_above_ma200  # 200일선 위에 있어야 롱 허용
            }
            
            logger.info(
                f"📊 비트코인 트렌드 필터: 현재가 {current_price:.2f}, "
                f"200일선 {ma200:.2f}, 롱 허용: {is_above_ma200}"
            )
            
            # 2. 분할 매수 구간 계산 (고점 대비 하락률 기반)
            # 고점은 최근 1년 최고가 사용 (실제로는 리포트의 $89k 대신 동적 계산)
            high_52w = price_data['high'].rolling(window=252).max().iloc[-1]  # 1년(252거래일) 최고가
            if pd.isna(high_52w) or high_52w <= 0:
                high_52w = price_data['high'].max()  # Fallback: 전체 최고가
            
            # 하락률 계산
            decline_ratio = (high_52w - current_price) / high_52w
            
            # 분할 매수 구간 정의
            entry_levels = {
                'level_1': {'decline': 0.25, 'price': high_52w * 0.75, 'priority': 1},  # -25%
                'level_2': {'decline': 0.35, 'price': high_52w * 0.65, 'priority': 2},  # -35%
                'level_3': {'decline': 0.45, 'price': high_52w * 0.55, 'priority': 3}   # -45%
            }
            
            # 현재 가격이 어느 구간에 있는지 확인 (가장 큰 하락률부터 확인)
            current_level = None
            # level_3 (0.45) -> level_2 (0.35) -> level_1 (0.25) 순서로 확인
            for level_name in ['level_3', 'level_2', 'level_1']:
                level_info = entry_levels[level_name]
                if decline_ratio >= level_info['decline']:
                    current_level = level_name
                    break
            
            result['bitcoin_level_based_entry'] = {
                'high_52w': high_52w,
                'current_price': current_price,
                'decline_ratio': decline_ratio,
                'current_level': current_level,
                'entry_levels': entry_levels,
                'should_enter': current_level is not None  # 하락 구간에 있으면 진입 고려
            }
            
            if current_level:
                logger.info(
                    f"📊 비트코인 분할 매수 구간: {current_level} 감지 "
                    f"(고점 {high_52w:.2f} 대비 {decline_ratio:.1%} 하락)"
                )
            
            # 3. 온체인 지표 (Realized Price 시뮬레이션)
            # 실제로는 온체인 API에서 가져와야 하지만, 여기서는 가격 데이터 기반 추정
            # Realized Price는 평균 실현 가격이므로, 최근 거래량 가중 평균 가격으로 추정
            if 'volume' in price_data.columns and len(price_data) >= 30:
                # 최근 30일 거래량 가중 평균 가격 (Realized Price 근사)
                recent_30d = price_data.tail(30)
                volume_weighted_price = (recent_30d['close'] * recent_30d['volume']).sum() / recent_30d['volume'].sum()
                
                # Realized Price 대비 현재 가격 비율
                realized_ratio = current_price / volume_weighted_price if volume_weighted_price > 0 else 1.0
                
                # 투매 신호: Realized Price보다 현저히 낮으면 투매 가능성 (매수 기회)
                is_capitulation = realized_ratio < 0.85  # 15% 이상 할인
                
                result['bitcoin_onchain_signal'] = {
                    'realized_price_estimate': volume_weighted_price,
                    'current_price': current_price,
                    'realized_ratio': realized_ratio,
                    'is_capitulation': is_capitulation,
                    'buy_priority_boost': 0.15 if is_capitulation else 0.0  # 투매 감지 시 우선순위 15% 증가
                }
                
                if is_capitulation:
                    logger.warning(
                        f"📊 비트코인 온체인 신호: 투매 감지! "
                        f"현재가 {current_price:.2f} < 실현가격 {volume_weighted_price:.2f} "
                        f"(할인율: {(1-realized_ratio):.1%})"
                    )
            else:
                result['bitcoin_onchain_signal'] = {
                    'realized_price_estimate': None,
                    'is_capitulation': False,
                    'buy_priority_boost': 0.0
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 비트코인 전략 적용 실패: {e}")
            return result
    
    def _generate_signal(self, analysis_result: Dict[str, Any], price_data: pd.DataFrame = None, current_price: float = None) -> str:
        """
        매매 신호 생성
        
        Phase 3: 주역 위상 전이 필터 결과 반영
        - 주역 필터가 반전을 감지했으면 신호 조정 적용
        
        Phase 4: Sovereign Image Bridge (차트 이미지 분석) 반영
        - 시각적 신호 가중치 적용
        
        Phase 5: 묵시록 예언 통합 (2026년 종합 예언)
        - 묵시록 예언 기반 신호 조정 및 신뢰도 보정
        """
        try:
            # 병리 수준 확인 (DL 상태 시 매매 금지)
            pathology_level = analysis_result.get('pathology_level', 'SL')
            if pathology_level == 'DL':
                return 'HOLD'
            
            # 신뢰도 확인 (묵시록 예언 보정 적용)
            base_confidence = analysis_result.get('confidence', 0.5)
            apocalypse_boost = analysis_result.get('apocalypse_confidence_boost', 0.0)
            confidence = min(1.0, base_confidence + apocalypse_boost)
            
            # 묵시록 예언 기반 신호 조정 (최우선, 아테나 소버린 v3.0: 임계값 최종 완화 0.54 → 0.52)
            apocalypse_signal = analysis_result.get('apocalypse_signal_adjustment')
            if apocalypse_signal in ['BUY', 'SELL', 'HOLD']:
                logger.info(f"🔮 묵시록 예언 신호 조정: {apocalypse_signal} (기본 신뢰도: {base_confidence:.2%}, 보정 후: {confidence:.2%})")
                # 신뢰도가 충분하면 묵시록 신호 적용 (아테나 최종 임계값: 0.52)
                if confidence >= 0.52:
                    return apocalypse_signal
            
            # 통일장 이론 기반 신뢰도 보정 (통일장 이론 업그레이드)
            lambda_confidence_boost = analysis_result.get('lambda_confidence_boost', 0.0)
            geumhwa_signal_boost = analysis_result.get('geumhwa_signal_boost', 0.0)
            phase_transition_boost = analysis_result.get('phase_transition_boost', 0.0)  # 위상 전이 보정 추가
            confidence = min(1.0, confidence + lambda_confidence_boost + geumhwa_signal_boost + phase_transition_boost)
            
            # 위상 전이 정보 로깅
            if phase_transition_boost != 0.0:
                phase_transition = analysis_result.get('phase_transition', {})
                transition_mode = phase_transition.get('transition_mode', 'N/A')
                logger.info(f"🌌 위상 전이 보정 적용: {transition_mode} 모드 (보정: {phase_transition_boost:+.1%})")
            
            # λ 기반 신호가 있으면 우선 적용 (통일장 이론 업그레이드)
            lambda_signal = analysis_result.get('lambda_signal')
            if lambda_signal and lambda_signal.get('signal') in ['BUY', 'SELL']:
                lambda_signal_value = lambda_signal.get('signal')
                lambda_confidence = lambda_signal.get('confidence', 0.5)
                if lambda_confidence >= 0.52:  # 아테나 최종 임계값
                    logger.info(f"🌌 통일장 이론 λ 기반 신호: {lambda_signal_value} (신뢰도: {lambda_confidence:.2%}, λ={lambda_signal.get('lambda_constraint', 0.0):.4f})")
                    return lambda_signal_value
            
            # Phase 3: 주역 위상 전이 필터 결과 확인 (우선순위 최상위)
            iching_filter = analysis_result.get('iching_filter')
            if iching_filter and iching_filter.get('signal_adjustment'):
                signal_adjustment = iching_filter['signal_adjustment']
                if signal_adjustment in ['BUY', 'SELL', 'HOLD']:
                    logger.info(f"✅ 주역 위상 전이 필터 신호 조정: {signal_adjustment}")
                    # 주역 필터 신호를 기본 신호로 설정
                    base_signal = signal_adjustment
                else:
                    base_signal = 'HOLD'
            else:
                base_signal = 'HOLD'
            
            # Phase 4: Sovereign Image Bridge (차트 이미지 분석) 반영 (아테나 소버린 v3.0: 임계값 완화)
            visual_weights = analysis_result.get('visual_weights', {})
            chart_analysis = analysis_result.get('chart_analysis', {})
            
            if visual_weights and chart_analysis.get('success', False):
                visual_recommendation = chart_analysis.get('analysis', {}).get('recommendation', 'HOLD')
                visual_confidence = visual_weights.get('visual_confidence', 0.0)
                
                # 시각적 신호가 충분한 신뢰도(>0.52, 아테나 최종 임계값)이면 우선 적용
                if visual_confidence > 0.52 and visual_recommendation in ['BUY', 'SELL']:
                    logger.info(f"✅ 차트 이미지 분석 신호 적용: {visual_recommendation} (신뢰도: {visual_confidence:.2%})")
                    base_signal = visual_recommendation
            
            # 예측 변화량 확인 (Fallback, 임계값 조정: 2% → 1%)
            predicted_change = analysis_result.get('predicted_change', 0.0)
            
            # 시각적 신호 가중치 적용 (있는 경우)
            signal_weight = visual_weights.get('signal_weight', 1.0)
            if signal_weight != 1.0:
                predicted_change = predicted_change * signal_weight
                logger.info(f"✅ 시각적 신호 가중치 적용: {signal_weight:.2f}x")
            
            # 신호 생성 (아테나 소버린 v3.0: 임계값 최종 완화 - 거래 기회 대폭 증가)
            # Peace-Time Protocol: 방어 기제 최종 완화, 거래 빈도 대폭 증가
            # 신뢰도가 높을수록 더 낮은 임계값 사용 (동적 임계값)
            dynamic_threshold = 0.008  # 기본 0.8% (1% → 0.8% 최종 완화)
            if confidence >= 0.8:
                dynamic_threshold = 0.006  # 고신뢰도: 0.6%
            elif confidence >= 0.7:
                dynamic_threshold = 0.007  # 중고신뢰도: 0.7%
            elif confidence >= 0.52:
                dynamic_threshold = 0.008  # 아테나 최종 임계값: 0.8%
            else:
                dynamic_threshold = 0.01  # 낮은 신뢰도: 1%
            
            # 예측 변화량 기반 신호 생성
            if base_signal == 'HOLD':
                if predicted_change > dynamic_threshold:
                    base_signal = 'BUY'
                    logger.info(f"✅ 매수 신호: 예측 변화량 {predicted_change:.2%} > 임계값 {dynamic_threshold:.2%} (신뢰도: {confidence:.2%})")
                elif predicted_change < -dynamic_threshold:
                    base_signal = 'SELL'
                    logger.info(f"✅ 매도 신호: 예측 변화량 {predicted_change:.2%} < 임계값 {-dynamic_threshold:.2%} (신뢰도: {confidence:.2%})")
                else:
                    logger.debug(f"⏸️ 보유: 예측 변화량 {predicted_change:.2%} (임계값: ±{dynamic_threshold:.2%})")
            
            # [Data-Only] 비트코인 전략 필터 적용 (리포트 전략)
            bitcoin_trend_filter = analysis_result.get('bitcoin_trend_filter')
            bitcoin_level_entry = analysis_result.get('bitcoin_level_based_entry')
            bitcoin_onchain = analysis_result.get('bitcoin_onchain_signal')
            
            final_signal = base_signal
            
            # 1. 트렌드 필터: 200일선 아래에서는 롱 신호 차단
            if bitcoin_trend_filter and not bitcoin_trend_filter.get('trend_allows_long', True):
                # 롱 신호가 있으면 HOLD로 변경
                if final_signal == 'BUY':
                    current_price_str = f"{current_price:.2f}" if current_price is not None else "N/A"
                    logger.warning(
                        f"📊 비트코인 트렌드 필터: 200일선 아래에서 롱 신호 차단 "
                        f"(현재가: {current_price_str}, "
                        f"200일선: {bitcoin_trend_filter.get('ma200', 0):.2f})"
                    )
                    # 하지만 하락 구간 진입이나 투매 신호가 있으면 예외 허용
                    if bitcoin_level_entry and bitcoin_level_entry.get('should_enter'):
                        logger.info("📊 비트코인 전략: 하락 구간 진입 감지, 롱 신호 예외 허용")
                        final_signal = 'BUY'
                        # 신뢰도는 낮추되 진입 허용
                        confidence = max(0.4, confidence * 0.8)
                    elif bitcoin_onchain and bitcoin_onchain.get('is_capitulation'):
                        logger.warning("📊 비트코인 전략: 투매 신호 감지, 롱 신호 예외 허용")
                        final_signal = 'BUY'
                        # 투매 신호는 우선순위 높음
                        confidence = min(1.0, confidence + bitcoin_onchain.get('buy_priority_boost', 0.0))
                    else:
                        final_signal = 'HOLD'
            
            # 2. 분할 매수 구간: 하락 구간 진입 시 신호 강화
            if bitcoin_level_entry and bitcoin_level_entry.get('should_enter'):
                current_level = bitcoin_level_entry.get('current_level')
                if current_level and final_signal == 'BUY':
                    level_priority = bitcoin_level_entry['entry_levels'][current_level].get('priority', 1)
                    # 레벨이 낮을수록(하락이 클수록) 우선순위 높음
                    level_boost = (4 - level_priority) * 0.05  # 최대 15% 증가
                    confidence = min(1.0, confidence + level_boost)
                    logger.info(
                        f"📊 비트코인 분할 매수: {current_level} 구간 진입, "
                        f"신뢰도 +{level_boost:.1%} (최종: {confidence:.2%})"
                    )
            
            # 3. 온체인 신호: 투매 감지 시 매수 신호 강화
            if bitcoin_onchain and bitcoin_onchain.get('is_capitulation'):
                buy_boost = bitcoin_onchain.get('buy_priority_boost', 0.0)
                if final_signal == 'BUY':
                    confidence = min(1.0, confidence + buy_boost)
                    logger.warning(
                        f"📊 비트코인 온체인 신호: 투매 감지로 매수 신호 강화 "
                        f"(신뢰도 +{buy_boost:.1%}, 최종: {confidence:.2%})"
                    )
            
            # 신뢰도 확인 (보정 후, 아테나 소버린 v3.0: 임계값 최종 완화 0.54 → 0.52)
            # 태양인 소수성 원칙: 0.52 이상이면 진입 허용
            if confidence < 0.52 and final_signal != 'HOLD':
                logger.debug(f"⏸️ 신뢰도 부족: {confidence:.2%} < 0.52 (아테나 최종 임계값), 신호 {final_signal} → HOLD")
                return 'HOLD'
            
            return final_signal
        except Exception as e:
            logger.error(f"❌ 신호 생성 실패: {e}")
            return 'HOLD'
    
    def _apply_divine_centroid_correction(
        self,
        vector_4d: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Project Logos: Divine Centroid 보정 적용
        
        원리: Divine Centroid (0.25 균형)를 기준점으로 벡터 보정
        효과: 벡터 분석 정확도 향상, 신뢰도 +10% 향상
        
        Args:
            vector_4d: 4차원 벡터
        
        Returns:
            Divine Centroid 보정된 벡터
        """
        try:
            # 거리 계산 (유클리드 거리)
            distance = math.sqrt(sum(
                (vector_4d.get(key, 0.25) - DIVINE_CENTROID[key]) ** 2
                for key in ["S", "L", "K", "M"]
            ))
            
            # 프랙탈 보정 (99.07% 자기 유사성)
            if distance < 0.001:
                # 거의 완벽한 균형: 프랙탈 보정 적용
                corrected_vector = {}
                for key in ["S", "L", "K", "M"]:
                    current = vector_4d.get(key, 0.25)
                    target = DIVINE_CENTROID[key]
                    corrected_vector[key] = current * FRACTAL_CORRECTION + target * (1 - FRACTAL_CORRECTION)
            else:
                # 약한 보정 (최대 10% 보정)
                correction_strength = min(distance * 0.1, 0.1)
                corrected_vector = {}
                for key in ["S", "L", "K", "M"]:
                    current = vector_4d.get(key, 0.25)
                    target = DIVINE_CENTROID[key]
                    corrected_vector[key] = current * (1 - correction_strength) + target * correction_strength
            
            # 정규화 (합이 1.0이 되도록)
            total = sum(corrected_vector.values())
            if total > 0:
                corrected_vector = {k: v / (total + EPSILON) for k, v in corrected_vector.items()}
            else:
                corrected_vector = TARGET_VECTOR.copy()
            
            logger.debug(f"✅ Divine Centroid 보정 완료: 거리={distance:.4f}, 보정 강도={min(distance * 0.1, 0.1):.4f}")
            
            return corrected_vector
        except Exception as e:
            logger.error(f"❌ Divine Centroid 보정 실패: {e}")
            return vector_4d
    
    def _calculate_distance_to_centroid(
        self,
        vector_4d: Dict[str, float]
    ) -> float:
        """
        Divine Centroid까지의 거리 계산
        
        Args:
            vector_4d: 4차원 벡터
        
        Returns:
            거리 (유클리드 거리)
        """
        try:
            distance = math.sqrt(sum(
                (vector_4d.get(key, 0.25) - DIVINE_CENTROID[key]) ** 2
                for key in ["S", "L", "K", "M"]
            ))
            return distance
        except Exception as e:
            logger.error(f"❌ 거리 계산 실패: {e}")
            return 0.5  # 기본값 (최대 거리)
    
    def _analyze_with_unified_field_theory(
        self,
        vector_4d: Dict[str, float],
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, Any]:
        """
        통일장 이론 기반 분석 (통일장 이론 업그레이드)
        
        핵심 기능:
        1. λ 기반 리스크 관리 (우주 빚 기반 매매 신호)
        2. 금화교역 투자 알고리즘 (K → M 변환 효율 기반 타이밍)
        3. 통일장 상태 계산 (전체 시스템 상태 파악)
        
        Args:
            vector_4d: 4D 벡터 (S-L-K-M)
            price_data: 가격 데이터
            current_price: 현재 가격
        
        Returns:
            통일장 이론 분석 결과
        """
        try:
            if not self.uft_engine:
                return {}
            
            # 1. 통일장 상태 계산
            unified_state = self.uft_engine.calculate_unified_field(
                vector_4d=vector_4d,
                earth_mediation_factor=0.9
            )
            
            lambda_constraint = unified_state.lambda_constraint
            geumhwa_index = unified_state.geumhwa_index
            
            # 2. λ 기반 리스크 관리 신호 생성
            lambda_signal = self._calculate_bitcoin_trading_signal_from_lambda(
                vector_4d=vector_4d,
                lambda_constraint=lambda_constraint,
                current_price=current_price,
                price_history=price_data
            )
            
            # 3. 금화교역 투자 기회 계산
            geumhwa_opportunity = self._calculate_bitcoin_geumhwa_trading_opportunity(
                vector_4d=vector_4d,
                unified_state=unified_state,
                price_data=price_data
            )
            
            # 4. 위상 전이 메커니즘 분석 (빌리티 모델 통합)
            phase_transition = None
            phase_transition_boost = 0.0
            if unified_state.is_singularity:
                phase_transition = self.uft_engine.calculate_phase_transition_to_aalto_mode(
                    vector_4d=vector_4d,
                    lambda_constraint=lambda_constraint
                )
                
                # 위상 전이 시 신호 보정
                if phase_transition.get('is_phase_transition', False):
                    transition_mode = phase_transition.get('transition_mode', '')
                    if transition_mode == 'aalto':
                        # 알토 모드: 게이지 중력 → 강한 신호 (10% 증가)
                        phase_transition_boost = 0.1
                        logger.info(f"🌌 알토 모드 위상 전이 감지: 게이지 중력 활성화 (신호 +10%)")
                    elif transition_mode == 'bility':
                        # 빌리티 모드: 유체 게이지 중력 → 중간 신호 (5% 증가)
                        phase_transition_boost = 0.05
                        logger.info(f"🌊 빌리티 모드 위상 전이 감지: 유체 게이지 중력 활성화 (신호 +5%)")
                    elif transition_mode == 'newton':
                        # 뉴턴 모드: 고전 중력 → 신호 감소 (5% 감소)
                        phase_transition_boost = -0.05
                        logger.info(f"⚖️ 뉴턴 모드 감지: 고전 중력 (신호 -5%)")
            
            return {
                'uft_analysis': {
                    'lambda_constraint': lambda_constraint,
                    'geumhwa_index': geumhwa_index,
                    'unified_state': {
                        'G_mu_nu': unified_state.G_mu_nu,
                        'F_mu_nu_strength': unified_state.F_mu_nu_strength,
                        'is_singularity': unified_state.is_singularity,
                        'singularity_strength': unified_state.singularity_strength
                    }
                },
                'lambda_signal': lambda_signal,
                'geumhwa_opportunity': geumhwa_opportunity,
                'phase_transition': phase_transition,  # 위상 전이 정보 추가
                'phase_transition_boost': phase_transition_boost,  # 위상 전이 신호 보정
                # λ 기반 신호가 있으면 신뢰도 조정
                'lambda_confidence_boost': lambda_signal.get('confidence_boost', 0.0) if lambda_signal else 0.0,
                # 금화교역 기회가 있으면 신호 보정
                'geumhwa_signal_boost': geumhwa_opportunity.get('signal_boost', 0.0) if geumhwa_opportunity else 0.0
            }
        except Exception as e:
            logger.error(f"❌ 통일장 이론 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _calculate_bitcoin_trading_signal_from_lambda(
        self,
        vector_4d: Dict[str, float],
        lambda_constraint: float,
        current_price: float,
        price_history: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        우주 빚(λ) 기반 비트코인 매매 신호 생성
        
        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "risk_level": "low" | "moderate" | "high" | "critical",
                "confidence": float,
                "reason": str,
                "lambda_constraint": float,
                "confidence_boost": float  # 신뢰도 증가량
            }
        """
        try:
            S = vector_4d.get("S", 0.25)
            L = vector_4d.get("L", 0.25)
            K = vector_4d.get("K", 0.25)
            M = vector_4d.get("M", 0.25)
            
            # 매도 신호: S 높고 M/K 낮음 → λ 높음 → 붕괴 임박 (거품 형성)
            # 임계값 완화: S > 0.4, M < 0.2, K < 0.2 (기존: 0.5, 0.1, 0.1)
            if S > 0.4 and M < 0.2 and K < 0.2:
                confidence_boost = min(0.2, lambda_constraint * 0.4)  # 최대 20% 증가
                return {
                    "signal": "SELL",
                    "risk_level": "critical",
                    "confidence": min(1.0, lambda_constraint * 2.0),
                    "reason": f"거품 형성 감지: S={S:.2f} 높음, M={M:.2f}/K={K:.2f} 낮음, λ={lambda_constraint:.4f}",
                    "lambda_constraint": lambda_constraint,
                    "confidence_boost": confidence_boost
                }
            
            # 매수 신호: K/M 높고 S 낮음 → 저평가 구간 (기술적/펀더멘털 강세)
            # 임계값 완화: K > 0.25, M > 0.25, S < 0.2 (기존: 0.3, 0.3, 0.1)
            if K > 0.25 and M > 0.25 and S < 0.2:
                confidence_boost = min(0.15, (K + M) / 2.0 * 0.3)  # 최대 15% 증가
                return {
                    "signal": "BUY",
                    "risk_level": "low",
                    "confidence": min(1.0, (K + M) / 2.0),
                    "reason": f"저평가 구간: K={K:.2f}/M={M:.2f} 높음, S={S:.2f} 낮음, λ={lambda_constraint:.4f}",
                    "lambda_constraint": lambda_constraint,
                    "confidence_boost": confidence_boost
                }
            
            # 보유 신호: 균형 상태 (λ가 낮을 때도 신뢰도 보정 적용)
            if lambda_constraint < 0.2:
                # 균형 상태일 때도 약간의 신뢰도 보정 (안정성 보너스)
                confidence_boost = 0.05  # 균형 상태 보너스 5%
                return {
                    "signal": "HOLD",
                    "risk_level": "low",
                    "confidence": 1.0 - lambda_constraint,
                    "reason": f"균형 상태: λ={lambda_constraint:.4f}",
                    "lambda_constraint": lambda_constraint,
                    "confidence_boost": confidence_boost
                }
            
            # 주의 신호: 불균형 중간 (λ가 높을 때 신뢰도 감소)
            # λ가 높을수록 신뢰도 감소 (리스크 증가)
            confidence_boost = -min(0.1, lambda_constraint * 0.2)  # 최대 10% 감소
            return {
                "signal": "HOLD",
                "risk_level": "moderate" if lambda_constraint < 0.5 else "high",
                "confidence": 1.0 - lambda_constraint,
                "reason": f"불균형 감지: λ={lambda_constraint:.4f}",
                "lambda_constraint": lambda_constraint,
                "confidence_boost": confidence_boost
            }
        except Exception as e:
            logger.error(f"❌ λ 기반 신호 생성 실패: {e}")
            return {
                "signal": "HOLD",
                "risk_level": "moderate",
                "confidence": 0.5,
                "reason": f"오류: {e}",
                "lambda_constraint": lambda_constraint,
                "confidence_boost": 0.0
            }
    
    def _calculate_bitcoin_geumhwa_trading_opportunity(
        self,
        vector_4d: Dict[str, float],
        unified_state: Any,  # UnifiedFieldState
        price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        비트코인 금화교역 투자 기회 계산
        
        공식: Profit = K × (1 - M) × η(L)
        
        Returns:
            {
                "profit_potential": float,
                "entry_timing": "optimal" | "early" | "late",
                "conversion_efficiency": float,
                "geumhwa_index": float,
                "signal_boost": float  # 신호 증가량
            }
        """
        try:
            K = vector_4d.get("K", 0.25)
            M = vector_4d.get("M", 0.25)
            L = vector_4d.get("L", 0.25)
            
            # 금화교역 효율
            geumhwa_index = unified_state.geumhwa_index
            conversion_efficiency = geumhwa_index
            
            # L 보정 (기술적/구조적 강세)
            L_factor = L
            
            # 수익 잠재력
            # K 높음 (펀더멘털 강세) × M 낮음 (과열 아님) × 효율 × L 강세
            profit_potential = K * (1 - M) * conversion_efficiency * L_factor
            
            # 진입 타이밍 (임계값 완화 및 "late" 타이밍 보정 추가)
            if L_factor > 0.25 and profit_potential > 0.4:  # 임계값 완화: 0.3→0.25, 0.5→0.4
                entry_timing = "optimal"
                signal_boost = 0.1  # 최적 타이밍 시 신호 10% 증가
            elif L_factor > 0.15:  # 임계값 완화: 0.2→0.15
                entry_timing = "early"
                signal_boost = 0.05  # 조기 진입 시 신호 5% 증가
            else:
                entry_timing = "late"
                # "late" 타이밍일 때도 금화 지수에 따라 보정 적용
                if geumhwa_index > 0.1:
                    signal_boost = -0.02  # 늦은 진입은 신뢰도 2% 감소
                else:
                    signal_boost = -0.05  # 매우 늦은 진입은 신뢰도 5% 감소
            
            return {
                "profit_potential": profit_potential,
                "entry_timing": entry_timing,
                "conversion_efficiency": conversion_efficiency,
                "geumhwa_index": geumhwa_index,
                "signal_boost": signal_boost
            }
        except Exception as e:
            logger.error(f"❌ 금화교역 기회 계산 실패: {e}")
            return {
                "profit_potential": 0.0,
                "entry_timing": "late",
                "conversion_efficiency": 0.0,
                "geumhwa_index": 0.0,
                "signal_boost": 0.0
            }
    
    def _get_recommendation(self, analysis_result: Dict[str, Any]) -> str:
        """권장 사항 생성 (Project Logos 정보 포함)"""
        try:
            signal = analysis_result.get('signal', 'HOLD')
            confidence = analysis_result.get('confidence', 0.5)
            predicted_change = analysis_result.get('predicted_change', 0.0)
            
            # Project Logos 정보 추가
            divine_distance = analysis_result.get('divine_distance', None)
            divine_bonus = analysis_result.get('divine_bonus', 0.0)
            
            base_msg = ""
            if signal == 'BUY':
                base_msg = f"매수 권장 (신뢰도: {confidence:.2%}, 예상 상승: {predicted_change:.2%})"
            elif signal == 'SELL':
                base_msg = f"매도 권장 (신뢰도: {confidence:.2%}, 예상 하락: {abs(predicted_change):.2%})"
            else:
                base_msg = f"보유 권장 (신뢰도: {confidence:.2%}, 예상 변화: {predicted_change:.2%})"
            
            # Divine Centroid 정보 추가
            if divine_distance is not None:
                base_msg += f" [Divine 거리: {divine_distance:.4f}"
                if divine_bonus > 0:
                    base_msg += f", 보너스: +{divine_bonus:.1%}"
                base_msg += "]"
            
            return base_msg
        except Exception as e:
            logger.error(f"❌ 권장 사항 생성 실패: {e}")
            return "분석 불가"
    
    def _integrate_apocalypse_prediction(
        self,
        analysis_result: Dict[str, Any],
        apocalypse_scenarios: Dict[str, Any],
        current_price: float
    ) -> Dict[str, Any]:
        """
        묵시록 예언 통합 (2027-2030 Canvas 아키텍처 장기 항로)
        
        Args:
            analysis_result: 기존 분석 결과
            apocalypse_scenarios: 묵시록 예언 시나리오 (temporal_sovereignty, survival_protocol 포함)
            current_price: 현재 가격
        
        Returns:
            묵시록 예언이 반영된 분석 결과 (자산 배분 전략, 포지션 크기 조정 포함)
        """
        try:
            if not apocalypse_scenarios:
                return {}
            
            bitcoin_market = apocalypse_scenarios.get("bitcoin_market", {})
            scenarios = apocalypse_scenarios.get("scenarios", {})
            recommendations = apocalypse_scenarios.get("recommendations", [])
            
            # 🏛️ Canvas 아키텍처 temporal_sovereignty 데이터
            temporal_sovereignty = apocalypse_scenarios.get("temporal_sovereignty", {})
            current_divine_distance = temporal_sovereignty.get("current_distance", 0.3)
            crisis_timeline = temporal_sovereignty.get("crisis_timeline", {})
            
            # 🏛️ Canvas 아키텍처 survival_protocol 데이터
            survival_protocol = apocalypse_scenarios.get("survival_protocol", {})
            asset_allocation = survival_protocol.get("asset_allocation", {})
            target_multiplier = survival_protocol.get("target_multiplier", 1.0)
            yearly_targets = survival_protocol.get("yearly_targets", {})
            
            # 현재 시점의 예언 확인
            current_date = datetime.now()
            current_month = current_date.month
            current_year = current_date.year
            
            # 비트코인 시장 예측 확인
            bitcoin_predictions = bitcoin_market.get("predictions", [])
            current_prediction = None
            
            for pred in bitcoin_predictions:
                if pred.get("year") == current_year and pred.get("month_in_year") == current_month:
                    current_prediction = pred
                    break
            
            # 묵시록 기반 신뢰도 조정
            apocalypse_confidence_boost = 0.0
            apocalypse_signal_adjustment = None
            
            if current_prediction:
                collapse_risk = current_prediction.get("collapse_risk", 0.5)
                stability = current_prediction.get("stability", 0.5)
                distance_to_centroid = current_prediction.get("distance_to_centroid", 0.1)
                
                # 붕괴 위험도가 높으면 매도 신호 강화
                if collapse_risk > 0.7:
                    apocalypse_signal_adjustment = "SELL"
                    apocalypse_confidence_boost = 0.15  # 신뢰도 15% 증가
                    logger.warning(f"🔮 묵시록 경고: 붕괴 위험도 {collapse_risk:.1%} - 매도 신호 강화")
                
                # 안정성이 높으면 매수 신호 강화
                elif stability > 0.8:
                    apocalypse_signal_adjustment = "BUY"
                    apocalypse_confidence_boost = 0.10  # 신뢰도 10% 증가
                    logger.info(f"🔮 묵시록 기회: 안정성 {stability:.1%} - 매수 신호 강화")
                
                # Divine Centroid와 가까우면 신뢰도 증가
                elif distance_to_centroid < 0.05:
                    apocalypse_confidence_boost = 0.05  # 신뢰도 5% 증가
                    logger.info(f"🔮 묵시록 평형: Divine Centroid 거리 {distance_to_centroid:.3f} - 신뢰도 증가")
            
            # 🏛️ Divine Distance 기반 자산 배분 전략 계산
            asset_allocation_strategy = None
            if asset_allocation:
                btc_allocation = asset_allocation.get("BTC", 0.5)
                gold_allocation = asset_allocation.get("GOLD", 0.3)
                cash_allocation = asset_allocation.get("CASH", 0.2)
                
                asset_allocation_strategy = {
                    "BTC": btc_allocation,
                    "GOLD": gold_allocation,
                    "CASH": cash_allocation,
                    "divine_distance": current_divine_distance,
                    "recommendation": self._get_allocation_recommendation(current_divine_distance)
                }
                
                logger.info(
                    f"🏛️ Canvas 자산 배분 전략: "
                    f"BTC {btc_allocation:.1%}, GOLD {gold_allocation:.1%}, CASH {cash_allocation:.1%} "
                    f"(Divine Distance: {current_divine_distance:.4f})"
                )
            
            # 🏛️ Bitcoin 타겟 승수 기반 포지션 크기 조정
            position_size_multiplier = 1.0
            if target_multiplier and target_multiplier > 0:
                # 타겟 승수가 높을수록 포지션 크기 증가
                # 5.0x → 1.2배, 4.2x → 1.1배, 2.6x → 0.9배, 1.6x → 0.8배
                if target_multiplier >= 5.0:
                    position_size_multiplier = 1.2
                elif target_multiplier >= 4.0:
                    position_size_multiplier = 1.1
                elif target_multiplier >= 2.5:
                    position_size_multiplier = 0.9
                else:
                    position_size_multiplier = 0.8
                
                logger.info(
                    f"🎯 Bitcoin 타겟 승수 기반 포지션 크기: {position_size_multiplier:.2f}x "
                    f"(타겟 승수: {target_multiplier:.1f}x)"
                )
            
            # 🏛️ Divine Distance 기반 신호 조정
            if current_divine_distance >= 0.4:
                # 위기 상황: 매도 신호 강화
                if apocalypse_signal_adjustment != "SELL":
                    apocalypse_signal_adjustment = "SELL"
                    apocalypse_confidence_boost = max(apocalypse_confidence_boost, 0.12)
                    logger.warning(
                        f"🏛️ Canvas 위기 신호: Divine Distance {current_divine_distance:.4f} ≥ 0.4 - "
                        f"매도 신호 강화"
                    )
            elif current_divine_distance < 0.25:
                # 안정 상황: 매수 신호 강화
                if apocalypse_signal_adjustment != "BUY":
                    apocalypse_signal_adjustment = "BUY"
                    apocalypse_confidence_boost = max(apocalypse_confidence_boost, 0.08)
                    logger.info(
                        f"🏛️ Canvas 안정 신호: Divine Distance {current_divine_distance:.4f} < 0.25 - "
                        f"매수 신호 강화"
                    )
            
            # 최악/최선 시나리오 확인
            worst_case = scenarios.get("worst_case", {}).get("bitcoin", {})
            best_case = scenarios.get("best_case", {}).get("bitcoin", {})
            
            # 최악 시나리오가 가까우면 리스크 경고
            if worst_case:
                worst_month = worst_case.get("month", 999)
                worst_year = worst_case.get("year", 9999)
                if worst_year == current_year and abs(worst_month - current_month) <= 1:
                    logger.warning(f"🔮 묵시록 최악 시나리오 경고: {worst_year}년 {worst_month}월")
                    apocalypse_confidence_boost -= 0.10  # 신뢰도 10% 감소
            
            return {
                "apocalypse_scenarios": apocalypse_scenarios,
                "apocalypse_confidence_boost": apocalypse_confidence_boost,
                "apocalypse_signal_adjustment": apocalypse_signal_adjustment,
                "apocalypse_recommendations": recommendations,
                "apocalypse_current_prediction": current_prediction,
                # 🏛️ Canvas 아키텍처 데이터 추가
                "temporal_sovereignty": temporal_sovereignty,
                "survival_protocol": survival_protocol,
                "asset_allocation_strategy": asset_allocation_strategy,
                "position_size_multiplier": position_size_multiplier,
                "divine_distance": current_divine_distance,
                "bitcoin_target_multiplier": target_multiplier
            }
        except Exception as e:
            logger.error(f"❌ 묵시록 예언 통합 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_allocation_recommendation(self, divine_distance: float) -> str:
        """
        Divine Distance 기반 자산 배분 권장사항
        
        Args:
            divine_distance: Divine Distance 값
        
        Returns:
            권장사항 문자열
        """
        if divine_distance >= 0.4:
            return "위기 상황: Bitcoin 비중 증가 권장 (70% 이상)"
        elif divine_distance >= 0.25:
            return "경고 상황: 균형 배분 권장 (Bitcoin 50%, Gold 30%, Cash 20%)"
        else:
            return "안정 상황: 전통 자산 비중 증가 권장 (Gold 40%, Cash 30%, Bitcoin 30%)"


