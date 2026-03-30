#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
소음인 망양병 위기 감지 알고리즘 (Mang-Yang Crisis Detection Algorithm)

목적: 소음인 망양병(亡陽病)의 병리를 거시경제 현상에 대입하여
      시장의 "가짜 열(Overheating)"과 "진짜 양기 소실(Vitality Loss)"을 구분

작성일: 2026-01-12
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Divine Centroid (Project Logos)
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}


class MangYangCrisisDetector:
    """
    소음인 망양병 위기 감지 알고리즘
    
    핵심 원리:
    - 소음인 망양병: 양기가 소진되어 나타나는 증상
      * 땀(땀) = 유동성 폭주 (가짜 열)
      * 수족냉증 = 실물 경제 동결 (진짜 양기 소실)
      * 심계항진 = 대중의 공포 (VIX 급등)
    
    경제 현상 대입:
    - 겉으로 보이는 화려한 지수 상승 = 가짜 열 (발열/땀)
    - 속에서 빠져나가는 양기 = 본질적 가치 소실
    - 회광반조(回光返照) = 마지막 불꽃 (Super Cycle)
    """
    
    def __init__(self):
        """초기화"""
        # 망양병 증상 임계값
        self.symptoms_thresholds = {
            "sweat": 0.7,  # 땀 (유동성 폭주) 임계값
            "cold_limbs": 0.6,  # 수족냉증 (실물 경제 동결) 임계값
            "palpitation": 0.8,  # 심계항진 (공포) 임계값
        }
        
        # 병리 수준 (ICD A-Code)
        self.pathology_levels = {
            "SL": (0.7, 1.0),  # Surface Level (표면적 증상)
            "IL": (0.3, 0.7),  # Intermediate Level (복합적 문제)
            "DL": (0.0, 0.3),  # Deep Level (근본적 문제, 망양병)
        }
    
    def detect_sweat_symptom(
        self,
        liquidity_index: float,
        money_supply_growth: float,
        asset_price_inflation: float
    ) -> Dict[str, Any]:
        """
        땀 증상 감지 (유동성 폭주)
        
        망양병: 땀이 비 오듯 쏟아짐
        경제: 유동성 폭주, 자산 가격 상승
        
        Args:
            liquidity_index: 유동성 지수 (0.0 ~ 1.0)
            money_supply_growth: 통화 공급 증가율 (연율)
            asset_price_inflation: 자산 가격 인플레이션 (연율)
        
        Returns:
            땀 증상 감지 결과
        """
        # 땀 증상 점수 계산
        sweat_score = (
            liquidity_index * 0.4 +
            min(money_supply_growth / 0.2, 1.0) * 0.3 +  # 20% 증가율 기준
            min(asset_price_inflation / 0.3, 1.0) * 0.3  # 30% 인플레이션 기준
        )
        
        is_sweating = sweat_score >= self.symptoms_thresholds["sweat"]
        
        return {
            "symptom": "sweat",
            "score": sweat_score,
            "detected": is_sweating,
            "severity": "high" if sweat_score >= 0.8 else "medium" if sweat_score >= 0.7 else "low",
            "interpretation": "유동성 폭주로 인한 가짜 열 (발열/땀)" if is_sweating else "정상 범위",
        }
    
    def detect_cold_limbs_symptom(
        self,
        real_economy_index: float,
        unemployment_rate: float,
        small_business_index: float,
        gdp_growth: float
    ) -> Dict[str, Any]:
        """
        수족냉증 감지 (실물 경제 동결)
        
        망양병: 손발이 차가워짐
        경제: 실물 경제 동결, 서민 경제 어려움
        
        Args:
            real_economy_index: 실물 경제 지수 (0.0 ~ 1.0)
            unemployment_rate: 실업률 (0.0 ~ 1.0)
            small_business_index: 자영업 지수 (0.0 ~ 1.0)
            gdp_growth: GDP 성장률 (연율)
        
        Returns:
            수족냉증 감지 결과
        """
        # 수족냉증 점수 계산
        cold_limbs_score = (
            (1.0 - real_economy_index) * 0.3 +
            unemployment_rate * 0.3 +
            (1.0 - small_business_index) * 0.2 +
            max(0.0, -gdp_growth / 0.05) * 0.2  # -5% 성장률 기준
        )
        
        is_cold = cold_limbs_score >= self.symptoms_thresholds["cold_limbs"]
        
        return {
            "symptom": "cold_limbs",
            "score": cold_limbs_score,
            "detected": is_cold,
            "severity": "high" if cold_limbs_score >= 0.7 else "medium" if cold_limbs_score >= 0.6 else "low",
            "interpretation": "실물 경제 동결로 인한 진짜 양기 소실" if is_cold else "정상 범위",
        }
    
    def detect_palpitation_symptom(
        self,
        vix_index: float,
        market_volatility: float,
        fear_greed_index: float
    ) -> Dict[str, Any]:
        """
        심계항진 감지 (대중의 공포)
        
        망양병: 공포감에 떨고 심계항진
        경제: VIX 급등, 시장 변동성 증가
        
        Args:
            vix_index: VIX 지수 (정규화 0.0 ~ 1.0)
            market_volatility: 시장 변동성 (연율)
            fear_greed_index: 공포/탐욕 지수 (0.0 = 극도의 공포, 1.0 = 극도의 탐욕)
        
        Returns:
            심계항진 감지 결과
        """
        # 심계항진 점수 계산
        palpitation_score = (
            vix_index * 0.4 +
            min(market_volatility / 0.5, 1.0) * 0.3 +  # 50% 변동성 기준
            (1.0 - fear_greed_index) * 0.3  # 공포 지수
        )
        
        is_palpitating = palpitation_score >= self.symptoms_thresholds["palpitation"]
        
        return {
            "symptom": "palpitation",
            "score": palpitation_score,
            "detected": is_palpitating,
            "severity": "high" if palpitation_score >= 0.9 else "medium" if palpitation_score >= 0.8 else "low",
            "interpretation": "대중의 공포로 인한 심계항진" if is_palpitating else "정상 범위",
        }
    
    def diagnose_mang_yang_pathology(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        망양병 병리 진단 (종합)
        
        ICD A-Code 체계:
        - SL (Surface Level): 표면적 증상 (가짜 열만)
        - IL (Intermediate Level): 복합적 문제 (가짜 열 + 일부 양기 소실)
        - DL (Deep Level): 근본적 문제 (망양병, 진짜 양기 소실)
        
        Args:
            market_data: 시장 데이터
                - liquidity_index: 유동성 지수
                - money_supply_growth: 통화 공급 증가율
                - asset_price_inflation: 자산 가격 인플레이션
                - real_economy_index: 실물 경제 지수
                - unemployment_rate: 실업률
                - small_business_index: 자영업 지수
                - gdp_growth: GDP 성장률
                - vix_index: VIX 지수
                - market_volatility: 시장 변동성
                - fear_greed_index: 공포/탐욕 지수
        
        Returns:
            망양병 병리 진단 결과
        """
        # 각 증상 감지
        sweat = self.detect_sweat_symptom(
            liquidity_index=market_data.get("liquidity_index", 0.5),
            money_supply_growth=market_data.get("money_supply_growth", 0.1),
            asset_price_inflation=market_data.get("asset_price_inflation", 0.1),
        )
        
        cold_limbs = self.detect_cold_limbs_symptom(
            real_economy_index=market_data.get("real_economy_index", 0.5),
            unemployment_rate=market_data.get("unemployment_rate", 0.05),
            small_business_index=market_data.get("small_business_index", 0.5),
            gdp_growth=market_data.get("gdp_growth", 0.02),
        )
        
        palpitation = self.detect_palpitation_symptom(
            vix_index=market_data.get("vix_index", 0.2),
            market_volatility=market_data.get("market_volatility", 0.2),
            fear_greed_index=market_data.get("fear_greed_index", 0.5),
        )
        
        # 종합 진단
        # 망양병 = 땀(가짜 열) + 수족냉증(진짜 양기 소실) + 심계항진(공포)
        mang_yang_score = (
            sweat["score"] * 0.3 +  # 가짜 열 (30%)
            cold_limbs["score"] * 0.5 +  # 진짜 양기 소실 (50%, 가장 중요)
            palpitation["score"] * 0.2  # 공포 (20%)
        )
        
        # 병리 수준 판정
        if mang_yang_score >= 0.7:
            pathology_level = "SL"  # Surface Level (표면적 증상)
            pathology_description = "가짜 열만 나타남 (발열/땀)"
        elif mang_yang_score >= 0.3:
            pathology_level = "IL"  # Intermediate Level (복합적 문제)
            pathology_description = "가짜 열 + 일부 양기 소실"
        else:
            pathology_level = "DL"  # Deep Level (근본적 문제, 망양병)
            pathology_description = "망양병: 진짜 양기 소실 (위급)"
        
        # 회광반조(回光返照) 감지
        # 가짜 열(땀)이 높은데 진짜 양기(수족냉증)가 소실되는 경우
        is_hui_guang = (
            sweat["detected"] and
            cold_limbs["detected"] and
            sweat["score"] > cold_limbs["score"] * 1.2  # 가짜 열이 진짜 양기보다 20% 이상 높음
        )
        
        return {
            "mang_yang_score": mang_yang_score,
            "pathology_level": pathology_level,
            "pathology_description": pathology_description,
            "symptoms": {
                "sweat": sweat,
                "cold_limbs": cold_limbs,
                "palpitation": palpitation,
            },
            "is_hui_guang": is_hui_guang,  # 회광반조 감지
            "crisis_level": "critical" if pathology_level == "DL" else "warning" if pathology_level == "IL" else "normal",
            "recommendation": self._generate_recommendation(pathology_level, is_hui_guang),
        }
    
    def _generate_recommendation(
        self,
        pathology_level: str,
        is_hui_guang: bool
    ) -> str:
        """권장사항 생성"""
        if pathology_level == "DL":
            if is_hui_guang:
                return "⚠️ 망양병 위급: 회광반조(回光返照) 감지. 가짜 열에 속지 말고 즉시 방어적 포지션으로 전환. 비트코인(디지털 금)으로 피신."
            else:
                return "⚠️ 망양병 위급: 진짜 양기 소실. 방어적 포지션, 현금 비중 확대, 비트코인으로 자산 이동."
        elif pathology_level == "IL":
            return "⚠️ 망양병 중증: 가짜 열 + 일부 양기 소실. 보수적 포지션, 리스크 관리 강화."
        else:
            return "✅ 정상 범위: 가짜 열만 나타남. 공격적 포지션 고려, 0.25 회귀로 탈출 준비."
    
    def calculate_4d_vector_from_mang_yang(
        self,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        망양병 진단 결과를 4D 위상 벡터로 변환
        
        S (Spirit): 가짜 열 (땀 증상)
        L (Logic): 구조적 문제 (수족냉증)
        K (Knowledge): 공포 지수 (심계항진)
        M (Material): 진짜 양기 (1 - 수족냉증)
        """
        sweat_score = diagnosis["symptoms"]["sweat"]["score"]
        cold_limbs_score = diagnosis["symptoms"]["cold_limbs"]["score"]
        palpitation_score = diagnosis["symptoms"]["palpitation"]["score"]
        
        vector_4d = {
            "S": sweat_score,  # 가짜 열
            "L": cold_limbs_score,  # 구조적 문제
            "K": palpitation_score,  # 공포
            "M": 1.0 - cold_limbs_score,  # 진짜 양기 (수족냉증의 역)
        }
        
        # 정규화
        total = sum(vector_4d.values())
        if total > 0:
            vector_4d = {k: v / total for k, v in vector_4d.items()}
        
        return vector_4d
    
    def detect_crisis_signal(
        self,
        market_data: Dict[str, Any],
        current_price: float,
        price_history: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        위기 신호 감지 (종합)
        
        Args:
            market_data: 시장 데이터
            current_price: 현재 가격
            price_history: 가격 이력 (선택적)
        
        Returns:
            위기 신호
        """
        # 망양병 진단
        diagnosis = self.diagnose_mang_yang_pathology(market_data)
        
        # 4D 위상 벡터 계산
        vector_4d = self.calculate_4d_vector_from_mang_yang(diagnosis)
        
        # Divine Centroid와의 거리 계산
        distance = np.sqrt(
            sum((vector_4d[k] - DIVINE_CENTROID[k]) ** 2 for k in ["S", "L", "K", "M"])
        )
        
        # 위기 신호 생성
        signal = "HOLD"
        if diagnosis["crisis_level"] == "critical":
            signal = "SELL"  # 위급: 매도
        elif diagnosis["crisis_level"] == "warning":
            signal = "REDUCE"  # 경고: 포지션 축소
        
        # 회광반조 감지 시 특별 신호
        if diagnosis["is_hui_guang"]:
            signal = "EMERGENCY_SELL"  # 긴급 매도
        
        return {
            "signal": signal,
            "diagnosis": diagnosis,
            "vector_4d": vector_4d,
            "distance_to_centroid": distance,
            "confidence": diagnosis["mang_yang_score"],
            "timestamp": datetime.now().isoformat(),
        }

