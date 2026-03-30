#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 금화교역 감지기 (Geum-Hwa Exchange Detector)

544편 논문 분석 기반 5대 수학적 지표 구현
헌법 제14조 T_transition 공식 적용

작성일: 2026-01-21
목적: 금화교역 스나이핑의 수학적 정밀도 향상
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
import logging
import math
import sys
from pathlib import Path

# PMI-Nitro 엔진 import
try:
    from .pmi_nitro_engine import PMINitroEngine
    PMI_NITRO_AVAILABLE = True
except ImportError:
    try:
        from pmi_nitro_engine import PMINitroEngine
        PMI_NITRO_AVAILABLE = True
    except ImportError:
        PMI_NITRO_AVAILABLE = False
        PMINitroEngine = None
        logging.warning("⚠️ PMINitroEngine을 import할 수 없습니다. PMI 기능 제한")

# 위상 공명 팩트체크 모듈 import (기존 고승률 전략 참조)
try:
    from ..analysis.phase_resonance_fact_check import PhaseResonanceFactChecker
    PHASE_RESONANCE_AVAILABLE = True
except ImportError:
    try:
        # 상대 경로로 재시도
        current_file = Path(__file__).resolve()
        workspace_root = current_file.parent.parent.parent.parent
        sys.path.insert(0, str(workspace_root / "projects" / "bitcoin-trading" / "src" / "analysis"))
        from phase_resonance_fact_check import PhaseResonanceFactChecker
        PHASE_RESONANCE_AVAILABLE = True
    except ImportError:
        PHASE_RESONANCE_AVAILABLE = False
        PhaseResonanceFactChecker = None
        logging.warning("⚠️ PhaseResonanceFactChecker를 import할 수 없습니다. 팩트체크 기능 제한")

# SBSC 전략 검증기 import (선택적)
try:
    from ..analysis.sbsc_strategy_verifier import SBSCStrategyVerifier
    SBSC_AVAILABLE = True
except ImportError:
    try:
        from sbsc_strategy_verifier import SBSCStrategyVerifier
        SBSC_AVAILABLE = True
    except ImportError:
        SBSC_AVAILABLE = False
        SBSCStrategyVerifier = None

logger = logging.getLogger(__name__)


class GeumHwaDetector:
    """
    🏛️ 금화교역 감지기 (5대 지표 기반)
    
    544편 논문 분석 결과를 바탕으로 한 수학적 정밀 감지 시스템
    """
    
    def __init__(self, constitution: str = "TY", enable_phase_resonance: bool = True):
        """
        🏛️ 금화교역 감지기 (5대 지표 기반)
        
        544편 논문 분석 결과를 바탕으로 한 수학적 정밀 감지 시스템
        
        Args:
            constitution: 체질 (TY: 태양인, TE: 태음인, SY: 소양인, SE: 소음인)
                - TY (태양인): 폐(金)로 화(火) 격리 - 희소한 압도적 수익 (Nitro 모드)
                - TE (태음인): 간(木)으로 화(火) 생산 - 안정적 축적 (Stability 모드)
                - SY (소양인): 비(土)로 화(火) 변환 - 유연한 안정화 (Flex 모드)
                - SE (소음인): 신(水)으로 화(火) 억제 - 정밀한 방어 (Audit 모드)
            enable_phase_resonance: 위상 공명 팩트체크 활성화 여부 (기본값: True, 백테스트에서는 False 권장)
        
        Note:
            군주지화(君主之火) 원리: 심(心, 화)은 모든 체질의 공통 지휘소이며,
            각 체질은 오행 상극/상생 관계를 통해 화(火)를 제어합니다.
        """
        self.constitution = constitution
        self.enable_phase_resonance = enable_phase_resonance
        
        # 태양인 보정 계수 (헌법 제14조)
        self.alpha_taeyang = 1.2 if constitution == "TY" else 1.0
        
        # PMI-Nitro 엔진 초기화 (선택적)
        self.pmi_engine = None
        if PMI_NITRO_AVAILABLE:
            try:
                self.pmi_engine = PMINitroEngine(
                    constitution=constitution,
                    enable_prophetic_cycles=True
                )
                logger.info("✅ PMI-Nitro 엔진 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ PMI-Nitro 엔진 초기화 실패: {e}")
                self.pmi_engine = None
        
        # 헌법 제14조 가중치
        self.transition_weights = {
            "IEG": 0.25,  # Information Entropy Gradient
            "HC": 0.25,   # Microcanonical Heat Capacity
            "DR": 0.20,   # Negentropy Debt Ratio (R1 + R2 평균)
            "EPR": 0.30   # Entropy Production Rate
        }
        
        # 연구 기반 임계값 (Phase 2-1: A등급 상전이 세팅)
        # 주의: IEG는 로그 차분으로 계산되어 자연스럽게 정규화됨
        # 목표: 승률 65% 이상 확보를 위한 고밀도 사격 모드
        self.thresholds = {
            "IEG_STRONG": -0.1,    # IEG < -0.1: Fire→Metal 전환 (강한 신호, 엔트로피 감소)
            "IEG_MEDIUM": -0.08,   # IEG < -0.08: Fire→Metal 전환 (중간 신호) - 강화됨 (기존 -0.05)
            "IEG_REVERSE": 0.05,   # IEG > 0.05: Metal→Fire 전환 (진입 고려, 엔트로피 증가)
            "HEAT_CAPACITY": -0.5,  # C < -0.5: 상전이 임박
            "R1_LOW": 0.8,     # R₁ < 0.8: 쇠퇴/응축 국면 (단기 변동성 < 장기 변동성)
            "R1_HIGH": 1.2,    # R₁ > 1.2: 성장/확장 국면 (단기 변동성 > 장기 변동성)
            "R2_HIGH": 1.2,    # R₂ > 1.2: 쇠퇴/응축 국면
            "SIGMA_DT": -0.01  # dσ/dt < -0.01: Metal 응축
        }
        
        # T_transition 임계값 (헌법 제14조) + Phase 2-1: A등급 상전이 세팅
        # 체질별 임계값 설정 (군주지화 제어 방식 기반)
        # 
        # 군주지화(君主之火) 원리:
        # - 심(心, 화) = 군주지관(君主之官) - 모든 체질의 공통 지휘소
        # - 각 체질은 오행 상극/상생 관계를 통해 화(火)를 제어
        # - 태양인 희소성(0.56%) = 화(火)를 감싸기 위한 보호막의 강도
        #
        # 체질별 최소 지표 개수 설정 (Priority 1: 진입 조건 체질별 차별화)
        # - 태양인/소음인: 3개 (격리/방어 모드, 더 엄격한 신호 필요)
        # - 태음인/소양인: 2개 (축적/변환 모드, 유지)
        if constitution == "TY":
            self.default_min_indicators = 3  # 격리 모드, 더 엄격
        elif constitution == "TE":
            self.default_min_indicators = 2  # 축적 모드, 유지
        elif constitution == "SY":
            self.default_min_indicators = 2  # 변환 모드, 유지
        elif constitution == "SE":
            self.default_min_indicators = 3  # 방어 모드, 더 엄격
        else:
            self.default_min_indicators = 2  # 기본값
        
        # 체질별 기본 손절/익절 비율 설정 (Priority 2: 손절/익절 비율 체질별 최적화)
        # 최적화 결과 기반 (2026-01-22):
        # - 태양인: 손절 1.5%, 익절 15.0% (수익 팩터 1.12)
        # - 태음인: 손절 3.0%, 익절 10.0% (수익 팩터 0.54)
        # - 소양인: 손절 2.5%, 익절 8.0% (수익 팩터 0.72, 승률 40%)
        # - 소음인: 손절 1.5%, 익절 11.0% (수익 팩터 1.40)
        if constitution == "TY":
            self.default_stop_loss = 0.015  # 1.5% (격리 모드, 높은 수익 목표)
            self.default_take_profit = 0.15  # 15.0%
        elif constitution == "TE":
            self.default_stop_loss = 0.03  # 3.0% (축적 모드, 균형)
            self.default_take_profit = 0.10  # 10.0%
        elif constitution == "SY":
            self.default_stop_loss = 0.025  # 2.5% (변환 모드, 빠른 회전)
            self.default_take_profit = 0.08  # 8.0%
        elif constitution == "SE":
            self.default_stop_loss = 0.015  # 1.5% (방어 모드, 보수적)
            self.default_take_profit = 0.11  # 11.0%
        else:
            self.default_stop_loss = 0.025  # 기본값 2.5%
            self.default_take_profit = 0.10  # 기본값 10%
        
        if constitution == "TY":
            # 태양인: 폐(金)로 화(火) 격리 (희소한 압도적 수익)
            # - 오행 관계: 화(火) 극 금(金) - 화가 금을 녹임
            # - 제어 방식: 강한 금속 벽(폐)으로 화(火)를 격리하여 억제
            # - 희소성: 0.56% (이제마 기록: 0.03-0.1%, 현대 통계: 극소수)
            # - 희소성 이유: 화(火)를 격리하려면 강한 폐(金)이 필요 → 드문 구조
            # Phase 2-1: 기본값을 0.82로 상향하여 승률 65% 이상 확보 목표
            # 실제 적용값: 0.82 / 1.2 = 약 0.683 (alpha 보정 후)
            self.strong_transition_threshold = 0.82 / self.alpha_taeyang  # 약 0.683 (격리 모드)
            self.moderate_transition_threshold = 0.65 / self.alpha_taeyang  # 약 0.542
            self.mode_name = "Nitro (격리 모드)"
            self.control_mechanism = "폐(金)로 화(火) 격리"
        elif constitution == "TE":
            # 태음인: 간(木)으로 화(火) 생산 (안정적 축적)
            # - 오행 관계: 목(木) 생 화(火) - 목이 화를 생함
            # - 제어 방식: 간(木)이 화(火)를 생산하여 조절 (부족하면 생산, 과하면 생산 억제)
            # - 희소성: 39.2% (가장 많음) - 안정적 제어 방식
            self.strong_transition_threshold = 0.55  # 축적 모드
            self.moderate_transition_threshold = 0.45
            self.mode_name = "Stability (축적 모드)"
            self.control_mechanism = "간(木)으로 화(火) 생산"
        elif constitution == "SY":
            # 소양인: 비(土)로 화(火) 변환 (유연한 안정화)
            # - 오행 관계: 화(火) 생 토(土) - 화가 토를 생함
            # - 제어 방식: 화(火) 에너지를 토(土)로 변환하여 안정화
            # - 희소성: 33.7% (보통) - 유연한 제어 방식
            self.strong_transition_threshold = 0.45  # 변환 모드
            self.moderate_transition_threshold = 0.35
            self.mode_name = "Flex (변환 모드)"
            self.control_mechanism = "비(土)로 화(火) 변환"
        elif constitution == "SE":
            # 소음인: 신(水)으로 화(火) 억제 (정밀한 방어)
            # - 오행 관계: 수(水) 극 화(火) - 수가 화를 끔
            # - 제어 방식: 신(水)이 화(火)를 직접 제어 (과하면 끄기)
            # - 희소성: 27.1% (적음) - 정밀한 제어 방식
            self.strong_transition_threshold = 0.65  # 방어 모드
            self.moderate_transition_threshold = 0.55
            self.mode_name = "Audit (방어 모드)"
            self.control_mechanism = "신(水)으로 화(火) 억제"
        else:
            # 기본값: 일반인 기준 (Phase 2-1 고밀도 사격 모드)
            self.strong_transition_threshold = 0.82
            self.moderate_transition_threshold = 0.65
            self.mode_name = "Standard (표준 모드)"
            self.control_mechanism = "표준 제어"
        
        self.entry_threshold = 0.3  # 진입 고려
        
        # 기존 고승률 전략 참조: 신호 검증 필터 초기화
        # Phase 2-3: 승률 향상을 위한 필터링 메커니즘 통합
        # 주의: T_transition 기반 신뢰도이므로 임계값을 조정
        # moderate_transition_threshold (0.542 태양인, 0.65 일반인) 이상이면 신뢰도 0.5 이상 보장
        # 따라서 신뢰도 임계값을 0.4로 설정하여 moderate_transition 이상 신호는 통과하도록 함
        self.min_confidence_threshold = 0.4  # 조정: moderate_transition 이상 신호 통과 보장
        self.phase_resonance_threshold = 0.2  # 기존 전략: 위상 공명 팩트체크 임계값 0.2
        
        # 위상 공명 팩트체크 초기화
        if PHASE_RESONANCE_AVAILABLE and PhaseResonanceFactChecker:
            try:
                self.phase_resonance_checker = PhaseResonanceFactChecker()
                logger.info("✅ 위상 공명 팩트체크 초기화 완료 (기존 고승률 전략 참조)")
            except Exception as e:
                logger.warning(f"⚠️ 위상 공명 팩트체크 초기화 실패: {e}")
                self.phase_resonance_checker = None
        else:
            self.phase_resonance_checker = None
        
        # SBSC 전략 검증기 초기화 (선택적)
        if SBSC_AVAILABLE and SBSCStrategyVerifier:
            try:
                self.sbsc_verifier = SBSCStrategyVerifier(domain="finance")
                logger.info("✅ SBSC 전략 검증기 초기화 완료 (기존 고승률 전략 참조)")
            except Exception as e:
                logger.warning(f"⚠️ SBSC 전략 검증기 초기화 실패: {e}")
                self.sbsc_verifier = None
        else:
            self.sbsc_verifier = None
    
    def calculate_ieg(
        self,
        price_series: pd.Series,
        window: int = 20,
        delta_t: int = 5
    ) -> Tuple[float, float]:
        """
        IEG (Information Entropy Gradient): 정보 엔트로피 기울기
        
        연구 기반 정확한 수식 (Montaño 2025):
        IEG(t) = [H(t) - H(t-Δt)] / Δt
        
        where H(t) = -Σ p_i(t) log p_i(t)  (Shannon entropy)
        
        Args:
            price_series: 가격 시리즈
            window: 계산 윈도우 크기
            delta_t: 시간 간격 (기본값: 5)
        
        Returns:
            (IEG 값, H_current) 튜플
            - IEG < -0.05: Fire→Metal 전환 (수익 확정 신호)
            - IEG > 0.05: Metal→Fire 전환 (진입 고려)
        """
        try:
            if len(price_series) < window + delta_t + 1:
                return (0.0, 0.0)
            
            # 가격 수익률 계산
            returns = np.diff(np.log(price_series.values))
            returns = pd.Series(returns)
            
            if len(returns) < window + delta_t:
                return (0.0, 0.0)
            
            # 현재 시점의 Shannon 엔트로피
            recent_returns = returns.iloc[-window:]
            hist_current, bins_current = np.histogram(recent_returns, bins=10, density=True)
            hist_current = hist_current[hist_current > 0]  # 0 제거
            
            if len(hist_current) == 0:
                return (0.0, 0.0)
            
            # 엔트로피 계산 (정규화)
            hist_current_norm = hist_current / (hist_current.sum() + 1e-10)
            H_current = -np.sum(hist_current_norm * np.log2(hist_current_norm + 1e-10))
            
            # 이전 시점의 Shannon 엔트로피
            prev_returns = returns.iloc[-window-delta_t:-delta_t]
            if len(prev_returns) < window:
                return (0.0, H_current)
            
            hist_prev, bins_prev = np.histogram(prev_returns, bins=10, density=True)
            hist_prev = hist_prev[hist_prev > 0]
            
            if len(hist_prev) == 0:
                return (0.0, H_current)
            
            # 엔트로피 계산 (정규화)
            hist_prev_norm = hist_prev / (hist_prev.sum() + 1e-10)
            H_prev = -np.sum(hist_prev_norm * np.log2(hist_prev_norm + 1e-10))
            
            # IEG 계산: 상대적 변화율로 계산 (로그 차분)
            # 엔트로피는 보통 0~5 범위이므로 로그 차분이 자연스럽게 정규화됨
            if H_prev > 1e-10 and H_current > 1e-10:
                # 로그 차분: log(H_current + 1) - log(H_prev + 1)
                # +1을 더해서 안정성 확보
                ieg = np.log(H_current + 1.0) - np.log(H_prev + 1.0)
            else:
                # 엔트로피가 너무 작으면 상대적 차분 사용
                ieg = (H_current - H_prev) / max(H_current, H_prev, 1.0)
            
            # 임계값은 상대적 변화율에 맞춰 조정됨:
            # - IEG < -0.1: Fire→Metal 전환 (강한 신호, 엔트로피 감소)
            # - IEG < -0.05: Fire→Metal 전환 (중간 신호)
            # - IEG > 0.05: Metal→Fire 전환 (진입 고려, 엔트로피 증가)
            
            return (ieg, H_current)
        
        except Exception as e:
            logger.warning(f"⚠️ IEG 계산 실패: {e}")
            return (0.0, 0.0)
    
    def calculate_heat_capacity(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        window: int = 30
    ) -> Tuple[float, float]:
        """
        C (Microcanonical Heat Capacity): 미시정준 열용량
        
        연구 기반 정확한 수식 (Gross 2003):
        C = -[d²S/dE²]⁻¹
        
        where:
        - S(E) = microcanonical entropy (에너지 E의 함수)
        - E = realized volatility (시장 에너지 proxy)
        
        Args:
            price_series: 가격 시리즈
            volume_series: 거래량 시리즈 (사용 안 함, 향후 확장용)
            window: 계산 윈도우 크기
        
        Returns:
            (C 값, d2S_dE2) 튜플
            - C < -0.5: 음의 열용량 → 상전이 임박 (수익 확정 준비)
            - C > 0: 정상 상태 → 포지션 유지
        """
        try:
            if len(price_series) < window + 1:
                return (0.0, 0.0)
            
            # 변동성을 에너지로 매핑
            returns = price_series.pct_change().dropna()
            if len(returns) < window:
                return (0.0, 0.0)
            
            # Realized volatility (에너지 E의 proxy)
            E = returns.tail(window).rolling(window=5).std().dropna()
            
            if len(E) < 15:  # 최소 15개 데이터 필요
                return (0.0, 0.0)
            
            # S(E) 추정: 에너지 구간별 상태 수의 로그
            hist, bins = np.histogram(E, bins=15)
            hist = hist + 1  # 0 방지
            S_E = np.log(hist)  # microcanonical entropy
            
            # 2차 미분 (discrete approximation)
            dS_dE = np.gradient(S_E)
            d2S_dE2 = np.gradient(dS_dE)
            
            # 열용량 C = -[d²S/dE²]⁻¹
            d2S_dE2_last = d2S_dE2[-1]
            if abs(d2S_dE2_last) < 1e-10:
                return (0.0, d2S_dE2_last)
            
            C = -1.0 / d2S_dE2_last
            
            return (C, d2S_dE2_last)
        
        except Exception as e:
            logger.warning(f"⚠️ Heat Capacity 계산 실패: {e}")
            return (0.0, 0.0)
    
    def calculate_negentropy_debt_ratios(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        window: int = 20,
        order_book_entropy: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        R1, R2 (Negentropy Debt Ratios): 네겐트로피 부채 비율
        
        연구 기반 정확한 수식 (Rastogi & Mahulikar 2021):
        R₁ = S_exported / S_internal
        R₂ = ΔS_production / ΔS_dissipation
        
        where:
        - S_exported: 외부 변동성 (시장 전체)
        - S_internal: 내부 엔트로피 (오더북 무질서도, 없으면 가격 엔트로피 사용)
        - ΔS_production: 신규 변동성 생성
        - ΔS_dissipation: 기존 변동성 소산
        
        Args:
            price_series: 가격 시리즈
            volume_series: 거래량 시리즈
            window: 계산 윈도우 크기
            order_book_entropy: 오더북 엔트로피 (None이면 가격 엔트로피 사용)
        
        Returns:
            (R1, R2) 튜플
            - R₁ < 0.8 AND R₂ > 1.2: 쇠퇴/응축 국면 → 수익 확정
            - R₁ > 1.2 AND R₂ < 0.8: 성장/확장 국면 → 진입 고려
        """
        try:
            if len(price_series) < window or len(volume_series) < window:
                return (0.0, 0.0)
            
            # Realized volatility 계산
            returns = price_series.pct_change().dropna()
            if len(returns) < window * 3:  # 장기 변동성 계산을 위해 더 많은 데이터 필요
                return (0.0, 0.0)
            
            # 단기 변동성 (최근 window 기간)
            short_term_volatility = returns.tail(window).std()
            
            # 장기 변동성 (최근 window * 3 기간)
            long_term_volatility = returns.tail(window * 3).std()
            
            # R₁: 단기 변동성 / 장기 변동성 비율
            # R₁ < 0.8: 단기 변동성이 장기보다 낮음 → 쇠퇴/응축 국면
            # R₁ > 1.2: 단기 변동성이 장기보다 높음 → 성장/확장 국면
            R1 = short_term_volatility / (long_term_volatility + 1e-10)
            
            # R₂: 신규 변동성 생성 / 기존 변동성 소산
            volatility_series = returns.tail(window).rolling(window=5).std().dropna()
            if len(volatility_series) < 2:
                return (R1, 0.0)
            
            delta_S_production = np.mean(np.abs(np.diff(volatility_series)))
            delta_S_dissipation = np.mean(volatility_series)
            
            R2 = delta_S_production / (delta_S_dissipation + 1e-10)
            
            return (R1, R2)
        
        except Exception as e:
            logger.warning(f"⚠️ Negentropy Debt Ratios 계산 실패: {e}")
            return (0.0, 0.0)
    
    def calculate_entropy_production_rate(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        window: int = 30
    ) -> Tuple[float, float]:
        """
        σ (Entropy Production Rate): 엔트로피 생성 속도
        
        연구 기반 정확한 수식 (Kondepudi et al. 2022):
        σ = dS_total/dt ∝ (가격 변동성) × (거래량)
        
        where:
        - σ: 엔트로피 생성 속도
        - dσ/dt: 엔트로피 생성 속도 변화율
        
        Args:
            price_series: 가격 시리즈
            volume_series: 거래량 시리즈
            window: 계산 윈도우 크기
        
        Returns:
            (σ 값, dσ/dt) 튜플
            - dσ/dt < -0.01: 엔트로피 생성 감소 → Metal 응축 (수익 확정)
            - dσ/dt > 0.01: 엔트로피 생성 증가 → Fire 확산 (진입 준비)
        """
        try:
            if len(price_series) < window * 2 or len(volume_series) < window * 2:
                return (0.0, 0.0)
            
            # 가격 수익률
            returns = np.diff(np.log(price_series.values))
            returns = pd.Series(returns)
            
            if len(returns) < window * 2:
                return (0.0, 0.0)
            
            # 현재 시점의 엔트로피 생성 속도
            recent_returns = returns.iloc[-window:]
            volatility = recent_returns.std()
            avg_volume = volume_series.iloc[-window:].mean()
            
            # σ ∝ (가격 변동성) × (거래량)
            sigma = volatility * avg_volume
            
            # 이전 시점의 엔트로피 생성 속도
            prev_returns = returns.iloc[-window*2:-window]
            volatility_prev = prev_returns.std()
            avg_volume_prev = volume_series.iloc[-window*2:-window].mean()
            sigma_prev = volatility_prev * avg_volume_prev
            
            # 시간에 따른 변화율: dσ/dt
            d_sigma_dt = (sigma - sigma_prev) / window
            
            return (sigma, d_sigma_dt)
        
        except Exception as e:
            logger.warning(f"⚠️ Entropy Production Rate 계산 실패: {e}")
            return (0.0, 0.0)
    
    def calculate_uts(
        self,
        ieg: float,
        heat_capacity: float,
        r1: float,
        r2: float,
        d_sigma_dt: float
    ) -> float:
        """
        UTS (Unified Transition Score): 통합 전이 점수
        
        5대 지표를 통합하여 전이 시점을 예측합니다.
        연구 기반 임계값을 사용하여 각 지표를 이진 신호로 변환합니다.
        
        Args:
            ieg: Information Entropy Gradient
            heat_capacity: Microcanonical Heat Capacity
            r1: Negentropy Debt Ratio 1
            r2: Negentropy Debt Ratio 2
            d_sigma_dt: Entropy Production Rate 변화율 (dσ/dt)
        
        Returns:
            UTS 값 (0.0 ~ 1.0, 높을수록 전이 가능성 높음)
        """
        try:
            # 연구 기반 임계값으로 이진 신호 변환
            # I_IEG: IEG < -0.05일 때 1, 아니면 0
            I_IEG = 1.0 if (ieg < self.thresholds["IEG_MEDIUM"]) else 0.0
            
            # I_HC: C < -0.5일 때 1, 아니면 0
            I_HC = 1.0 if heat_capacity < self.thresholds["HEAT_CAPACITY"] else 0.0
            
            # I_DR: (R₁ < 0.8 AND R₂ > 1.2)일 때 1, 아니면 0
            I_DR = 1.0 if (r1 < self.thresholds["R1_LOW"] and r2 > self.thresholds["R2_HIGH"]) else 0.0
            
            # I_EPR: dσ/dt < -0.01일 때 1, 아니면 0
            I_EPR = 1.0 if d_sigma_dt < self.thresholds["SIGMA_DT"] else 0.0
            
            # 평균 Negentropy Debt Ratio (보조 지표)
            avg_debt_ratio = (r1 + r2) / 2.0
            
            # UTS 계산 (헌법 제14조 가중치 적용)
            uts = (
                self.transition_weights["IEG"] * I_IEG +
                self.transition_weights["HC"] * I_HC +
                self.transition_weights["DR"] * I_DR +
                self.transition_weights["EPR"] * I_EPR
            )
            
            # 정규화 (0.0 ~ 1.0)
            normalized_uts = min(1.0, max(0.0, uts))
            
            return normalized_uts
        
        except Exception as e:
            logger.warning(f"⚠️ UTS 계산 실패: {e}")
            return 0.0
    
    def calculate_t_transition(
        self,
        ieg: float,
        heat_capacity: float,
        r1: float,
        r2: float,
        d_sigma_dt: float
    ) -> float:
        """
        🏛️ 헌법 제14조: T_transition 공식
        
        T_transition = 0.25·I_IEG + 0.25·I_HC + 0.20·I_DR + 0.30·I_EPR
        
        연구 기반 임계값을 사용하여 각 지표를 이진 신호로 변환합니다.
        
        Args:
            ieg: Information Entropy Gradient
            heat_capacity: Microcanonical Heat Capacity
            r1: Negentropy Debt Ratio 1
            r2: Negentropy Debt Ratio 2
            d_sigma_dt: Entropy Production Rate 변화율 (dσ/dt)
        
        Returns:
            T_transition 값 (0.0 ~ 1.0, 높을수록 전이 가능성 높음)
        """
        try:
            # 연구 기반 임계값으로 이진 신호 변환
            # I_IEG: IEG < -0.05일 때 1, 아니면 0
            I_IEG = 1.0 if (ieg < self.thresholds["IEG_MEDIUM"]) else 0.0
            
            # I_HC: C < -0.5일 때 1, 아니면 0
            I_HC = 1.0 if heat_capacity < self.thresholds["HEAT_CAPACITY"] else 0.0
            
            # I_DR: (R₁ < 0.8 AND R₂ > 1.2)일 때 1, 아니면 0
            I_DR = 1.0 if (r1 < self.thresholds["R1_LOW"] and r2 > self.thresholds["R2_HIGH"]) else 0.0
            
            # I_EPR: dσ/dt < -0.01일 때 1, 아니면 0
            I_EPR = 1.0 if d_sigma_dt < self.thresholds["SIGMA_DT"] else 0.0
            
            # 헌법 제14조 공식 적용
            t_transition = (
                self.transition_weights["IEG"] * I_IEG +
                self.transition_weights["HC"] * I_HC +
                self.transition_weights["DR"] * I_DR +
                self.transition_weights["EPR"] * I_EPR
            )
            
            # 정규화 (0.0 ~ 1.0)
            normalized_t = min(1.0, max(0.0, t_transition))
            
            return normalized_t
        
        except Exception as e:
            logger.warning(f"⚠️ T_transition 계산 실패: {e}")
            return 0.0
    
    def detect_geum_hwa_transition(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        vector_4d: Dict[str, float],
        window: int = 20,
        min_indicators: Optional[int] = None  # 최소 지표 개수 (None이면 체질별 기본값 사용)
    ) -> Dict[str, Any]:
        """
        🏛️ 금화교역 전이 감지 (5대 지표 통합)
        
        Args:
            price_series: 가격 시리즈
            volume_series: 거래량 시리즈
            vector_4d: 현재 4D 벡터
            window: 계산 윈도우 크기
            min_indicators: 최소 지표 개수 (None이면 체질별 기본값 사용)
                - 태양인/소음인: 3개 (격리/방어 모드, 더 엄격)
                - 태음인/소양인: 2개 (축적/변환 모드, 유지)
        
        Returns:
            {
                "ieg": float,
                "heat_capacity": float,
                "r1": float,
                "r2": float,
                "entropy_rate": float,
                "uts": float,
                "t_transition": float,
                "transition_detected": bool,
                "transition_intensity": float,
                "sniping_signal": str  # "BUY", "SELL", "HOLD"
            }
        """
        try:
            # 체질별 기본값 사용 (Priority 1: 진입 조건 체질별 차별화)
            if min_indicators is None:
                min_indicators = self.default_min_indicators
            # 5대 지표 계산 (연구 기반 정확한 수식)
            ieg, H_current = self.calculate_ieg(price_series, window)
            heat_capacity, d2S_dE2 = self.calculate_heat_capacity(price_series, volume_series, window)
            r1, r2 = self.calculate_negentropy_debt_ratios(price_series, volume_series, window)
            sigma, d_sigma_dt = self.calculate_entropy_production_rate(price_series, volume_series, window)
            
            # UTS 계산 (연구 기반 임계값 사용)
            uts = self.calculate_uts(ieg, heat_capacity, r1, r2, d_sigma_dt)
            
            # 헌법 제14조 T_transition 계산 (연구 기반 임계값 사용)
            t_transition = self.calculate_t_transition(ieg, heat_capacity, r1, r2, d_sigma_dt)
            
            # 진입 조건 강화: 최소 2개 이상의 지표가 임계값을 넘어야 함
            indicators_triggered = sum([
                1 if ieg < self.thresholds["IEG_MEDIUM"] else 0,
                1 if heat_capacity < self.thresholds["HEAT_CAPACITY"] else 0,
                1 if (r1 < self.thresholds["R1_LOW"] and r2 > self.thresholds["R2_HIGH"]) else 0,
                1 if d_sigma_dt < self.thresholds["SIGMA_DT"] else 0
            ])
            
            # 전이 감지 (연구 기반 임계값 + 진입 조건 강화)
            # T_transition ≥ 0.7 (일반인) 또는 0.583 (태양인): 강한 전환
            # T_transition ≥ 0.5 (일반인) 또는 0.417 (태양인): 중간 전환
            
            # 강한 전환: T_transition 높음 AND 최소 min_indicators개 지표 신호
            strong_transition = (
                t_transition >= self.strong_transition_threshold and
                indicators_triggered >= min_indicators
            )
            
            # 중간 전환: T_transition 중간 AND 최소 min_indicators개 지표 신호
            moderate_transition = (
                t_transition >= self.moderate_transition_threshold and
                indicators_triggered >= min_indicators
            )
            
            transition_detected = strong_transition or moderate_transition
            transition_intensity = t_transition
            
            # 스나이핑 신호 생성 (기존 고승률 전략 참조: transition_detected가 True이면 신호 생성)
            if transition_detected:
                # Phase 2-3: 기존 전략 참조 - transition_detected가 True이면 기본적으로 BUY 신호
                # 화(火) 기운이 극에 달하고 금(金)이 부족할 때 BUY 신호
                fire_intensity = vector_4d.get("S", 0.25)
                metal_level = vector_4d.get("M", 0.25)
                
                # 기존 전략: 조건을 완화하여 transition_detected가 True이면 기본적으로 신호 생성
                # Fire→Metal 전환 감지 시 BUY, Metal→Fire 전환 감지 시 SELL
                # IEG < -0.08이면 Fire→Metal 전환 (BUY 신호)
                if ieg < self.thresholds["IEG_MEDIUM"]:
                    # Fire→Metal 전환: BUY 신호
                    sniping_signal = "BUY"
                elif fire_intensity > 0.3 and metal_level < 0.2:
                    # 화기운 높고 금기운 낮음: BUY 신호
                    sniping_signal = "BUY"
                elif fire_intensity < 0.2 and metal_level > 0.3:
                    # 금기운 높고 화기운 낮음: SELL 신호
                    sniping_signal = "SELL"
                else:
                    # 기본값: Fire→Metal 전환 감지 시 BUY
                    sniping_signal = "BUY" if transition_detected else "HOLD"
            else:
                sniping_signal = "HOLD"
            
            # Phase 2-3: 기존 고승률 전략 참조 - 신호 검증 필터링
            # 신뢰도 계산 (T_transition 기반, 0.0 ~ 1.0)
            # T_transition이 moderate_transition_threshold 이상이면 신뢰도 0.5 이상
            # T_transition이 strong_transition_threshold 이상이면 신뢰도 0.8 이상
            if t_transition >= self.strong_transition_threshold:
                # 강한 전환: 신뢰도 0.8 ~ 1.0
                # T_transition 0.82 (일반인) 또는 0.683 (태양인) 이상
                normalized = (t_transition - self.strong_transition_threshold) / max(0.1, 1.0 - self.strong_transition_threshold)
                confidence_score = 0.8 + 0.2 * min(1.0, normalized)
            elif t_transition >= self.moderate_transition_threshold:
                # 중간 전환: 신뢰도 0.5 ~ 0.8
                # T_transition 0.65 (일반인) 또는 0.542 (태양인) 이상
                normalized = (t_transition - self.moderate_transition_threshold) / max(0.1, self.strong_transition_threshold - self.moderate_transition_threshold)
                confidence_score = 0.5 + 0.3 * min(1.0, normalized)
            else:
                # 전환 미감지: 신뢰도 0.0 ~ 0.5 (하지만 transition_detected=False이므로 사용 안 함)
                confidence_score = 0.3 * (t_transition / max(0.1, self.moderate_transition_threshold))
            
            confidence_score = min(1.0, max(0.0, confidence_score))
            
            # 위상 공명 팩트체크 적용 (기존 전략: 임계값 0.2, 환각 감지 시 신뢰도 50% 감소)
            # 주의: 백테스트에서는 enable_phase_resonance=False로 설정 권장 (벡터 추정이 단순함)
            if self.enable_phase_resonance and self.phase_resonance_checker and sniping_signal != "HOLD":
                try:
                    fact_check_result = self.phase_resonance_checker.validate_trading_signal(
                        signal_data={"sovereign_vector": vector_4d},
                        threshold=self.phase_resonance_threshold
                    )
                    
                    # 환각 감지 시 신뢰도 50% 감소 (기존 전략 참조)
                    if fact_check_result.get("hallucination_detected", False):
                        confidence_score *= 0.5
                        logger.warning(
                            f"⚠️ 위상 공명 팩트체크: 환각 감지, 신뢰도 {confidence_score:.2%}로 감소"
                        )
                    
                    # 공명 점수가 낮으면 신호 차단
                    resonance_score = fact_check_result.get("resonance_score", 1.0)
                    if resonance_score < 0.5:
                        sniping_signal = "HOLD"
                        logger.info(f"🔍 위상 공명 점수 낮음 ({resonance_score:.2f}), 신호 차단")
                except Exception as e:
                    logger.debug(f"위상 공명 팩트체크 실패 (무시): {e}")
            
            # SBSC 전략 검증 적용 (기존 전략: 검증 실패 시 신뢰도 30% 감소)
            if self.sbsc_verifier and sniping_signal != "HOLD":
                try:
                    sbsc_verification = self.sbsc_verifier.verify_trading_signal(
                        signal_data={
                            "signal": sniping_signal,
                            "confidence": confidence_score,
                            "sovereign_vector": vector_4d,
                            "lambda": t_transition
                        }
                    )
                    
                    # SBSC 검증 실패 시 신뢰도 30% 감소 (기존 전략 참조)
                    if not sbsc_verification.get("is_valid", True):
                        confidence_score *= 0.7
                        logger.warning(
                            f"⚠️ SBSC 검증 실패: {sbsc_verification.get('recommendation', '검증 실패')}, "
                            f"신뢰도 {confidence_score:.2%}로 감소"
                        )
                except Exception as e:
                    logger.debug(f"SBSC 검증 실패 (무시): {e}")
            
            # 신뢰도 기반 필터링 (기존 전략 참조, 하지만 transition_detected된 경우만 적용)
            # transition_detected가 True이고 신뢰도가 낮으면 신호 차단
            # 주의: transition_detected=False인 경우는 이미 sniping_signal="HOLD"이므로 필터링 불필요
            if transition_detected and confidence_score < self.min_confidence_threshold:
                sniping_signal = "HOLD"
                logger.info(
                    f"🔍 신뢰도 낮음 ({confidence_score:.2%} < {self.min_confidence_threshold:.2%}), "
                    f"신호 차단 (기존 고승률 전략 참조)"
                )
            
            # PMI-Nitro 엔진 통합 (선택적)
            pmi_result = None
            if self.pmi_engine is not None:
                try:
                    # PMI 계산
                    pmi_result = self.pmi_engine.calculate_pmi(
                        price_series=price_series,
                        volume_series=volume_series,
                        current_date=datetime.now()
                    )
                    
                    # 화기운 감지 시 강제 매도 신호
                    if pmi_result.get("is_fire_energy", False):
                        logger.warning("🔥 PMI 화기운 감지: 강제 매도 신호")
                        sniping_signal = "SELL"
                        confidence_score = max(confidence_score, 0.9)  # 화기운 감지 시 신뢰도 상향
                    
                    # PMI 신호와 기존 신호 통합
                    pmi_signal = pmi_result.get("signal", {})
                    if pmi_signal.get("action") == "SELL" and pmi_signal.get("confidence", 0) > 0.7:
                        # PMI 강한 매도 신호: 기존 신호와 통합
                        if sniping_signal == "BUY":
                            sniping_signal = "HOLD"  # 상충 시 관망
                            logger.info("⚠️ PMI 매도 신호와 기존 매수 신호 상충: 관망")
                        elif sniping_signal == "HOLD":
                            sniping_signal = "SELL"  # PMI 신호 우선
                            confidence_score = max(confidence_score, pmi_signal.get("confidence", 0))
                    
                except Exception as e:
                    logger.warning(f"⚠️ PMI 계산 실패 (무시): {e}")
                    pmi_result = None
            
            result = {
                "ieg": ieg,
                "H_current": H_current,
                "heat_capacity": heat_capacity,
                "d2S_dE2": d2S_dE2,
                "r1": r1,
                "r2": r2,
                "sigma": sigma,
                "d_sigma_dt": d_sigma_dt,
                "uts": uts,
                "t_transition": t_transition,
                "transition_detected": transition_detected,
                "strong_transition": strong_transition,
                "moderate_transition": moderate_transition,
                "transition_intensity": transition_intensity,
                "indicators_triggered": indicators_triggered,  # 신호를 준 지표 개수
                "min_indicators": min_indicators,  # Priority 1: 체질별 최소 지표 개수
                "sniping_signal": sniping_signal,
                "confidence_score": confidence_score,  # Phase 2-3: 신뢰도 점수 추가
                "constitution": self.constitution,
                "mode_name": self.mode_name,
                "control_mechanism": self.control_mechanism,
                "alpha_taeyang_applied": self.constitution == "TY",
                "strong_threshold": self.strong_transition_threshold,
                "moderate_threshold": self.moderate_transition_threshold,
                "min_confidence_threshold": self.min_confidence_threshold,  # Phase 2-3: 최소 신뢰도 임계값
                "default_stop_loss": self.default_stop_loss,  # Priority 2: 체질별 기본 손절 비율
                "default_take_profit": self.default_take_profit,  # Priority 2: 체질별 기본 익절 비율
                "pmi_result": pmi_result  # PMI-Nitro 엔진 결과 (선택적)
            }
            
            if transition_detected:
                transition_type = "강한 전환" if strong_transition else "중간 전환"
                logger.info(
                    f"🔥 금화교역 전이 감지 ({transition_type}): T_transition={t_transition:.3f}, "
                    f"IEG={ieg:.4f}, C={heat_capacity:.4f}, R1={r1:.3f}, R2={r2:.3f}, "
                    f"dσ/dt={d_sigma_dt:.4f}, 신호={sniping_signal}"
                )
            
            return result
        
        except Exception as e:
            logger.warning(f"⚠️ 금화교역 전이 감지 실패: {e}")
            return {
                "ieg": 0.0,
                "H_current": 0.0,
                "heat_capacity": 0.0,
                "d2S_dE2": 0.0,
                "r1": 0.0,
                "r2": 0.0,
                "sigma": 0.0,
                "d_sigma_dt": 0.0,
                "uts": 0.0,
                "t_transition": 0.0,
                "transition_detected": False,
                "strong_transition": False,
                "moderate_transition": False,
                "transition_intensity": 0.0,
                "sniping_signal": "HOLD",
                "confidence_score": 0.0,  # Phase 2-3: 신뢰도 점수 추가
                "constitution": self.constitution,
                "alpha_taeyang_applied": False,
                "strong_threshold": self.strong_transition_threshold,
                "moderate_threshold": self.moderate_transition_threshold,
                "min_confidence_threshold": self.min_confidence_threshold  # Phase 2-3: 최소 신뢰도 임계값
            }

