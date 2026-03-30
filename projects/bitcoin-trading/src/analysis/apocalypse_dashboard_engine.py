#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 묵시록 대시보드 엔진 (Apocalypse Dashboard Engine)

목적: 뉴스 수집 → 병증 진단 → 4D 위상 벡터 변환 → 위기 신호 생성

작성일: 2026-01-12
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "src" / "analysis"))

from apocalypse_news_collector import ApocalypseNewsCollector
from sasang_constitution_crisis_detector import SasangConstitutionCrisisDetector
from phase_space_nowcaster import PhaseSpaceNowcaster
from graphrag_pathology_inferencer import GraphRAGPathologyInferencer

logger = logging.getLogger(__name__)


class ApocalypseDashboardEngine:
    """
    묵시록 대시보드 엔진
    
    통합 프로세스:
    1. 뉴스 수집 (ApocalypseNewsCollector)
    2. 병증 진단 (SasangConstitutionCrisisDetector)
    3. 4D 위상 벡터 변환
    4. 위기 신호 생성
    """
    
    def __init__(self, newsapi_key: Optional[str] = None):
        """초기화"""
        self.news_collector = ApocalypseNewsCollector(newsapi_key=newsapi_key)
        self.crisis_detector = SasangConstitutionCrisisDetector()
        self.nowcaster = PhaseSpaceNowcaster()  # 나우캐스터 추가
        self.graphrag_inferencer = GraphRAGPathologyInferencer()  # GraphRAG 추론기 추가
    
    def analyze_current_crisis(
        self,
        days: int = 7,
        limit_per_keyword: int = 10
    ) -> Dict[str, Any]:
        """
        현재 위기 상황 종합 분석
        
        Args:
            days: 최근 며칠간의 뉴스
            limit_per_keyword: 키워드당 수집할 뉴스 개수
            
        Returns:
            {
                "pathology_news": {...},  # 수집된 뉴스
                "market_data": {...},  # 시장 데이터
                "pathology_diagnosis": {...},  # 병증 진단 결과
                "crisis_level": "EMERGENCY_SELL" | "SELL" | "REDUCE" | "HOLD",
                "vector_4d": {"S": float, "L": float, "K": float, "M": float},
                "distance_to_centroid": float,
                "max_risk_constitution": str,
                "timestamp": str
            }
        """
        # 1. 뉴스 수집
        logger.info("📰 뉴스 수집 중...")
        pathology_news = self.news_collector.collect_pathology_news(
            days=days,
            limit_per_keyword=limit_per_keyword
        )
        
        # 1-1. GraphRAG 기반 엔티티 추출 및 병증 추론
        logger.info("🕸️ GraphRAG 기반 병증 추론 중...")
        all_news = []
        for constitution, pathologies in pathology_news.items():
            for pathology, news_list in pathologies.items():
                all_news.extend(news_list)
        
        entities = self.graphrag_inferencer.extract_entities_from_news(all_news)
        graph_inference = self.graphrag_inferencer.infer_pathology_from_graph(entities)
        
        # 2. 시장 데이터 변환
        logger.info("📊 시장 데이터 변환 중...")
        market_data = self.news_collector.aggregate_news_to_market_data(pathology_news)
        
        # 2-1. GraphRAG 점수와 키워드 점수 통합
        keyword_scores = self._extract_keyword_scores_from_pathology_news(pathology_news)
        integrated_scores = self.graphrag_inferencer.aggregate_pathology_scores(
            graph_inference,
            keyword_scores
        )
        
        # 시장 데이터에 GraphRAG 점수 반영
        market_data = self._merge_graphrag_scores_to_market_data(market_data, integrated_scores)
        
        # 3. 병증 진단
        logger.info("🔬 병증 진단 중...")
        pathology_diagnosis = self.crisis_detector.diagnose_all_constitutions(market_data)
        
        # 4. 병증 진단 결과를 표준 형식으로 변환
        standardized_diagnosis = self._standardize_pathology_diagnosis(pathology_diagnosis)
        
        # 5. 최대 위험 체질 식별 (표준화된 진단 결과 기반)
        max_risk_constitution = self._identify_max_risk_constitution(standardized_diagnosis)
        
        # 6. 4D 위상 벡터 계산
        vector_4d = self._calculate_4d_vector_from_pathology(standardized_diagnosis)
        
        # 7. Divine Centroid와의 거리 계산
        from sasang_constitution_crisis_detector import DIVINE_CENTROID
        import numpy as np
        
        current_vector = np.array([
            vector_4d.get("S", 0.25),
            vector_4d.get("L", 0.25),
            vector_4d.get("K", 0.25),
            vector_4d.get("M", 0.25)
        ])
        
        divine_vector = np.array([
            DIVINE_CENTROID["S"],
            DIVINE_CENTROID["L"],
            DIVINE_CENTROID["K"],
            DIVINE_CENTROID["M"]
        ])
        
        distance_to_centroid = float(np.linalg.norm(current_vector - divine_vector))
        
        # 8. 나우캐스터 업데이트 (위상 벡터 기록)
        self.nowcaster.update_phase_vector(vector_4d)
        
        # 9. 패턴 매칭 (DTW)
        pattern_match = self.nowcaster.match_historical_patterns(window_days=30)
        
        # 10. 시나리오 확률 계산
        scenarios = self.nowcaster.predict_scenarios(horizon_days=30)
        
        # 11. 위기 신호 생성 (시나리오 기반)
        crisis_level = self._generate_crisis_signal_from_scenarios(
            scenarios,
            distance_to_centroid
        )
        
        return {
            "pathology_news": pathology_news,
            "market_data": market_data,
            "pathology_diagnosis": standardized_diagnosis,
            "crisis_level": crisis_level,
            "vector_4d": vector_4d,
            "distance_to_centroid": distance_to_centroid,
            "max_risk_constitution": max_risk_constitution,
            "pattern_matching": pattern_match,
            "scenarios": scenarios.get("scenarios", {}),
            "nowcasting": {
                "distance_velocity": float(self.nowcaster.velocity),
                "distance_acceleration": float(self.nowcaster.acceleration)
            },
            "graphrag_inference": {
                "triggered_entities": entities,
                "graph_paths": graph_inference.get("graph_inference", {}).get("paths", []),
                "graph_density": graph_inference.get("graph_inference", {}).get("graph_density", 0.0)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _standardize_pathology_diagnosis(
        self,
        pathology_diagnosis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        병증 진단 결과를 표준 형식으로 변환
        
        Args:
            pathology_diagnosis: 원본 병증 진단 결과
            
        Returns:
            표준화된 병증 진단 결과
        """
        standardized = {}
        
        # diagnose_all_constitutions의 반환 형식: {"diagnosis": {"태양인": {...}, ...}, ...}
        if "diagnosis" in pathology_diagnosis:
            # 표준 형식
            for constitution, diag in pathology_diagnosis["diagnosis"].items():
                if isinstance(diag, dict):
                    score = diag.get("score", diag.get("overall_score", 0.0))
                    standardized[constitution] = {
                        "overall_score": score,
                        "pathology_level": self._determine_pathology_level(score),
                        "detected": diag.get("detected", False),
                        "interpretation": diag.get("interpretation", ""),
                        "symptoms": diag.get("symptoms", {})
                    }
                else:
                    standardized[constitution] = {
                        "overall_score": 0.0,
                        "pathology_level": "SL",
                        "detected": False,
                        "interpretation": "",
                        "symptoms": {}
                    }
        else:
            # 직접 딕셔너리 형식
            for constitution, diag in pathology_diagnosis.items():
                if isinstance(diag, dict):
                    score = diag.get("overall_score", diag.get("score", 0.0))
                    standardized[constitution] = {
                        "overall_score": score,
                        "pathology_level": self._determine_pathology_level(score),
                        "detected": diag.get("detected", False),
                        "interpretation": diag.get("interpretation", ""),
                        "symptoms": diag.get("symptoms", {})
                    }
                else:
                    standardized[constitution] = {
                        "overall_score": 0.0,
                        "pathology_level": "SL",
                        "detected": False,
                        "interpretation": "",
                        "symptoms": {}
                    }
        
        return standardized
    
    def _determine_pathology_level(self, score: float) -> str:
        """
        병리 수준 판정
        
        Args:
            score: 병증 점수 (0.0 ~ 1.0)
            
        Returns:
            "SL" | "IL" | "DL"
        """
        if score >= 0.7:
            return "SL"  # Surface Level
        elif score >= 0.3:
            return "IL"  # Intermediate Level
        else:
            return "DL"  # Deep Level
    
    def _calculate_4d_vector_from_pathology(
        self,
        pathology_diagnosis: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        병증 진단 결과를 4D 벡터로 변환
        
        Args:
            pathology_diagnosis: 병증 진단 결과
            
        Returns:
            4D 벡터 (S, L, K, M)
        """
        # 각 체질의 병증 점수를 4D 벡터로 매핑
        # S (Spirit): 태양인 상열 + 소음인 가짜 열
        # L (Logic): 태음인 표리병 + 소양인 기반 구조
        # K (Knowledge): 태양인 외부 충격 + 소양인 음기 소실
        # M (Material): 소음인 진짜 양기 소실
        
        taeyang = pathology_diagnosis.get("태양인", {})
        taeum = pathology_diagnosis.get("태음인", {})
        soyang = pathology_diagnosis.get("소양인", {})
        soeum = pathology_diagnosis.get("소음인", {})
        
        taeyang_score = taeyang.get("overall_score", 0.0)
        taeum_score = taeum.get("overall_score", 0.0)
        soyang_score = soyang.get("overall_score", 0.0)
        soeum_score = soeum.get("overall_score", 0.0)
        
        # 증상 점수 추출 (가능한 경우)
        taeyang_symptoms = taeyang.get("symptoms", {})
        taeum_symptoms = taeum.get("symptoms", {})
        soyang_symptoms = soyang.get("symptoms", {})
        soeum_symptoms = soeum.get("symptoms", {})
        
        # 4D 벡터 계산 (증상 점수 우선 사용)
        S = (
            taeyang_symptoms.get("해역증", taeyang_score * 0.3) * 0.3 +  # 태양인 상열
            soeum_symptoms.get("땀", soeum_score * 0.2) * 0.2      # 소음인 가짜 열
        )
        
        L = (
            taeum_symptoms.get("배추표병", taeum_score * 0.3) * 0.3 +    # 태음인 표리병
            soyang_symptoms.get("등척소장병", soyang_score * 0.2) * 0.2     # 소양인 기반 구조
        )
        
        K = (
            taeyang_symptoms.get("상한", taeyang_score * 0.2) * 0.2 +  # 태양인 외부 충격
            soyang_symptoms.get("망음증", soyang_score * 0.3) * 0.3     # 소양인 음기 소실
        )
        
        M = (
            soeum_symptoms.get("수족냉증", soeum_score * 0.3) * 0.3      # 소음인 진짜 양기 소실
        )
        
        # 정규화 (합이 1.0이 되도록)
        total = S + L + K + M
        if total > 0:
            S = S / total
            L = L / total
            K = K / total
            M = M / total
        else:
            # 기본값 (Divine Centroid)
            S = 0.25
            L = 0.25
            K = 0.25
            M = 0.25
        
        return {
            "S": float(S),
            "L": float(L),
            "K": float(K),
            "M": float(M)
        }
    
    def _identify_max_risk_constitution(
        self,
        pathology_diagnosis: Dict[str, Any]
    ) -> str:
        """
        최대 위험 체질 식별
        
        Args:
            pathology_diagnosis: 병증 진단 결과
            
        Returns:
            최대 위험 체질 이름
        """
        max_score = 0.0
        max_constitution = "소음인"  # 기본값
        
        for constitution, diag in pathology_diagnosis.items():
            if isinstance(diag, dict):
                score = diag.get("overall_score", diag.get("score", 0.0))
                if score > max_score:
                    max_score = score
                    max_constitution = constitution
        
        return max_constitution
    
    def _generate_crisis_signal(
        self,
        pathology_diagnosis: Dict[str, Any],
        distance_to_centroid: float,
        max_risk_constitution: str
    ) -> str:
        """
        위기 신호 생성 (기존 방식 - 호환성 유지)
        
        Args:
            pathology_diagnosis: 병증 진단 결과
            distance_to_centroid: Divine Centroid와의 거리
            max_risk_constitution: 최대 위험 체질
            
        Returns:
            "EMERGENCY_SELL" | "SELL" | "REDUCE" | "HOLD"
        """
        # 최대 위험 체질의 병리 수준 확인
        max_risk_pathology = pathology_diagnosis.get(max_risk_constitution, {})
        pathology_level = max_risk_pathology.get("pathology_level", "SL")
        overall_score = max_risk_pathology.get("overall_score", 0.0)
        
        # 위기 신호 판정
        if overall_score >= 0.8 or distance_to_centroid >= 0.3:
            return "EMERGENCY_SELL"
        elif overall_score >= 0.6 or distance_to_centroid >= 0.2:
            return "SELL"
        elif overall_score >= 0.4 or distance_to_centroid >= 0.1:
            return "REDUCE"
        else:
            return "HOLD"
    
    def _generate_crisis_signal_from_scenarios(
        self,
        scenarios: Dict[str, Any],
        distance_to_centroid: float
    ) -> str:
        """
        시나리오 기반 위기 신호 생성 (새로운 방식)
        
        Args:
            scenarios: 시나리오 확률 딕셔너리
            distance_to_centroid: Divine Centroid와의 거리
            
        Returns:
            "EMERGENCY_SELL" | "SELL" | "REDUCE" | "HOLD"
        """
        scenario_c = scenarios.get("scenarios", {}).get("C_collapse", {})
        collapse_prob = scenario_c.get("probability", 0.0)
        
        # 시나리오 C 확률 기반 판정
        if collapse_prob >= 0.5 or distance_to_centroid >= 0.4:
            return "EMERGENCY_SELL"
        elif collapse_prob >= 0.3 or distance_to_centroid >= 0.3:
            return "SELL"
        elif collapse_prob >= 0.1 or distance_to_centroid >= 0.2:
            return "REDUCE"
        else:
            return "HOLD"
    
    def _extract_keyword_scores_from_pathology_news(
        self,
        pathology_news: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> Dict[str, Dict[str, float]]:
        """
        병증 뉴스에서 키워드 기반 점수 추출
        
        Args:
            pathology_news: 병증 뉴스 딕셔너리
            
        Returns:
            키워드 기반 병증 점수
        """
        keyword_scores = {
            "태양인": {"해역증": 0.0, "상한": 0.0},
            "태음인": {"배추표병": 0.0},
            "소양인": {"망음증": 0.0},
            "소음인": {"망양증": 0.0}
        }
        
        max_news_count = 20  # 최대 뉴스 개수 기준
        
        for constitution, pathologies in pathology_news.items():
            for pathology_name, news_list in pathologies.items():
                news_count = len(news_list)
                score = min(news_count / max_news_count, 1.0)
                
                if constitution in keyword_scores:
                    if pathology_name in keyword_scores[constitution]:
                        keyword_scores[constitution][pathology_name] = score
        
        return keyword_scores
    
    def _merge_graphrag_scores_to_market_data(
        self,
        market_data: Dict[str, Any],
        integrated_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        GraphRAG 점수를 시장 데이터에 병합
        
        Args:
            market_data: 시장 데이터
            integrated_scores: 통합된 병증 점수
            
        Returns:
            병합된 시장 데이터
        """
        # 태양인
        taeyang = integrated_scores.get("태양인", {})
        market_data["asset_price_inflation"] = max(
            market_data.get("asset_price_inflation", 0.0),
            taeyang.get("해역증", 0.0)
        )
        market_data["geopolitical_risk"] = max(
            market_data.get("geopolitical_risk", 0.0),
            taeyang.get("상한", 0.0)
        )
        
        # 태음인
        taeum = integrated_scores.get("태음인", {})
        market_data["stagflation_index"] = max(
            market_data.get("stagflation_index", 0.0),
            taeum.get("배추표병", 0.0)
        )
        
        # 소양인
        soyang = integrated_scores.get("소양인", {})
        market_data["liquidity_crisis"] = max(
            market_data.get("liquidity_crisis", 0.0),
            soyang.get("망음증", 0.0)
        )
        
        # 소음인
        soeum = integrated_scores.get("소음인", {})
        market_data["fake_recovery_index"] = max(
            market_data.get("fake_recovery_index", 0.0),
            soeum.get("망양증", 0.0)
        )
        market_data["real_economy_freeze"] = max(
            market_data.get("real_economy_freeze", 0.0),
            soeum.get("망양증", 0.0) * 0.8
        )
        
        return market_data


async def main():
    """테스트 함수"""
    engine = ApocalypseDashboardEngine()
    
    print("\n🏛️ 묵시록 대시보드 엔진 테스트")
    print("=" * 80)
    
    result = engine.analyze_current_crisis(days=7, limit_per_keyword=10)
    
    print(f"\n✅ 분석 완료:")
    print(f"   위기 신호: {result['crisis_level']}")
    print(f"   최대 위험 체질: {result['max_risk_constitution']}")
    print(f"   Divine Centroid 거리: {result['distance_to_centroid']:.3f}")
    print(f"   4D 벡터: S={result['vector_4d']['S']:.3f}, L={result['vector_4d']['L']:.3f}, K={result['vector_4d']['K']:.3f}, M={result['vector_4d']['M']:.3f}")
    
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

