#!/usr/bin/env python3
"""
주식 특화 4D 지능 팩 (Stock 4D Intelligence Pack)

대화 기능 없이 순수 자동매매에 특화된 주식 분석 엔진
- L(Logic) + M(Material) 중심: 기술적 분석 + 실제 주가
- 주식 시장 특화 지식 통합
- 자동매매 엔진에 직접 통합
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import logging

# ProphecyStack (KOSPI 통일장 레짐) 선택적 import
try:
    from tools.prophecy.prophecy_stack import get_prophecy_stack
    PROPHECY_STACK_AVAILABLE = True
except ImportError:
    get_prophecy_stack = None  # type: ignore[misc, assignment]
    PROPHECY_STACK_AVAILABLE = False

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

# 이론 모듈 import
try:
    from tools.core.ICDUnifiedModel import ICDUnifiedModel
    from tools.core.ICDStockAnalysisEngine import ICDStockAnalysisEngine
    from tools.core.MKM12DynamicsPredictor import MKM12DynamicsPredictor
    THEORY_AVAILABLE = True
except ImportError as e:
    THEORY_AVAILABLE = False
    logging.warning(f"⚠️ 이론 모듈 import 실패: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stock4DIntelligencePack:
    """
    주식 특화 4D 지능 팩
    
    핵심 특징:
    - 대화 기능 없음 (순수 자동매매 전용)
    - L(Logic) + M(Material) 중심 가중치
    - 주식 시장 특화 지식 통합
    - 자동매매 엔진에 직접 통합
    """
    
    # 주식 특화 4D 벡터 가중치 (L + M 중심)
    STOCK_4D_WEIGHTS = {
        'S': 0.15,  # Spirit (심리): 15% (주식은 기술적 분석 중심)
        'L': 0.40,  # Logic (논리): 40% (기술적 분석 강화)
        'K': 0.20,  # Knowledge (지식): 20% (재무 지표, 뉴스)
        'M': 0.25   # Material (물질): 25% (실제 주가, 거래량)
    }
    
    def __init__(
        self,
        symbol: str = "005930",  # 삼성전자 (기본값)
        use_icd: bool = True,
        use_mkm12: bool = True
    ):
        """
        Args:
            symbol: 종목 코드 (기본값: 005930 = 삼성전자)
            use_icd: ICD 통합 모델 사용 여부
            use_mkm12: MKM12 동역학 예측 사용 여부
        """
        self.symbol = symbol
        self.use_icd = use_icd and THEORY_AVAILABLE
        self.use_mkm12 = use_mkm12 and THEORY_AVAILABLE
        
        # 이론 모듈 초기화
        self.icd_model = None
        self.icd_engine = None
        self.mkm12_predictor = None
        self._myeongri_controller = None  # G_환경 e (명리 기반, 지연 로딩)
        self._myeongri_failed = False  # 한 번 실패 시 재시도 안 함 (튕김 방지)
        
        if self.use_icd:
            try:
                self.icd_model = ICDUnifiedModel()
                self.icd_engine = ICDStockAnalysisEngine()
                logger.info("✅ ICD 통합 모델 초기화 완료 (주식 특화)")
            except Exception as e:
                logger.warning(f"⚠️ ICD 통합 모델 초기화 실패: {e}")
                self.use_icd = False
        
        if self.use_mkm12:
            try:
                self.mkm12_predictor = MKM12DynamicsPredictor()
                logger.info("✅ MKM12 동역학 예측 모델 초기화 완료 (주식 특화)")
            except Exception as e:
                logger.warning(f"⚠️ MKM12 동역학 예측 모델 초기화 실패: {e}")
                self.use_mkm12 = False
        
        # G_환경 e: 명리 기반 — __init__에서 생성 제거, 최초 사용 시 _get_env_factor_and_type()에서 지연 로딩 (튕김 방지)
    
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
    
    def analyze_stock_market(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        volume: float = 0.0,
        market_cap: float = 0.0,
        per: float = 0.0,
        pbr: float = 0.0
    ) -> Dict[str, Any]:
        """
        주식 시장 분석 (4D 지능 팩)
        
        Args:
            price_data: 가격 데이터 (OHLCV)
            current_price: 현재 주가
            volume: 거래량
            market_cap: 시가총액
            per: PER (주가수익비율)
            pbr: PBR (주가순자산비율)
        
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
            'recommendation': 'HOLD',
            'stock_specific': {
                'technical_score': 0.5,
                'fundamental_score': 0.5,
                'momentum_score': 0.5
            }
        }
        
        try:
            # 1. 주식 특화 4D 벡터 계산 (L + M 중심)
            vector_4d = self._calculate_stock_4d_vector(
                price_data, current_price, volume, market_cap, per, pbr
            )
            result['vector_4d'] = vector_4d
            
            # 2. ICD 통합 모델 분석 (주식 도메인)
            if self.use_icd and self.icd_model:
                icd_result = self._analyze_with_icd_stock(
                    price_data, current_price, per, pbr
                )
                result.update(icd_result)
            
            # 3. MKM12 동역학 예측 (주식 특화 가중치 적용)
            if self.use_mkm12 and self.mkm12_predictor:
                mkm12_result = self._analyze_with_mkm12_stock(
                    vector_4d, price_data, current_price
                )
                result.update(mkm12_result)
            
            # 4. 주식 특화 기술적 분석
            technical_analysis = self._technical_analysis_stock(
                price_data, current_price, volume
            )
            result['stock_specific'].update(technical_analysis)
            
            # 5. 최종 신호 생성 (주식 특화 로직)
            result['signal'] = self._generate_stock_signal(result)
            result['recommendation'] = self._get_stock_recommendation(result)

            # 6. KOSPI 통일장 레짐 반영 (ProphecyStack)
            if PROPHECY_STACK_AVAILABLE and get_prophecy_stack is not None:
                try:
                    now = datetime.now()
                    stack = get_prophecy_stack()
                    kospi_summary = stack.get_kospi_unified_field_summary(
                        year=now.year, month=now.month, domain_hint="stock_kospi"
                    )
                    if kospi_summary is not None:
                        regime = getattr(kospi_summary, "regime_label", None) or getattr(
                            kospi_summary, "regime", None
                        )
                        lam = getattr(kospi_summary, "lambda_constraint", None)
                        result["kospi_regime"] = regime
                        result["kospi_lambda"] = lam
                        if regime == "위험":
                            result["confidence"] = (result.get("confidence") or 0.5) * 0.5
                            if result.get("signal") == "BUY":
                                result["signal"] = "HOLD"
                                result["recommendation"] = "HOLD"
                        elif regime == "주의":
                            result["confidence"] = (result.get("confidence") or 0.5) * 0.8
                except Exception as ke:
                    logger.debug("KOSPI 통일장 레짐 조회 생략: %s", ke)
            
        except Exception as e:
            logger.error(f"❌ 주식 시장 분석 실패: {e}")
        
        return result
    
    def _calculate_stock_4d_vector(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        volume: float = 0.0,
        market_cap: float = 0.0,
        per: float = 0.0,
        pbr: float = 0.0
    ) -> Dict[str, float]:
        """
        주식 특화 4D 벡터 계산 (L + M 중심)
        
        주식 시장 특화:
        - S(Spirit): 시장 심리 (15%)
        - L(Logic): 기술적 분석 강도 (40%)
        - K(Knowledge): 재무 지표, 뉴스 (20%)
        - M(Material): 실제 주가, 거래량 (25%)
        """
        try:
            # S (Spirit): 시장 심리 (15%)
            # 가격 모멘텀 기반
            momentum = (current_price - price_data['close'].iloc[-5:].mean()) / price_data['close'].iloc[-5:].mean() if len(price_data) >= 5 else 0.0
            S = max(0.0, min(1.0, 0.5 + momentum * 10)) * self.STOCK_4D_WEIGHTS['S'] / 0.25
            
            # L (Logic): 기술적 분석 강도 (40%)
            # 추세 강도 + 패턴 인식
            trend_strength = abs(price_data['close'].pct_change().mean()) if len(price_data) > 1 else 0.0
            rsi = self._calculate_rsi(price_data) if len(price_data) >= 14 else 50.0
            macd_signal = self._calculate_macd_signal(price_data) if len(price_data) >= 26 else 0.0
            
            # 기술적 분석 종합 점수
            technical_score = (trend_strength * 100 + abs(rsi - 50) / 50 + abs(macd_signal)) / 3
            L = max(0.0, min(1.0, technical_score)) * self.STOCK_4D_WEIGHTS['L'] / 0.25
            
            # K (Knowledge): 재무 지표, 뉴스 (20%)
            # PER, PBR 기반 밸류에이션
            per_score = 0.5
            if per > 0:
                # PER이 낮을수록 (10 이하) 좋음
                per_score = max(0.0, min(1.0, 1.0 - (per - 10) / 50)) if per <= 10 else max(0.0, min(1.0, 1.0 - (per - 10) / 100))
            
            pbr_score = 0.5
            if pbr > 0:
                # PBR이 낮을수록 (1 이하) 좋음
                pbr_score = max(0.0, min(1.0, 1.0 - (pbr - 1) / 5))
            
            fundamental_score = (per_score + pbr_score) / 2
            K = fundamental_score * self.STOCK_4D_WEIGHTS['K'] / 0.25
            
            # M (Material): 실제 주가, 거래량 (25%)
            # 거래량 + 가격 안정성
            volume_ratio = volume / price_data['volume'].mean() if 'volume' in price_data.columns and len(price_data) > 0 and price_data['volume'].mean() > 0 else 1.0
            price_stability = 1.0 - (price_data['close'].std() / price_data['close'].mean()) if len(price_data) > 0 and price_data['close'].mean() > 0 else 0.5
            
            material_score = (volume_ratio / 2.0 + price_stability) / 2
            M = max(0.0, min(1.0, material_score)) * self.STOCK_4D_WEIGHTS['M'] / 0.25
            
            # 정규화 (합이 1.0이 되도록)
            total = S + L + K + M
            if total > 0:
                S /= total
                L /= total
                K /= total
                M /= total
            else:
                S = self.STOCK_4D_WEIGHTS['S']
                L = self.STOCK_4D_WEIGHTS['L']
                K = self.STOCK_4D_WEIGHTS['K']
                M = self.STOCK_4D_WEIGHTS['M']
            
            logger.info(f"📊 주식 특화 4D 벡터: S={S:.4f}, L={L:.4f}, K={K:.4f}, M={M:.4f}")
            
            return {'S': S, 'L': L, 'K': K, 'M': M}
            
        except Exception as e:
            logger.error(f"❌ 주식 특화 4D 벡터 계산 실패: {e}")
            return {
                'S': self.STOCK_4D_WEIGHTS['S'],
                'L': self.STOCK_4D_WEIGHTS['L'],
                'K': self.STOCK_4D_WEIGHTS['K'],
                'M': self.STOCK_4D_WEIGHTS['M']
            }
    
    def _calculate_rsi(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """RSI (Relative Strength Index) 계산"""
        try:
            if len(price_data) < period + 1:
                return 50.0
            
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs != 0 else 50.0
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        except Exception as e:
            logger.warning(f"⚠️ RSI 계산 실패: {e}")
            return 50.0
    
    def _calculate_macd_signal(self, price_data: pd.DataFrame) -> float:
        """MACD 신호 계산"""
        try:
            if len(price_data) < 26:
                return 0.0
            
            ema12 = price_data['close'].ewm(span=12, adjust=False).mean()
            ema26 = price_data['close'].ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            
            macd_signal = (macd.iloc[-1] - signal.iloc[-1]) / price_data['close'].iloc[-1] if price_data['close'].iloc[-1] > 0 else 0.0
            
            return macd_signal
        except Exception as e:
            logger.warning(f"⚠️ MACD 계산 실패: {e}")
            return 0.0
    
    def _analyze_with_icd_stock(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        per: float = 0.0,
        pbr: float = 0.0
    ) -> Dict[str, Any]:
        """ICD 통합 모델 분석 (주식 도메인)"""
        try:
            if not self.icd_model:
                return {
                    'dcv': 0.5,
                    'lambda': 0.5,
                    'pathology_level': 'SL'
                }
            
            # 주식 특화 벡터 변환
            price_vector = self._price_to_vector_stock(price_data, current_price, per, pbr)
            
            # ICD 분석 (주식 도메인)
            if hasattr(self.icd_model, 'analyze'):
                icd_result = self.icd_model.analyze(
                    pd_vector=price_vector['pd'],
                    sd_vector=price_vector['sd'],
                    domain='stock'  # 주식 도메인
                )
            elif hasattr(self.icd_engine, 'analyze'):
                icd_result = self.icd_engine.analyze(
                    price_data=price_data,
                    current_price=current_price
                )
            else:
                return {
                    'dcv': 0.5,
                    'lambda': 0.5,
                    'pathology_level': 'SL'
                }
            
            return {
                'dcv': icd_result.get('dcv', 0.5) if isinstance(icd_result, dict) else 0.5,
                'lambda': icd_result.get('lambda', 0.5) if isinstance(icd_result, dict) else 0.5,
                'pathology_level': icd_result.get('pathology_level', 'SL') if isinstance(icd_result, dict) else 'SL'
            }
        except Exception as e:
            logger.error(f"❌ ICD 주식 분석 실패: {e}")
            return {
                'dcv': 0.5,
                'lambda': 0.5,
                'pathology_level': 'SL'
            }
    
    def _analyze_with_mkm12_stock(
        self,
        vector_4d: Dict[str, float],
        price_data: pd.DataFrame,
        current_price: float
    ) -> Dict[str, Any]:
        """MKM12 동역학 예측 (주식 특화 가중치 적용)"""
        try:
            if not self.mkm12_predictor:
                return {}
            
            # MKM12 동역학 예측 (G_환경 e: 명리 기반, 지연 로딩)
            env_factor, env_type = self._get_env_factor_and_type()
            if hasattr(self.mkm12_predictor, 'predict_dynamics'):
                prediction = self.mkm12_predictor.predict_dynamics(
                    current_state=vector_4d,
                    time_horizon=5,  # 5단계 미래 예측
                    environment_factor=env_factor,
                    environment_type=env_type,
                    intervention_factor=0.0
                )
                
                predicted_states = prediction.get('predicted_states', [])
                final_predicted_state = predicted_states[-1] if predicted_states else vector_4d
            else:
                prediction = self.mkm12_predictor.predict(
                    current_state=vector_4d,
                    time_horizon=1
                )
                final_predicted_state = prediction.get('predicted_state', vector_4d)
            
            # 예측 변화량 계산 (주식 특화)
            predicted_change = self._calculate_predicted_change_stock(
                vector_4d,
                final_predicted_state,
                current_price
            )
            
            # 동적 신뢰도 계산
            confidence = self._calculate_dynamic_confidence_stock(
                vector_4d,
                final_predicted_state
            )
            
            return {
                'predicted_state': final_predicted_state,
                'predicted_change': predicted_change,
                'pattern_type': prediction.get('pattern_type', None) if isinstance(prediction, dict) else None,
                'confidence': confidence
            }
        except Exception as e:
            logger.error(f"❌ MKM12 주식 분석 실패: {e}")
            return {}
    
    def _calculate_predicted_change_stock(
        self,
        current_state: Dict[str, float],
        predicted_state: Dict[str, float],
        current_price: float
    ) -> float:
        """예측 변화량 계산 (주식 특화)"""
        try:
            # L과 M 차원에 더 높은 가중치 (주식 특화)
            L_change = predicted_state.get("L", 0.25) - current_state.get("L", 0.25)
            M_change = predicted_state.get("M", 0.25) - current_state.get("M", 0.25)
            S_change = predicted_state.get("S", 0.25) - current_state.get("S", 0.25)
            K_change = predicted_state.get("K", 0.25) - current_state.get("K", 0.25)
            
            # 주식 특화 가중 평균 (L + M 중심)
            weighted_change = (
                L_change * 0.5 +  # Logic (기술적 분석) 50%
                M_change * 0.3 +  # Material (실제 주가) 30%
                S_change * 0.1 +  # Spirit (심리) 10%
                K_change * 0.1    # Knowledge (재무) 10%
            )
            
            # 아크탄젠트 스케일링: -5% ~ +5% 범위로 압축
            raw_change = weighted_change * 20
            predicted_change = np.arctan(raw_change) / np.pi * 0.05
            
            return predicted_change
        except Exception as e:
            logger.warning(f"⚠️ 주식 예측 변화량 계산 실패: {e}")
            return 0.0
    
    def _calculate_dynamic_confidence_stock(
        self,
        vector_4d: Dict[str, float],
        predicted_state: Dict[str, float]
    ) -> float:
        """동적 신뢰도 계산 (주식 특화)"""
        try:
            EQUILIBRIUM = 0.25
            
            # L 차원 편차에 더 높은 가중치 (주식 특화)
            L_deviation = abs(vector_4d.get('L', 0.25) - EQUILIBRIUM)
            M_deviation = abs(vector_4d.get('M', 0.25) - EQUILIBRIUM)
            
            # 주식 특화 신뢰도 계산
            deviation_score = (L_deviation * 0.6 + M_deviation * 0.4) * 4  # 정규화
            
            # 예측 일관성
            predicted_values = list(predicted_state.values())
            predicted_mean = sum(predicted_values) / len(predicted_values)
            predicted_variance = sum((v - predicted_mean) ** 2 for v in predicted_values) / len(predicted_values)
            stability = max(0.0, min(1.0, 1.0 - predicted_variance * 10))
            
            # 가중 평균
            confidence = (
                deviation_score * 0.6 +    # L+M 편차 (60%)
                stability * 0.4           # 예측 일관성 (40%)
            )
            
            # 0.3 ~ 0.9 범위로 정규화
            confidence = 0.3 + (confidence * 0.6)
            
            return confidence
        except Exception as e:
            logger.warning(f"⚠️ 주식 동적 신뢰도 계산 실패: {e}")
            return 0.5
    
    def _price_to_vector_stock(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        per: float = 0.0,
        pbr: float = 0.0
    ) -> Dict[str, List[float]]:
        """가격 데이터를 벡터로 변환 (주식 특화)"""
        try:
            # PD Vector (Primary Drive): 가격 추세 + 재무 지표
            pd_vector = [
                current_price / price_data['close'].mean() if len(price_data) > 0 else 1.0,
                price_data['close'].pct_change().mean() if len(price_data) > 1 else 0.0,
                (1.0 / per) if per > 0 else 0.5,  # PER 역수 (낮을수록 좋음)
                (1.0 / pbr) if pbr > 0 else 0.5    # PBR 역수 (낮을수록 좋음)
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
            logger.error(f"❌ 주식 벡터 변환 실패: {e}")
            return {
                'pd': [1.0, 0.0, 0.5, 0.5],
                'sd': [0.0, 0.0, 0.0]
            }
    
    def _technical_analysis_stock(
        self,
        price_data: pd.DataFrame,
        current_price: float,
        volume: float = 0.0
    ) -> Dict[str, float]:
        """주식 특화 기술적 분석"""
        try:
            # RSI
            rsi = self._calculate_rsi(price_data)
            rsi_score = abs(rsi - 50) / 50  # 0~1 범위
            
            # MACD
            macd_signal = self._calculate_macd_signal(price_data)
            macd_score = abs(macd_signal) * 100  # 0~1 범위로 정규화 필요
            
            # 거래량 분석
            volume_score = 0.5
            if 'volume' in price_data.columns and len(price_data) > 0:
                volume_ratio = volume / price_data['volume'].mean() if price_data['volume'].mean() > 0 else 1.0
                volume_score = min(1.0, volume_ratio / 2.0)
            
            # 기술적 분석 종합 점수
            technical_score = (rsi_score + macd_score + volume_score) / 3
            
            # 모멘텀 점수
            momentum = (current_price - price_data['close'].iloc[-5:].mean()) / price_data['close'].iloc[-5:].mean() if len(price_data) >= 5 else 0.0
            momentum_score = max(0.0, min(1.0, 0.5 + momentum * 10))
            
            return {
                'technical_score': technical_score,
                'fundamental_score': 0.5,  # 재무 지표는 별도로 계산
                'momentum_score': momentum_score
            }
        except Exception as e:
            logger.warning(f"⚠️ 기술적 분석 실패: {e}")
            return {
                'technical_score': 0.5,
                'fundamental_score': 0.5,
                'momentum_score': 0.5
            }
    
    def _generate_stock_signal(self, analysis_result: Dict[str, Any]) -> str:
        """매매 신호 생성 (주식 특화 로직)"""
        try:
            # 병리 수준 확인
            pathology_level = analysis_result.get('pathology_level', 'SL')
            if pathology_level == 'DL':
                return 'HOLD'
            
            # 신뢰도 확인 (주식은 더 높은 임계값)
            confidence = analysis_result.get('confidence', 0.5)
            if confidence < 0.6:  # 주식은 60% 이상 필요
                return 'HOLD'
            
            # 기술적 분석 점수 확인
            technical_score = analysis_result.get('stock_specific', {}).get('technical_score', 0.5)
            if technical_score < 0.5:
                return 'HOLD'
            
            # 예측 변화량 확인
            predicted_change = analysis_result.get('predicted_change', 0.0)
            
            # 주식 특화 신호 생성 (더 보수적)
            if predicted_change > 0.02:  # 2% 이상 상승 예측
                return 'BUY'
            elif predicted_change < -0.02:  # 2% 이상 하락 예측
                return 'SELL'
            else:
                return 'HOLD'
        except Exception as e:
            logger.error(f"❌ 주식 신호 생성 실패: {e}")
            return 'HOLD'
    
    def _get_stock_recommendation(self, analysis_result: Dict[str, Any]) -> str:
        """권장 사항 생성 (주식 특화)"""
        try:
            signal = analysis_result.get('signal', 'HOLD')
            confidence = analysis_result.get('confidence', 0.5)
            predicted_change = analysis_result.get('predicted_change', 0.0)
            technical_score = analysis_result.get('stock_specific', {}).get('technical_score', 0.5)
            
            if signal == 'BUY':
                return f"매수 권장 (신뢰도: {confidence:.2%}, 기술적 점수: {technical_score:.2%}, 예상 상승: {predicted_change:.2%})"
            elif signal == 'SELL':
                return f"매도 권장 (신뢰도: {confidence:.2%}, 기술적 점수: {technical_score:.2%}, 예상 하락: {abs(predicted_change):.2%})"
            else:
                return f"보유 권장 (신뢰도: {confidence:.2%}, 기술적 점수: {technical_score:.2%}, 예상 변화: {predicted_change:.2%})"
        except Exception as e:
            logger.error(f"❌ 주식 권장 사항 생성 실패: {e}")
            return "분석 불가"

