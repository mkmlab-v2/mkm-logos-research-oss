#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ PMI-Nitro 융합 매매 엔진 (Prophetic-Momentum Index Nitro Engine)

우주의 본질적 주기성(Biblical & Myeongri)과 비선형 카오스 이론(Entropy & Duffing) 융합
화기운(Fire Energy) 감지를 '예지적 수준'으로 격상

작성일: 2026-01-23
목적: 금융 시장의 무작위성(Aleatoric Uncertainty) 너머 구조적 필연성(Epistemic Certainty) 포착
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime, timedelta
from scipy.integrate import odeint
from scipy.signal import find_peaks
import logging
import math

logger = logging.getLogger(__name__)


class PMINitroEngine:
    """
    🏛️ PMI-Nitro 융합 매매 엔진
    
    핵심 기능:
    1. Improved Permutation Entropy (IPE) - 정보 엔트로피 기반 화기운 감지
    2. Duffing Oscillator - 비선형 카오스 기반 위상 전이 감지
    3. Prophetic-Momentum Index (PMI) - 성경/명리 주기성 통합 지표
    4. 사상체질별 위험 관리 (SLPT) - 체질별 손절/익절 전략
    """
    
    def __init__(
        self,
        constitution: str = "SY",
        prophetic_year_days: int = 360,
        daewun_threshold: int = 3600,  # 10년 대운 (3600일)
        enable_prophetic_cycles: bool = True
    ):
        """
        Args:
            constitution: 체질 (TY: 태양인, TE: 태음인, SY: 소양인, SE: 소음인)
            prophetic_year_days: 예언적 년 일수 (기본값: 360일)
            daewun_threshold: 대운 임계점 (기본값: 3600일 = 10년)
            enable_prophetic_cycles: 성경/명리 주기성 활성화 여부
        """
        self.constitution = constitution
        self.prophetic_year_days = prophetic_year_days
        self.daewun_threshold = daewun_threshold
        self.enable_prophetic_cycles = enable_prophetic_cycles
        
        # IPE 파라미터 (Monster Artifact: 0.45 하향 조정)
        self.ipe_m = 3  # 패턴 길이
        self.ipe_delta = 0.01  # 양자화 간격
        self.ipe_threshold = 0.45  # 화기 임계값 (0.45: 선제적 퇴각 트리거)
        
        # Duffing Oscillator 파라미터
        self.duffing_mu = 0.5  # 감쇠 계수
        self.duffing_a = 1.0  # 선형 복원력 계수
        self.duffing_b = 1.0  # 비선형 복원력 계수
        self.duffing_omega = 1.2  # 외력 주파수
        
        # 성경적 하모닉스 주기
        self.prophetic_cycles = {
            "1260": 1260,  # 추세 지속 주기 (3.5년)
            "2520": 2520   # 완전한 회전 주기 (7년)
        }
        
        # 명리적 임계점 (대운)
        self.myungri_cycles = {
            "daewun": daewun_threshold,  # 10년 대운
            "sub_cycle": 360  # 1년 소주기
        }
        
        # 사상체질별 위험 관리 설정
        self.constitution_strategies = self._init_constitution_strategies()
        
        logger.info(f"✅ PMI-Nitro 엔진 초기화 완료 (체질: {constitution})")
    
    def _init_constitution_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        사상체질별 위험 관리 전략 초기화
        
        Returns:
            체질별 전략 딕셔너리
        """
        return {
            "SY": {  # 소양인 (도파민적 공격형)
                "stop_loss_type": "trailing_tight",  # 타이트한 트레일링 스탑
                "take_profit_trigger": "pmi_breakout_1",  # PMI 1단계 돌파 시 즉시 실현
                "risk_multiplier": 1.2,
                "momentum_focus": True
            },
            "TE": {  # 태음인 (GABA적 안정형)
                "stop_loss_type": "wide_volatility",  # 넓은 변동성 수용
                "take_profit_trigger": "2520_cycle_complete",  # 2520 주기 완성 시 매도
                "risk_multiplier": 0.9,
                "stability_focus": True
            },
            "SE": {  # 소음인 (세로토닌적 방어형)
                "stop_loss_type": "entropy_reversal",  # EG(엔트로피) 반전 시 즉시 탈출
                "take_profit_trigger": "pmi_spike_partial",  # PMI 스파이크 시 분할 익절
                "risk_multiplier": 0.7,
                "defense_focus": True
            },
            "TY": {  # 태양인 (아세틸콜린적 비전형)
                "stop_loss_type": "4d_core_threshold",  # 4D-Core 임계점 기준 스탑
                "take_profit_trigger": "macro_inflection",  # 거시적 변곡점 매도
                "risk_multiplier": 1.1,
                "vision_focus": True
            }
        }
    
    def calculate_ipe(
        self,
        signal: np.ndarray,
        m: Optional[int] = None,
        delta: Optional[float] = None
    ) -> float:
        """
        Improved Permutation Entropy (IPE) 계산
        
        기존 PE는 가격의 진폭을 무시하지만, IPE는 진폭 정보를 양자화하여
        '질서 속의 무질서'를 더 정확히 잡아냅니다.
        
        Args:
            signal: 가격 신호 배열
            m: 패턴 길이 (기본값: self.ipe_m)
            delta: 양자화 간격 (기본값: self.ipe_delta)
        
        Returns:
            IPE 값 (0~1 범위, 높을수록 비주기적 카오스)
        """
        if m is None:
            m = self.ipe_m
        if delta is None:
            delta = self.ipe_delta
        
        n = len(signal)
        if n < m:
            logger.warning(f"⚠️ 신호 길이({n})가 패턴 길이({m})보다 짧습니다")
            return 0.0
        
        symbol_patterns = []
        for j in range(n - m + 1):
            vec = signal[j:j+m]
            # 진폭 정보를 포함한 양자화 (Symbolization)
            symbolic_vec = [np.floor((v - vec[0]) / delta) for v in vec]
            symbol_patterns.append(tuple(symbolic_vec))
        
        if len(symbol_patterns) == 0:
            return 0.0
        
        # 고유 패턴과 빈도 계산
        unique, counts = np.unique(symbol_patterns, axis=0, return_counts=True)
        probs = counts / len(symbol_patterns)
        
        # 엔트로피 계산 (0으로 나누기 방지)
        probs = probs[probs > 0]
        if len(probs) == 0:
            return 0.0
        
        ipe = -np.sum(probs * np.log(probs))
        
        # 정규화 (최대 엔트로피 = log(m!))
        max_entropy = math.log(math.factorial(m))
        if max_entropy > 0:
            ipe_normalized = ipe / max_entropy
        else:
            ipe_normalized = 0.0
        
        return float(ipe_normalized)
    
    def fire_energy_detector(
        self,
        market_price: np.ndarray,
        mu: Optional[float] = None,
        a: Optional[float] = None,
        b: Optional[float] = None
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Duffing Oscillator를 이용한 화기운(Fire Energy) 감지
        
        시장 신호가 주입되었을 때, 오실레이터의 출력이 '주기적 상태'에서
        '카오스 상태'로 전이되는 시점이 바로 화기가 극대화되어 폭발하기 직전의 변곡점입니다.
        
        Args:
            market_price: 시장 가격 배열
            mu: 감쇠 계수 (기본값: self.duffing_mu)
            a: 선형 복원력 계수 (기본값: self.duffing_a)
            b: 비선형 복원력 계수 (기본값: self.duffing_b)
        
        Returns:
            (ipe_score, is_fire_energy, metadata) 튜플
            - ipe_score: IPE 점수
            - is_fire_energy: 화기운 감지 여부 (IPE > 0.15)
            - metadata: 추가 메타데이터
        """
        if mu is None:
            mu = self.duffing_mu
        if a is None:
            a = self.duffing_a
        if b is None:
            b = self.duffing_b
        
        # 시간 배열 생성
        t = np.linspace(0, 100, len(market_price))
        
        # 시장 신호 정규화
        market_signal = (market_price - np.mean(market_price)) / (np.std(market_price) + 1e-10)
        
        def duffing_oscillator(x_v, t_val, s_t):
            """
            Duffing Oscillator 미분 방정식
            
            dx/dt = v
            dv/dt = -μv - ax - bx³ + 0.5cos(ωt) + s(t)
            """
            x, v = x_v
            # 시장 신호 s_t를 외력으로 주입
            signal_value = s_t[int(t_val % len(s_t))] if len(s_t) > 0 else 0.0
            return [
                v,
                -mu * v - a * x - b * x**3 + 0.5 * np.cos(self.duffing_omega * t_val) + signal_value
            ]
        
        try:
            # 초기 조건: [위치, 속도]
            initial_condition = [0.1, 0.0]
            
            # ODE 해석
            sol = odeint(duffing_oscillator, initial_condition, t, args=(market_signal,))
            
            # IPE 계산 (위치 신호 사용)
            ipe_score = self.calculate_ipe(sol[:, 0])
            
            # 화기운 감지 여부
            is_fire_energy = ipe_score > self.ipe_threshold
            
            # 메타데이터
            metadata = {
                "ipe_score": float(ipe_score),
                "ipe_threshold": self.ipe_threshold,
                "oscillator_position": float(sol[-1, 0]),
                "oscillator_velocity": float(sol[-1, 1]),
                "phase_transition": is_fire_energy,
                "signal_std": float(np.std(market_signal))
            }
            
            return (ipe_score, is_fire_energy, metadata)
        
        except Exception as e:
            logger.error(f"❌ Duffing Oscillator 계산 실패: {e}")
            return (0.0, False, {"error": str(e)})
    
    def calculate_prophetic_cycles(
        self,
        current_date: datetime,
        reference_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        성경적 하모닉스 주기 계산
        
        Args:
            current_date: 현재 날짜
            reference_date: 기준 날짜 (None이면 2013년 고점 사용)
        
        Returns:
            주기별 위상 딕셔너리
        """
        if reference_date is None:
            # 2013년 비트코인 고점 (대략 2013-12-04)
            reference_date = datetime(2013, 12, 4)
        
        days_elapsed = (current_date - reference_date).days
        
        cycles = {}
        for name, period in self.prophetic_cycles.items():
            # 주기 위상 계산 (0~1 범위)
            phase = (days_elapsed % period) / period
            cycles[f"prophetic_{name}"] = phase
            cycles[f"prophetic_{name}_days"] = days_elapsed % period
        
        return cycles
    
    def calculate_myungri_threshold(
        self,
        current_date: datetime,
        reference_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        명리적 임계점 (대운) 계산
        
        Args:
            current_date: 현재 날짜
            reference_date: 기준 날짜
        
        Returns:
            명리적 임계점 정보
        """
        if reference_date is None:
            reference_date = datetime(2013, 12, 4)
        
        days_elapsed = (current_date - reference_date).days
        
        # 대운 주기 계산
        daewun_phase = (days_elapsed % self.daewun_threshold) / self.daewun_threshold
        daewun_remaining = self.daewun_threshold - (days_elapsed % self.daewun_threshold)
        
        # 교운기(Gyogyeun) 감지: 대운 말기 (90% 이상)
        is_gyogyeun = daewun_phase >= 0.9
        
        return {
            "daewun_phase": daewun_phase,
            "daewun_remaining_days": daewun_remaining,
            "is_gyogyeun": is_gyogyeun,
            "sub_cycle_phase": (days_elapsed % self.myungri_cycles["sub_cycle"]) / self.myungri_cycles["sub_cycle"]
        }
    
    def calculate_pmi(
        self,
        price_series: pd.Series,
        volume_series: Optional[pd.Series] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Prophetic-Momentum Index (PMI) 계산
        
        고주파 카오스 에너지(Fire)와 저주파 역사적 주기(Prophecy)를 결합한
        최종 사격 통제 장치입니다.
        
        PMI = w1 * HC + w2 * EG + w3 * VAM
        
        where:
        - HC (Harmonic Cycle): 성경/명리 주기의 정현파 합산
        - EG (Entropy Gradient): IPE의 1차 미분값
        - VAM (Volatility-Adjusted Momentum): 시장의 기(Qi, Volatility)로 정규화된 가격 속도
        
        Args:
            price_series: 가격 시리즈
            volume_series: 거래량 시리즈 (선택적)
            current_date: 현재 날짜 (None이면 마지막 날짜 사용)
        
        Returns:
            PMI 지표 및 메타데이터
        """
        if current_date is None:
            current_date = datetime.now()
        
        # 1. HC (Harmonic Cycle) 계산
        prophetic_cycles = self.calculate_prophetic_cycles(current_date)
        myungri_threshold = self.calculate_myungri_threshold(current_date)
        
        # 정현파 합산
        hc_1260 = np.sin(2 * np.pi * prophetic_cycles["prophetic_1260"])
        hc_2520 = np.sin(2 * np.pi * prophetic_cycles["prophetic_2520"])
        hc_daewun = np.sin(2 * np.pi * myungri_threshold["daewun_phase"])
        
        hc = (hc_1260 + hc_2520 + hc_daewun) / 3.0
        
        # 2. EG (Entropy Gradient) 계산
        # IPE를 여러 윈도우로 계산하여 기울기 추정
        window_size = min(50, len(price_series) // 4)
        if window_size < 10:
            eg = 0.0
            ipe_current = 0.0
        else:
            # 최근 윈도우 IPE
            recent_prices = price_series.iloc[-window_size:].values
            ipe_current, _, _ = self.fire_energy_detector(recent_prices)
            
            # 이전 윈도우 IPE
            if len(price_series) >= window_size * 2:
                prev_prices = price_series.iloc[-window_size*2:-window_size].values
                ipe_prev, _, _ = self.fire_energy_detector(prev_prices)
                eg = ipe_current - ipe_prev
            else:
                eg = 0.0
        
        # 3. VAM (Volatility-Adjusted Momentum) 계산
        returns = price_series.pct_change().dropna()
        if len(returns) < 20:
            vam = 0.0
            volatility = 0.0
        else:
            # 최근 20일 모멘텀
            momentum = returns.iloc[-20:].mean()
            volatility = returns.iloc[-20:].std()
            
            # 변동성으로 정규화
            if volatility > 0:
                vam = momentum / volatility
            else:
                vam = 0.0
        
        # 4. PMI 가중치 (Monster Artifact: K->M 붕괴 감시형)
        w_hc = 0.15  # 하모닉 사이클 가중치 (고점에서 축소)
        w_eg = 0.55  # 엔트로피 기울기 가중치 (메인 센서)
        w_vam = 0.30  # 변동성 조정 모멘텀 가중치 (Duffing 추적)
        
        # 5. PMI 계산
        pmi = w_hc * hc + w_eg * eg + w_vam * vam
        
        # 6. 화기운 감지
        is_fire_energy = ipe_current > self.ipe_threshold
        
        # 7. 사상체질별 신호 해석
        constitution_strategy = self.constitution_strategies.get(self.constitution, {})
        
        return {
            "pmi": float(pmi),
            "hc": float(hc),
            "eg": float(eg),
            "vam": float(vam),
            "ipe_current": float(ipe_current),
            "is_fire_energy": is_fire_energy,
            "volatility": float(volatility),
            "momentum": float(returns.iloc[-20:].mean()) if len(returns) >= 20 else 0.0,
            "prophetic_cycles": prophetic_cycles,
            "myungri_threshold": myungri_threshold,
            "constitution_strategy": constitution_strategy,
            "signal": self._interpret_pmi_signal(pmi, is_fire_energy, constitution_strategy),
            "timestamp": current_date.isoformat()
        }
    
    def _interpret_pmi_signal(
        self,
        pmi: float,
        is_fire_energy: bool,
        constitution_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PMI 신호 해석 (사상체질별 v7.0 캘리브레이션)
        
        Args:
            pmi: PMI 값
            is_fire_energy: 화기운 감지 여부
            constitution_strategy: 체질별 전략
        
        Returns:
            신호 해석 결과 (신뢰도 1.0 형용모순 제거)
        """
        # 1. 시변성 엔트로피(IPE) 기반 신뢰도 하락 가중치 계산
        # 엔트로피가 극단적으로 높으면(카오스) 신뢰도는 급락해야 함
        # - s_factor: 데이터 신선도/안정성 계수
        ipe_current = getattr(self, 'ipe_current', 0.5) # 마지막 계산값 참조
        data_stability = max(0.1, 1.0 - ipe_current)
        
        signal = {
            "action": "HOLD",
            "confidence": 0.0,
            "risk_level": "MEDIUM",
            "recommendation": ""
        }
        
        # 2. 화기운(Fire Energy) 감지 시: SELL/Short 대응 (Lot's Escape)
        if is_fire_energy:
            signal["action"] = "SELL"
            # 최대로 높아도 0.92를 넘지 않음 (환각 방지)
            signal["confidence"] = min(0.92, 0.85 + (abs(pmi) * 0.1))
            signal["risk_level"] = "HIGH"
            signal["recommendation"] = "🔥 LOT'S ESCAPE: 소돔의 붕괴(Chaos) 감지, 뒤를 돌아보지 말고 즉시 전량 청산"
            return signal
        
        # 3. PMI 기반 신호 (0.25 평형 이탈도 기반)
        abs_pmi = abs(pmi)
        
        if pmi > 0.45:
            signal["action"] = "BUY"
            # 신뢰도 동적 계산: PMI 강도와 데이터 안정성의 곱
            signal["confidence"] = min(0.88, abs_pmi * data_stability * 1.5)
            signal["risk_level"] = "MEDIUM"
            signal["recommendation"] = f"🔥 PMI 상승(+{pmi:.2f}): 상승 하모닉스 진입"
        elif pmi < -0.45:
            signal["action"] = "SELL"
            signal["confidence"] = min(0.88, abs_pmi * data_stability * 1.5)
            signal["risk_level"] = "MEDIUM"
            signal["recommendation"] = f"❄️ PMI 하락({pmi:.2f}): 하락 사이클 진입"
        else:
            signal["action"] = "HOLD"
            # 평형 상태에서는 신뢰도가 낮음 (불확실성)
            signal["confidence"] = min(0.45, 0.2 + (data_stability * 0.1))
            signal["risk_level"] = "LOW"
            signal["recommendation"] = "⚖️ PMI 평형(Logos Hub): 방향성 탐색 중, 관망"
        
        # 4. 체질별 가용성 보정 (SLPT)
        current_confidence = float(signal["confidence"])
        if constitution_strategy.get("defense_focus", False):  # SE(소음인): 의심이 많음
            current_confidence *= 0.85
        elif constitution_strategy.get("momentum_focus", False):  # SY(소양인): 직관을 믿음
            current_confidence = min(0.91, current_confidence * 1.15)
        
        signal["confidence"] = current_confidence
        
        # 5. 최종 신뢰도 0.25 이하 시 'UNVERIFIED' 강제 필터링
        if current_confidence < 0.25:
             signal["recommendation"] = "[⚠️ UNVERIFIED] " + str(signal["recommendation"])
             signal["confidence"] = round(current_confidence, 3)
        
        return signal
    
    def get_constitution_stop_loss_take_profit(
        self,
        current_price: float,
        entry_price: float,
        pmi_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        사상체질별 손절/익절 가격 계산
        
        Args:
            current_price: 현재 가격
            entry_price: 진입 가격
            pmi_result: PMI 계산 결과
        
        Returns:
            손절/익절 가격 딕셔너리
        """
        strategy = self.constitution_strategies.get(self.constitution, {})
        signal = pmi_result.get("signal", {})
        
        # 기본 손절/익절 비율 (GeumHwaDetector와 동일)
        if self.constitution == "TY":
            base_stop_loss_pct = 0.015  # 1.5%
            base_take_profit_pct = 0.15  # 15.0%
        elif self.constitution == "TE":
            base_stop_loss_pct = 0.03  # 3.0%
            base_take_profit_pct = 0.10  # 10.0%
        elif self.constitution == "SY":
            base_stop_loss_pct = 0.025  # 2.5%
            base_take_profit_pct = 0.08  # 8.0%
        elif self.constitution == "SE":
            base_stop_loss_pct = 0.015  # 1.5%
            base_take_profit_pct = 0.11  # 11.0%
        else:
            base_stop_loss_pct = 0.025  # 기본값
            base_take_profit_pct = 0.10  # 기본값
        
        # PMI 신호에 따른 조정
        if signal.get("action") == "SELL" and signal.get("confidence", 0) > 0.7:
            # 강한 매도 신호: 손절 타이트화
            base_stop_loss_pct *= 0.8
        
        # 손절/익절 가격 계산
        stop_loss_price = entry_price * (1 - base_stop_loss_pct)
        take_profit_price = entry_price * (1 + base_take_profit_pct)
        
        return {
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "stop_loss_pct": base_stop_loss_pct,
            "take_profit_pct": base_take_profit_pct
        }

