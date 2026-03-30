#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ GraphRAG 병증 추론기 (GraphRAG Pathology Inferencer)

목적: 주관적 직관을 인과관계 그래프로 전환
- 지식 그래프 구축 (성경 아키타입, 경제 현상, 기술 트렌드)
- 뉴스 엔티티 추출 → 그래프 매핑
- 경로 탐색 기반 병증 추론

작성일: 2026-01-12
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "mcp-servers"))

# GraphRAG 시스템 (선택적)
try:
    from graph_rag_system import GraphRAGSystem, GraphNode, GraphEdge
    GRAPHRAG_AVAILABLE = True
except ImportError:
    GRAPHRAG_AVAILABLE = False
    print("⚠️ GraphRAG 시스템을 찾을 수 없습니다. 기본 방식 사용")

# NetworkX (선택적)
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("⚠️ NetworkX를 찾을 수 없습니다. pip install networkx 필요")

logger = logging.getLogger(__name__)


class GraphRAGPathologyInferencer:
    """
    GraphRAG 기반 병증 추론기
    
    목적: 주관적 키워드 매핑을 인과관계 그래프로 전환
    """
    
    def __init__(self):
        """초기화"""
        self.knowledge_graph = None
        self.graph_rag = None
        
        if GRAPHRAG_AVAILABLE:
            try:
                self.graph_rag = GraphRAGSystem()
            except Exception as e:
                logger.warning(f"⚠️ GraphRAG 시스템 초기화 실패: {e}")
        
        # 지식 그래프 구축
        self._build_knowledge_graph()
    
    def _build_knowledge_graph(self):
        """
        지식 그래프 구축
        
        노드: 성경 아키타입, 경제 현상, 기술 트렌드, 병증
        엣지: 인과관계, 유사성, 트리거 관계
        """
        if not NETWORKX_AVAILABLE:
            logger.warning("⚠️ NetworkX 미설치, 그래프 구축 불가")
            return
        
        self.knowledge_graph = nx.DiGraph()
        
        # 노드 추가
        nodes = [
            # 성경 아키타입
            {"id": "성경_흰말", "type": "biblical_archetype", "properties": {"승리": True, "미혹": True, "활": True}},
            {"id": "성경_붉은말", "type": "biblical_archetype", "properties": {"전쟁": True, "평화제거": True}},
            {"id": "성경_검은말", "type": "biblical_archetype", "properties": {"기근": True, "물가상승": True}},
            {"id": "성경_청황색말", "type": "biblical_archetype", "properties": {"사망": True, "질서종말": True}},
            
            # 기술 트렌드
            {"id": "기술_Generative_AI", "type": "technology", "properties": {"대량생산": True, "진위왜곡": True, "지능정복": True}},
            {"id": "기술_딥페이크", "type": "technology", "properties": {"진위왜곡": True, "정보조작": True}},
            {"id": "기술_자동화", "type": "technology", "properties": {"대량생산": True, "실업증가": True}},
            
            # 경제 현상
            {"id": "경제_버블", "type": "economic_phenomenon", "properties": {"과열": True, "투기": True, "가격상승": True}},
            {"id": "경제_스태그플레이션", "type": "economic_phenomenon", "properties": {"경기침체": True, "인플레이션": True}},
            {"id": "경제_유동성고갈", "type": "economic_phenomenon", "properties": {"신용위축": True, "부채위기": True}},
            {"id": "경제_실물동결", "type": "economic_phenomenon", "properties": {"실업증가": True, "소비감소": True}},
            
            # 병증
            {"id": "병증_태양인_해역증", "type": "pathology", "properties": {"상열": True, "과열": True}},
            {"id": "병증_태양인_상한", "type": "pathology", "properties": {"외부충격": True, "표병": True}},
            {"id": "병증_태음인_배추표병", "type": "pathology", "properties": {"표리병": True, "복합문제": True}},
            {"id": "병증_소양인_망음증", "type": "pathology", "properties": {"음기소실": True, "유동성고갈": True}},
            {"id": "병증_소음인_망양증", "type": "pathology", "properties": {"양기소실": True, "가짜열": True}},
        ]
        
        for node in nodes:
            self.knowledge_graph.add_node(
                node["id"],
                type=node["type"],
                properties=node.get("properties", {})
            )
        
        # 엣지 추가 (인과관계)
        edges = [
            # 성경 아키타입 → 기술 트렌드
            {"source": "성경_흰말", "target": "기술_Generative_AI", "relationship": "미혹→진위왜곡", "weight": 0.85},
            {"source": "성경_흰말", "target": "기술_딥페이크", "relationship": "미혹→정보조작", "weight": 0.80},
            {"source": "성경_붉은말", "target": "기술_자동화", "relationship": "전쟁→실업증가", "weight": 0.70},
            
            # 기술 트렌드 → 경제 현상
            {"source": "기술_Generative_AI", "target": "경제_버블", "relationship": "대량생산→과열", "weight": 0.72},
            {"source": "기술_딥페이크", "target": "경제_버블", "relationship": "정보조작→투기", "weight": 0.65},
            {"source": "기술_자동화", "target": "경제_실물동결", "relationship": "실업증가→소비감소", "weight": 0.75},
            
            # 경제 현상 → 병증
            {"source": "경제_버블", "target": "병증_태양인_해역증", "relationship": "과열→상열", "weight": 0.80},
            {"source": "경제_스태그플레이션", "target": "병증_태음인_배추표병", "relationship": "복합문제→표리병", "weight": 0.85},
            {"source": "경제_유동성고갈", "target": "병증_소양인_망음증", "relationship": "신용위축→음기소실", "weight": 0.90},
            {"source": "경제_실물동결", "target": "병증_소음인_망양증", "relationship": "소비감소→양기소실", "weight": 0.88},
            
            # 성경 아키타입 → 병증 (직접 연결)
            {"source": "성경_흰말", "target": "병증_태양인_해역증", "relationship": "미혹→상열", "weight": 0.75},
            {"source": "성경_검은말", "target": "병증_소양인_망음증", "relationship": "기근→음기소실", "weight": 0.82},
            {"source": "성경_청황색말", "target": "병증_소음인_망양증", "relationship": "사망→양기소실", "weight": 0.90},
        ]
        
        for edge in edges:
            self.knowledge_graph.add_edge(
                edge["source"],
                edge["target"],
                relationship=edge["relationship"],
                weight=edge["weight"]
            )
        
        logger.info(f"✅ 지식 그래프 구축 완료 ({len(self.knowledge_graph.nodes())}개 노드, {len(self.knowledge_graph.edges())}개 엣지)")
    
    def extract_entities_from_news(
        self,
        news_list: List[Dict[str, Any]]
    ) -> List[str]:
        """
        뉴스에서 엔티티 추출
        
        Args:
            news_list: 뉴스 리스트
            
        Returns:
            엔티티 리스트
        """
        entities = []
        
        # 간단한 키워드 기반 엔티티 추출
        # 실제 구현 시: NER 모델 사용 (spaCy, transformers 등)
        
        entity_keywords = {
            "기술_Generative_AI": ["AI", "artificial intelligence", "generative", "GPT", "LLM", "인공지능"],
            "기술_딥페이크": ["deepfake", "딥페이크", "fake video", "조작"],
            "기술_자동화": ["automation", "자동화", "robot", "로봇"],
            "경제_버블": ["bubble", "버블", "overheating", "과열", "speculation", "투기"],
            "경제_스태그플레이션": ["stagflation", "스태그플레이션", "stagnation", "경기침체"],
            "경제_유동성고갈": ["liquidity crisis", "유동성 위기", "credit crunch", "신용 경색"],
            "경제_실물동결": ["real economy freeze", "실물 경제 동결", "unemployment", "실업"],
            "성경_흰말": ["peace", "평화", "victory", "승리", "deception", "미혹"],
            "성경_붉은말": ["war", "전쟁", "conflict", "분쟁"],
            "성경_검은말": ["famine", "기근", "inflation", "인플레이션"],
            "성경_청황색말": ["death", "사망", "collapse", "붕괴"],
        }
        
        # 뉴스 텍스트 수집
        all_text = " ".join([
            news.get("title", "") + " " + news.get("description", "")
            for news in news_list
        ]).lower()
        
        # 키워드 매칭
        for entity_id, keywords in entity_keywords.items():
            for keyword in keywords:
                if keyword.lower() in all_text:
                    entities.append(entity_id)
                    break  # 중복 방지
        
        return list(set(entities))  # 중복 제거
    
    def infer_pathology_from_graph(
        self,
        entities: List[str]
    ) -> Dict[str, Any]:
        """
        그래프 기반 병증 추론
        
        Args:
            entities: 추출된 엔티티 리스트
            
        Returns:
            병증 추론 결과
        """
        if not NETWORKX_AVAILABLE or self.knowledge_graph is None:
            logger.warning("⚠️ 그래프 미구축, 기본 추론 반환")
            return self._default_pathology_inference(entities)
        
        pathology_scores = {
            "태양인": {"해역증": 0.0, "상한": 0.0},
            "태음인": {"배추표병": 0.0},
            "소양인": {"망음증": 0.0},
            "소음인": {"망양증": 0.0}
        }
        
        # 각 엔티티에서 병증까지의 경로 탐색
        for entity in entities:
            if entity not in self.knowledge_graph:
                continue
            
            # 병증 노드 찾기
            pathology_nodes = [
                node for node in self.knowledge_graph.nodes()
                if node.startswith("병증_")
            ]
            
            for pathology_node in pathology_nodes:
                try:
                    # 최단 경로 탐색
                    if nx.has_path(self.knowledge_graph, entity, pathology_node):
                        path = nx.shortest_path(
                            self.knowledge_graph,
                            entity,
                            pathology_node
                        )
                        
                        # 경로 가중치 계산
                        path_weight = 1.0
                        for i in range(len(path) - 1):
                            edge_data = self.knowledge_graph[path[i]][path[i+1]]
                            path_weight *= edge_data.get("weight", 1.0)
                        
                        # 병증 점수 업데이트
                        pathology_name = pathology_node.replace("병증_", "")
                        if "태양인" in pathology_name:
                            if "해역증" in pathology_name:
                                pathology_scores["태양인"]["해역증"] += path_weight
                            elif "상한" in pathology_name:
                                pathology_scores["태양인"]["상한"] += path_weight
                        elif "태음인" in pathology_name:
                            pathology_scores["태음인"]["배추표병"] += path_weight
                        elif "소양인" in pathology_name:
                            pathology_scores["소양인"]["망음증"] += path_weight
                        elif "소음인" in pathology_name:
                            pathology_scores["소음인"]["망양증"] += path_weight
                
                except nx.NetworkXNoPath:
                    continue
        
        # 정규화 (0.0 ~ 1.0)
        max_score = max([
            max(scores.values()) if scores else 0.0
            for scores in pathology_scores.values()
        ])
        
        if max_score > 0:
            for constitution in pathology_scores:
                for pathology in pathology_scores[constitution]:
                    pathology_scores[constitution][pathology] /= max_score
        
        # 경로 정보 수집
        path_info = []
        for entity in entities[:3]:  # 상위 3개만
            if entity not in self.knowledge_graph:
                continue
            
            for pathology_node in [n for n in self.knowledge_graph.nodes() if n.startswith("병증_")]:
                try:
                    if nx.has_path(self.knowledge_graph, entity, pathology_node):
                        path = nx.shortest_path(self.knowledge_graph, entity, pathology_node)
                        path_info.append({
                            "source": entity,
                            "target": pathology_node,
                            "path": path,
                            "length": len(path) - 1
                        })
                except:
                    continue
        
        return {
            "pathology_scores": pathology_scores,
            "graph_inference": {
                "triggered_entities": entities,
                "paths": path_info[:5],  # 상위 5개 경로
                "graph_density": len(self.knowledge_graph.edges()) / max(len(self.knowledge_graph.nodes()), 1)
            }
        }
    
    def _default_pathology_inference(
        self,
        entities: List[str]
    ) -> Dict[str, Any]:
        """기본 병증 추론 (그래프 미사용 시)"""
        return {
            "pathology_scores": {
                "태양인": {"해역증": 0.0, "상한": 0.0},
                "태음인": {"배추표병": 0.0},
                "소양인": {"망음증": 0.0},
                "소음인": {"망양증": 0.0}
            },
            "graph_inference": {
                "triggered_entities": entities,
                "paths": [],
                "graph_density": 0.0
            }
        }
    
    def aggregate_pathology_scores(
        self,
        graph_inference: Dict[str, Any],
        keyword_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        그래프 추론 점수와 키워드 점수 통합
        
        Args:
            graph_inference: 그래프 추론 결과
            keyword_scores: 키워드 기반 점수
            
        Returns:
            통합된 병증 점수
        """
        graph_scores = graph_inference.get("pathology_scores", {})
        
        # 가중 평균 (그래프 0.6, 키워드 0.4)
        integrated_scores = {}
        
        for constitution in ["태양인", "태음인", "소양인", "소음인"]:
            integrated_scores[constitution] = {}
            
            graph_const = graph_scores.get(constitution, {})
            keyword_const = keyword_scores.get(constitution, {})
            
            for pathology in graph_const.keys() | keyword_const.keys():
                graph_score = graph_const.get(pathology, 0.0)
                keyword_score = keyword_const.get(pathology, 0.0)
                
                integrated_scores[constitution][pathology] = (
                    graph_score * 0.6 + keyword_score * 0.4
                )
        
        return integrated_scores


if __name__ == "__main__":
    # 테스트
    inferencer = GraphRAGPathologyInferencer()
    
    # 샘플 뉴스
    sample_news = [
        {"title": "AI technology advances rapidly", "description": "Generative AI creates new opportunities"},
        {"title": "Market bubble concerns grow", "description": "Stock prices reach new highs"},
        {"title": "Liquidity crisis looms", "description": "Credit markets tighten"}
    ]
    
    # 엔티티 추출
    entities = inferencer.extract_entities_from_news(sample_news)
    print(f"\n📊 추출된 엔티티: {entities}")
    
    # 병증 추론
    result = inferencer.infer_pathology_from_graph(entities)
    print(f"\n🔬 병증 추론 결과:")
    print(f"   병증 점수: {result['pathology_scores']}")
    print(f"   그래프 경로: {len(result['graph_inference']['paths'])}개")

