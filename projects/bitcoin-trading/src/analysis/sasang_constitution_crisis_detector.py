#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사상체질 병증 기반 위기 감지 알고리즘 (통합)

목적: 4가지 사상체질(태양인, 태음인, 소양인, 소음인)의 병증을 모두 통합하여
      거시경제 현상에 대입하여 시장 위기를 감지

작성일: 2026-01-12
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

# 태양인 전용 감지기 (상세도 보완)
try:
    from taeyang_crisis_detector import TaeyangCrisisDetector
    TAEYANG_DETECTOR_AVAILABLE = True
except ImportError:
    TAEYANG_DETECTOR_AVAILABLE = False
    logger.warning("TaeyangCrisisDetector를 사용할 수 없습니다. 기본 구현을 사용합니다.")

logger = logging.getLogger(__name__)

# Divine Centroid (Project Logos)
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}


class SasangConstitutionCrisisDetector:
    """
    사상체질 병증 기반 위기 감지 알고리즘 (통합)
    
    핵심 원리:
    - 태양인: 상한(傷寒) - 표병, 해역증(解㑊證), 열격증(噎膈證)
    - 태음인: 배추표병(背聚表病) - 표리병, 위완수한표한(胃脘수한表寒)
    - 소양인: 망음증(亡陰證) - 리병, 등척소장병(等脊小腸病)
    - 소음인: 망양증(亡陽證) - 리병
    
    각 체질의 병증을 경제 현상에 대입하여 종합적으로 위기 감지
    """
    
    def __init__(self):
        """초기화"""
        # 태양인 전용 감지기 초기화 (상세도 보완)
        if TAEYANG_DETECTOR_AVAILABLE:
            self.taeyang_detector = TaeyangCrisisDetector()
        else:
            self.taeyang_detector = None
        
        # 체질별 병증 임계값
        self.pathology_thresholds = {
            "태양인": {
                "상한": 0.7,  # 표병 (외부 충격)
                "해역증": 0.6,  # 상열(上熱) 증상
                "열격증": 0.6,  # 열격(噎膈) 증상
            },
            "태음인": {
                "배추표병": 0.7,  # 표리병 (복합적 문제)
                "위완수한표한": 0.6,  # 위장 중심, 표면 한랭
            },
            "소양인": {
                "망음증": 0.7,  # 리병 (내부 문제)
                "등척소장병": 0.6,  # 척추 소장 관련
            },
            "소음인": {
                "망양증": 0.7,  # 리병 (양기 소실)
            },
        }
        
        # 병리 수준 (ICD A-Code)
        self.pathology_levels = {
            "SL": (0.7, 1.0),  # Surface Level (표면적 증상)
            "IL": (0.3, 0.7),  # Intermediate Level (복합적 문제)
            "DL": (0.0, 0.3),  # Deep Level (근본적 문제)
        }
    
    def detect_taeyang_pathology(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        태양인 병증 감지
        
        병증:
        - 상한(傷寒): 표병 (외부 충격)
        - 해역증(解㑊證): 상열(上熱) 증상
        - 열격증(噎膈證): 열격(噎膈) 증상
        
        경제 현상 대입:
        - 상한: 외부 충격 (전쟁, 지정학적 갈등, 급격한 정책 변화)
        - 해역증: 상열 (자산 가격 급등, 과열 버블)
        - 열격증: 열격 (시장 교란, 거래 중단)
        
        상세도 보완 (2026-01-13):
        - TaeyangCrisisDetector 사용 (소음인 수준의 상세도)
        - 각 증상별 상세 메서드 활용
        """
        # 태양인 전용 감지기 사용 (상세도 보완)
        if self.taeyang_detector:
            return self.taeyang_detector.diagnose_taeyang_pathology(market_data)
        
        # Fallback: 기본 구현 (이전 방식)
        # 상한(傷寒) 감지: 외부 충격
        external_shock_score = (
            market_data.get("geopolitical_risk", 0.0) * 0.4 +
            market_data.get("policy_change_volatility", 0.0) * 0.3 +
            market_data.get("war_risk_index", 0.0) * 0.3
        )
        
        # 해역증(解㑊證) 감지: 상열(上熱)
        upper_heat_score = (
            market_data.get("asset_price_inflation", 0.0) * 0.4 +
            market_data.get("market_overheating", 0.0) * 0.3 +
            market_data.get("speculation_index", 0.0) * 0.3
        )
        
        # 열격증(噎膈證) 감지: 열격(噎膈)
        obstruction_score = (
            market_data.get("market_disruption", 0.0) * 0.4 +
            market_data.get("trading_halt_frequency", 0.0) * 0.3 +
            market_data.get("liquidity_crisis", 0.0) * 0.3
        )
        
        # 종합 점수
        taeyang_score = (
            external_shock_score * 0.4 +
            upper_heat_score * 0.3 +
            obstruction_score * 0.3
        )
        
        return {
            "constitution": "태양인",
            "pathology": "상한/해역증/열격증",
            "score": taeyang_score,
            "symptoms": {
                "상한": external_shock_score,
                "해역증": upper_heat_score,
                "열격증": obstruction_score,
            },
            "detected": taeyang_score >= self.pathology_thresholds["태양인"]["상한"],
            "interpretation": "태양인 병증: 외부 충격 + 상열 + 시장 교란",
        }
    
    def detect_taeeum_pathology(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        태음인 병증 감지
        
        병증:
        - 배추표병(背聚表病): 표리병 (복합적 문제)
        - 위완수한표한(胃脘수한表寒): 위장 중심, 표면 한랭
        
        경제 현상 대입:
        - 배추표병: 표리 동시 문제 (자산 버블 + 실물 경제 침체)
        - 위완수한표한: 위장(실물 경제) 수한 + 표면(자산 시장) 한랭
        """
        # 배추표병(背聚表病) 감지: 표리 동시 문제
        surface_internal_score = (
            market_data.get("asset_bubble_index", 0.0) * 0.3 +
            market_data.get("real_economy_decline", 0.0) * 0.3 +
            market_data.get("stagflation_index", 0.0) * 0.4
        )
        
        # 위완수한표한(胃脘수한表寒) 감지
        stomach_cold_score = (
            market_data.get("real_economy_index", 0.0) * 0.4 +  # 위장(실물) 수한
            (1.0 - market_data.get("asset_market_heat", 0.0)) * 0.3 +  # 표면 한랭
            market_data.get("wealth_polarization", 0.0) * 0.3
        )
        
        # 종합 점수
        taeeum_score = (
            surface_internal_score * 0.6 +
            stomach_cold_score * 0.4
        )
        
        return {
            "constitution": "태음인",
            "pathology": "배추표병/위완수한표한",
            "score": taeeum_score,
            "symptoms": {
                "배추표병": surface_internal_score,
                "위완수한표한": stomach_cold_score,
            },
            "detected": taeeum_score >= self.pathology_thresholds["태음인"]["배추표병"],
            "interpretation": "태음인 병증: 표리 동시 문제 + 실물 경제 수한 + 자산 시장 한랭",
        }
    
    def detect_soyang_pathology(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        소양인 병증 감지
        
        병증:
        - 망음증(亡陰證): 리병 (음기 소실)
        - 등척소장병(等脊小腸病): 척추 소장 관련
        
        경제 현상 대입:
        - 망음증: 음기 소실 (유동성 고갈, 신용 위축)
        - 등척소장병: 척추(기반 구조) + 소장(소화/흡수) 문제
        """
        # 망음증(亡陰證) 감지: 음기 소실
        yin_loss_score = (
            (1.0 - market_data.get("liquidity_index", 0.0)) * 0.4 +  # 유동성 고갈
            market_data.get("credit_crunch", 0.0) * 0.3 +  # 신용 위축
            market_data.get("deflation_risk", 0.0) * 0.3  # 디플레이션 위험
        )
        
        # 등척소장병(等脊小腸病) 감지: 기반 구조 + 소화 문제
        spine_intestine_score = (
            market_data.get("infrastructure_crisis", 0.0) * 0.4 +  # 척추(기반 구조)
            market_data.get("supply_chain_disruption", 0.0) * 0.3 +  # 소장(소화/흡수)
            market_data.get("distribution_crisis", 0.0) * 0.3
        )
        
        # 종합 점수
        soyang_score = (
            yin_loss_score * 0.6 +
            spine_intestine_score * 0.4
        )
        
        return {
            "constitution": "소양인",
            "pathology": "망음증/등척소장병",
            "score": soyang_score,
            "symptoms": {
                "망음증": yin_loss_score,
                "등척소장병": spine_intestine_score,
            },
            "detected": soyang_score >= self.pathology_thresholds["소양인"]["망음증"],
            "interpretation": "소양인 병증: 음기 소실 + 기반 구조 + 공급망 문제",
        }
    
    def detect_soeum_pathology(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        소음인 병증 감지 (기존 망양병)
        
        병증:
        - 망양증(亡陽證): 리병 (양기 소실)
        
        경제 현상 대입:
        - 망양증: 양기 소실 (진짜 양기 소실)
        """
        # 땀(汗) 증상: 유동성 폭주
        sweat_score = (
            market_data.get("liquidity_index", 0.0) * 0.4 +
            min(market_data.get("money_supply_growth", 0.0) / 0.2, 1.0) * 0.3 +
            min(market_data.get("asset_price_inflation", 0.0) / 0.3, 1.0) * 0.3
        )
        
        # 수족냉증(手足冷): 실물 경제 동결
        cold_limbs_score = (
            (1.0 - market_data.get("real_economy_index", 0.0)) * 0.3 +
            market_data.get("unemployment_rate", 0.0) * 0.3 +
            (1.0 - market_data.get("small_business_index", 0.0)) * 0.2 +
            max(0.0, -market_data.get("gdp_growth", 0.0) / 0.05) * 0.2
        )
        
        # 심계항진(心悸亢進): 대중의 공포
        palpitation_score = (
            market_data.get("vix_index", 0.0) * 0.4 +
            min(market_data.get("market_volatility", 0.0) / 0.5, 1.0) * 0.3 +
            (1.0 - market_data.get("fear_greed_index", 0.0)) * 0.3
        )
        
        # 망양증 종합 점수
        mang_yang_score = (
            sweat_score * 0.3 +  # 가짜 열
            cold_limbs_score * 0.5 +  # 진짜 양기 소실 (가장 중요)
            palpitation_score * 0.2  # 공포
        )
        
        return {
            "constitution": "소음인",
            "pathology": "망양증",
            "score": mang_yang_score,
            "symptoms": {
                "땀": sweat_score,
                "수족냉증": cold_limbs_score,
                "심계항진": palpitation_score,
            },
            "detected": mang_yang_score >= self.pathology_thresholds["소음인"]["망양증"],
            "interpretation": "소음인 병증: 가짜 열 + 진짜 양기 소실 + 공포",
        }
    
    def diagnose_all_constitutions(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        모든 체질의 병증 진단 (통합)
        
        Args:
            market_data: 시장 데이터
        
        Returns:
            모든 체질의 병증 진단 결과
        """
        # 각 체질별 병증 진단
        taeyang = self.detect_taeyang_pathology(market_data)
        taeeum = self.detect_taeeum_pathology(market_data)
        soyang = self.detect_soyang_pathology(market_data)
        soeum = self.detect_soeum_pathology(market_data)
        
        # 종합 위험도 계산
        all_scores = [
            taeyang["score"],
            taeeum["score"],
            soyang["score"],
            soeum["score"]
        ]
        
        max_score = max(all_scores)
        max_constitution = None
        if max_score == taeyang["score"]:
            max_constitution = "태양인"
        elif max_score == taeeum["score"]:
            max_constitution = "태음인"
        elif max_score == soyang["score"]:
            max_constitution = "소양인"
        else:
            max_constitution = "소음인"
        
        # 평균 위험도
        avg_score = np.mean(all_scores)
        
        # 병리 수준 판정
        if max_score >= 0.7:
            pathology_level = "SL"  # Surface Level
        elif max_score >= 0.3:
            pathology_level = "IL"  # Intermediate Level
        else:
            pathology_level = "DL"  # Deep Level
        
        return {
            "diagnosis": {
                "태양인": taeyang,
                "태음인": taeeum,
                "소양인": soyang,
                "소음인": soeum,
            },
            "max_risk_constitution": max_constitution,
            "max_risk_score": max_score,
            "average_risk_score": avg_score,
            "pathology_level": pathology_level,
            "crisis_level": "critical" if pathology_level == "DL" else "warning" if pathology_level == "IL" else "normal",
            "recommendation": self._generate_integrated_recommendation(
                taeyang, taeeum, soyang, soeum, max_constitution
            ),
        }
    
    def _generate_integrated_recommendation(
        self,
        taeyang: Dict[str, Any],
        taeeum: Dict[str, Any],
        soyang: Dict[str, Any],
        soeum: Dict[str, Any],
        max_constitution: str
    ) -> str:
        """통합 권장사항 생성"""
        recommendations = []
        
        if taeyang["detected"]:
            recommendations.append("⚠️ 태양인 병증: 외부 충격 대비, 방어적 포지션")
        
        if taeeum["detected"]:
            recommendations.append("⚠️ 태음인 병증: 스태그플레이션 대비, 자산 이동")
        
        if soyang["detected"]:
            recommendations.append("⚠️ 소양인 병증: 유동성 고갈 대비, 현금 보유")
        
        if soeum["detected"]:
            recommendations.append("⚠️ 소음인 병증: 망양병 위급, 비트코인으로 피신")
        
        if max_constitution == "소음인" and soeum["score"] >= 0.7:
            recommendations.append("🚨 최우선: 소음인 망양병 위급, 긴급 매도!")
        
        if not recommendations:
            return "✅ 정상 범위: 모든 체질 병증 정상"
        
        return " | ".join(recommendations)
    
    def calculate_4d_vector_from_all_pathologies(
        self,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        모든 체질 병증 진단 결과를 4D 위상 벡터로 변환
        
        S (Spirit): 태양인 상열 + 소음인 가짜 열
        L (Logic): 태음인 표리병 + 소양인 기반 구조
        K (Knowledge): 태양인 외부 충격 + 소양인 음기 소실
        M (Material): 소음인 진짜 양기 소실
        """
        taeyang = diagnosis["diagnosis"]["태양인"]
        taeeum = diagnosis["diagnosis"]["태음인"]
        soyang = diagnosis["diagnosis"]["소양인"]
        soeum = diagnosis["diagnosis"]["소음인"]
        
        vector_4d = {
            "S": (
                taeyang["symptoms"]["해역증"] * 0.3 +  # 태양인 상열
                soeum["symptoms"]["땀"] * 0.3 +  # 소음인 가짜 열
                0.2  # 기본값
            ),
            "L": (
                taeeum["symptoms"]["배추표병"] * 0.4 +  # 태음인 표리병
                soyang["symptoms"]["등척소장병"] * 0.3 +  # 소양인 기반 구조
                0.2  # 기본값
            ),
            "K": (
                taeyang["symptoms"]["상한"] * 0.3 +  # 태양인 외부 충격
                soyang["symptoms"]["망음증"] * 0.3 +  # 소양인 음기 소실
                0.2  # 기본값
            ),
            "M": (
                soeum["symptoms"]["수족냉증"] * 0.5 +  # 소음인 진짜 양기 소실 (가장 중요)
                0.3  # 기본값
            ),
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
        위기 신호 감지 (통합: 모든 체질)
        
        Args:
            market_data: 시장 데이터
            current_price: 현재 가격
            price_history: 가격 이력 (선택적)
        
        Returns:
            위기 신호 (통합)
        """
        # 모든 체질 병증 진단
        diagnosis = self.diagnose_all_constitutions(market_data)
        
        # 4D 위상 벡터 계산
        vector_4d = self.calculate_4d_vector_from_all_pathologies(diagnosis)
        
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
        
        # 소음인 망양병 위급 시 특별 신호
        soeum = diagnosis["diagnosis"]["소음인"]
        if soeum["detected"] and soeum["score"] >= 0.8:
            signal = "EMERGENCY_SELL"  # 긴급 매도
        
        return {
            "signal": signal,
            "diagnosis": diagnosis,
            "vector_4d": vector_4d,
            "distance_to_centroid": distance,
            "confidence": diagnosis["max_risk_score"],
            "max_risk_constitution": diagnosis["max_risk_constitution"],
            "timestamp": datetime.now().isoformat(),
        }

