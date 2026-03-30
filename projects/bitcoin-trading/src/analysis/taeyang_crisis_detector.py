#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
태양인 병증 위기 감지 알고리즘 (Taeyang Crisis Detection Algorithm)

목적: 태양인 병증(상한, 해역증, 열격증)의 병리를 거시경제 현상에 대입하여
      시장의 "외부 충격", "과열 버블", "시장 교란"을 구분

작성일: 2026-01-13
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


class TaeyangCrisisDetector:
    """
    태양인 병증 위기 감지 알고리즘
    
    핵심 원리:
    - 태양인 병증: 표병(表病) 중심
      * 상한(傷寒): 외부 충격 (전쟁, 지정학적 갈등)
      * 해역증(解㑊證): 상열(上熱) 증상 (자산 가격 급등, 과열 버블)
      * 열격증(噎膈證): 열격(噎膈) 증상 (시장 교란, 거래 중단)
    
    경제 현상 대입:
    - 상한: 외부 충격 (전쟁, 지정학적 갈등, 급격한 정책 변화)
    - 해역증: 상열 (자산 가격 급등, 과열 버블, 투기 열풍)
    - 열격증: 열격 (시장 교란, 거래 중단, 서킷브레이커)
    """
    
    def __init__(self):
        """초기화"""
        # 태양인 병증 증상 임계값
        self.symptoms_thresholds = {
            "sanghan": 0.7,  # 상한 (외부 충격) 임계값
            "hae_yeok": 0.6,  # 해역증 (상열, 과열) 임계값
            "yeol_gyeok": 0.6,  # 열격증 (열격, 거래 중단) 임계값
        }
        
        # 병리 수준 (ICD A-Code)
        self.pathology_levels = {
            "SL": (0.7, 1.0),  # Surface Level (표면적 증상)
            "IL": (0.3, 0.7),  # Intermediate Level (복합적 문제)
            "DL": (0.0, 0.3),  # Deep Level (근본적 문제)
        }
    
    def detect_sanghan_symptom(
        self,
        geopolitical_risk: float,
        policy_change_volatility: float,
        war_risk_index: float
    ) -> Dict[str, Any]:
        """
        상한(傷寒) 증상 감지 (외부 충격)
        
        상한: 표병 (외부 충격)
        경제: 전쟁, 지정학적 갈등, 급격한 정책 변화
        
        Args:
            geopolitical_risk: 지정학적 위험 지수 (0.0 ~ 1.0)
            policy_change_volatility: 정책 변화 변동성 (0.0 ~ 1.0)
            war_risk_index: 전쟁 위험 지수 (0.0 ~ 1.0)
        
        Returns:
            상한 증상 감지 결과
        """
        # 상한 증상 점수 계산
        sanghan_score = (
            geopolitical_risk * 0.4 +
            policy_change_volatility * 0.3 +
            war_risk_index * 0.3
        )
        
        is_sanghan = sanghan_score >= self.symptoms_thresholds["sanghan"]
        
        return {
            "symptom": "sanghan",
            "score": sanghan_score,
            "detected": is_sanghan,
            "severity": "high" if sanghan_score >= 0.8 else "medium" if sanghan_score >= 0.7 else "low",
            "interpretation": "외부 충격으로 인한 표병 (상한)" if is_sanghan else "정상 범위",
            "details": {
                "geopolitical_risk": geopolitical_risk,
                "policy_change_volatility": policy_change_volatility,
                "war_risk_index": war_risk_index
            }
        }
    
    def detect_hae_yeok_symptom(
        self,
        asset_price_inflation: float,
        market_overheating: float,
        speculation_index: float,
        vector_4d: Optional[Dict[str, float]] = None  # S-M 괴리 기반 붕괴 감지 (2026-01-13 추가)
    ) -> Dict[str, Any]:
        """
        해역증(解㑊證) 증상 감지 (상열, 과열)
        
        해역증: 상열(上熱) 증상 + 하체 무력 (상체 강화 + 하체 약화)
        경제: 자산 가격 급등, 과열 버블, 투기 열풍
        
        핵심: S-M 괴리 기반 붕괴 감지
        - S 차원이 높아지면서 M 차원이 급락 → 해역증 (붕괴 위험)
        - 단순히 S가 높다고 "안정"으로 판단하지 않음
        
        Args:
            asset_price_inflation: 자산 가격 인플레이션 (연율)
            market_overheating: 시장 과열 지수 (0.0 ~ 1.0)
            speculation_index: 투기 지수 (0.0 ~ 1.0)
            vector_4d: 4차원 벡터 (S-M 괴리 계산용, 선택적)
        
        Returns:
            해역증 증상 감지 결과
        """
        # 해역증 증상 점수 계산 (기존)
        hae_yeok_score = (
            min(asset_price_inflation / 0.3, 1.0) * 0.4 +  # 30% 인플레이션 기준
            market_overheating * 0.3 +
            speculation_index * 0.3
        )
        
        # S-M 괴리 기반 붕괴 감지 (2026-01-13 추가)
        s_m_gap_score = 0.0
        s_m_gap_detected = False
        collapse_risk_boost = 0.0
        
        if vector_4d:
            s_value = vector_4d.get("S", 0.25)
            m_value = vector_4d.get("M", 0.25)
            
            # S-M 괴리 계산: S가 높고 M이 낮을수록 위험
            # 정상 상태: S ≈ M ≈ 0.25
            # 해역증: S > 0.3 and M < 0.2 (상체 강화 + 하체 무력)
            s_m_gap = s_value - m_value
            
            # 괴리 임계값: 0.07 이상이면 해역증 의심 (30% 하향 조정)
            gap_threshold = 0.07  # 동적 임계값 (30% 하향 조정)
            
            if s_m_gap > gap_threshold:
                s_m_gap_detected = True
                # 괴리 정도에 따라 붕괴 위험도 증가
                # 괴리 0.1 = 위험도 +0.3, 괴리 0.2 = 위험도 +0.6
                collapse_risk_boost = min(1.0, (s_m_gap - gap_threshold) * 3.0)
                s_m_gap_score = collapse_risk_boost
            
            logger.debug(f"S-M 괴리: {s_m_gap:.4f}, 임계값: {gap_threshold:.4f}, 붕괴 위험 증가: {collapse_risk_boost:.4f}")
        
        # 해역증 최종 점수: 기존 점수 + S-M 괴리 기반 붕괴 위험
        final_hae_yeok_score = hae_yeok_score + (s_m_gap_score * 0.5)  # S-M 괴리 가중치 50%
        
        # 해역증 감지: 기존 임계값 또는 S-M 괴리 감지
        is_hae_yeok = final_hae_yeok_score >= self.symptoms_thresholds["hae_yeok"] or s_m_gap_detected
        
        # 심각도 판정: S-M 괴리 감지 시 자동으로 "high" 또는 "critical"
        if s_m_gap_detected and collapse_risk_boost > 0.5:
            severity = "critical"  # 붕괴 위험 극대
        elif s_m_gap_detected or final_hae_yeok_score >= 0.8:
            severity = "high"
        elif final_hae_yeok_score >= 0.6:
            severity = "medium"
        else:
            severity = "low"
        
        interpretation = "상열로 인한 과열 버블 (해역증)"
        if s_m_gap_detected:
            interpretation += f" + S-M 괴리 감지 (상체 강화 + 하체 무력, 붕괴 위험 {collapse_risk_boost*100:.1f}%)"
        
        return {
            "symptom": "hae_yeok",
            "score": final_hae_yeok_score,
            "detected": is_hae_yeok,
            "severity": severity,
            "interpretation": interpretation if is_hae_yeok else "정상 범위",
            "s_m_gap_detected": s_m_gap_detected,  # S-M 괴리 감지 여부
            "s_m_gap_score": s_m_gap_score,  # S-M 괴리 점수
            "collapse_risk_boost": collapse_risk_boost,  # 붕괴 위험 증가율
            "details": {
                "asset_price_inflation": asset_price_inflation,
                "market_overheating": market_overheating,
                "speculation_index": speculation_index,
                "s_m_gap": vector_4d.get("S", 0.25) - vector_4d.get("M", 0.25) if vector_4d else 0.0,
                "gap_threshold": 0.07  # 동적 임계값 (30% 하향 조정)
            }
        }
    
    def detect_yeol_gyeok_symptom(
        self,
        market_disruption: float,
        trading_halt_frequency: float,
        liquidity_crisis: float
    ) -> Dict[str, Any]:
        """
        열격증(噎膈證) 증상 감지 (열격, 거래 중단)
        
        열격증: 열격(噎膈) 증상
        경제: 시장 교란, 거래 중단, 서킷브레이커
        
        Args:
            market_disruption: 시장 교란 지수 (0.0 ~ 1.0)
            trading_halt_frequency: 거래 중단 빈도 (0.0 ~ 1.0)
            liquidity_crisis: 유동성 위기 지수 (0.0 ~ 1.0)
        
        Returns:
            열격증 증상 감지 결과
        """
        # 열격증 증상 점수 계산
        yeol_gyeok_score = (
            market_disruption * 0.4 +
            trading_halt_frequency * 0.3 +
            liquidity_crisis * 0.3
        )
        
        is_yeol_gyeok = yeol_gyeok_score >= self.symptoms_thresholds["yeol_gyeok"]
        
        return {
            "symptom": "yeol_gyeok",
            "score": yeol_gyeok_score,
            "detected": is_yeol_gyeok,
            "severity": "high" if yeol_gyeok_score >= 0.8 else "medium" if yeol_gyeok_score >= 0.6 else "low",
            "interpretation": "시장 교란으로 인한 열격 (열격증)" if is_yeol_gyeok else "정상 범위",
            "details": {
                "market_disruption": market_disruption,
                "trading_halt_frequency": trading_halt_frequency,
                "liquidity_crisis": liquidity_crisis
            }
        }
    
    def diagnose_taeyang_pathology(
        self,
        market_data: Dict[str, Any],
        vector_4d: Optional[Dict[str, float]] = None  # S-M 괴리 기반 붕괴 감지 (2026-01-13 추가)
    ) -> Dict[str, Any]:
        """
        태양인 병증 종합 진단
        
        Args:
            market_data: 시장 데이터
        
        Returns:
            태양인 병증 진단 결과
        """
        # 각 증상별 감지
        sanghan_result = self.detect_sanghan_symptom(
            geopolitical_risk=market_data.get("geopolitical_risk", 0.0),
            policy_change_volatility=market_data.get("policy_change_volatility", 0.0),
            war_risk_index=market_data.get("war_risk_index", 0.0)
        )
        
        hae_yeok_result = self.detect_hae_yeok_symptom(
            asset_price_inflation=market_data.get("asset_price_inflation", 0.0),
            market_overheating=market_data.get("market_overheating", 0.0),
            speculation_index=market_data.get("speculation_index", 0.0),
            vector_4d=vector_4d  # S-M 괴리 기반 붕괴 감지 (2026-01-13 추가)
        )
        
        yeol_gyeok_result = self.detect_yeol_gyeok_symptom(
            market_disruption=market_data.get("market_disruption", 0.0),
            trading_halt_frequency=market_data.get("trading_halt_frequency", 0.0),
            liquidity_crisis=market_data.get("liquidity_crisis", 0.0)
        )
        
        # 종합 점수 계산
        taeyang_score = (
            sanghan_result["score"] * 0.4 +
            hae_yeok_result["score"] * 0.3 +
            yeol_gyeok_result["score"] * 0.3
        )
        
        # 병리 수준 판정
        if taeyang_score >= 0.7:
            pathology_level = "SL"  # Surface Level
        elif taeyang_score >= 0.3:
            pathology_level = "IL"  # Intermediate Level
        else:
            pathology_level = "DL"  # Deep Level
        
        return {
            "constitution": "태양인",
            "pathology": "상한/해역증/열격증",
            "score": taeyang_score,
            "pathology_level": pathology_level,
            "symptoms": {
                "상한": sanghan_result["score"],
                "해역증": hae_yeok_result["score"],
                "열격증": yeol_gyeok_result["score"],
            },
            "symptom_details": {
                "상한": sanghan_result,
                "해역증": hae_yeok_result,
                "열격증": yeol_gyeok_result,
            },
            "detected": taeyang_score >= self.symptoms_thresholds["sanghan"],
            "interpretation": "태양인 병증: 외부 충격 + 상열 + 시장 교란",
            "recommendation": self._generate_recommendation(
                sanghan_result, hae_yeok_result, yeol_gyeok_result, taeyang_score
            )
        }
    
    def _generate_recommendation(
        self,
        sanghan_result: Dict[str, Any],
        hae_yeok_result: Dict[str, Any],
        yeol_gyeok_result: Dict[str, Any],
        taeyang_score: float
    ) -> str:
        """태양인 병증 진단 기반 권장사항 생성"""
        recommendations = []
        
        if sanghan_result["detected"]:
            recommendations.append("⚠️ 상한(외부 충격) 감지: 방어적 포지션, 헤징 강화")
        
        if hae_yeok_result["detected"]:
            recommendations.append("⚠️ 해역증(과열 버블) 감지: 과열 자산 매도, 현금 비중 확대")
        
        if yeol_gyeok_result["detected"]:
            recommendations.append("⚠️ 열격증(시장 교란) 감지: 거래 중단 대비, 유동성 확보")
        
        if taeyang_score >= 0.7:
            recommendations.append("🚨 최우선: 태양인 병증 위급, 긴급 매도!")
        
        return " | ".join(recommendations) if recommendations else "정상 범위"

