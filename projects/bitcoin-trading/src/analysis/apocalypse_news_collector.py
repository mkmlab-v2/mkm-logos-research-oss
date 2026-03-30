#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 묵시록 뉴스 수집기 (Apocalypse News Collector)

목적: 웹 뉴스에서 4체질 병증 관련 키워드를 수집하여 병증 진단에 활용

작성일: 2026-01-12
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# 외부 라이브러리 (선택적)
try:
    from newsapi import NewsApiClient
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False
    print("⚠️ newsapi를 찾을 수 없습니다. pip install newsapi-python 필요")

logger = logging.getLogger(__name__)


class ApocalypseNewsCollector:
    """
    묵시록 뉴스 수집기
    
    목적: 4체질 병증 관련 키워드를 웹 뉴스에서 수집
    """
    
    # 4체질 병증별 키워드 매핑
    PATHOLOGY_KEYWORDS = {
        "태양인": {
            "상한": ["war", "conflict", "geopolitical", "sanctions", "military", "전쟁", "분쟁", "제재"],
            "해역증": ["bubble", "overheating", "speculation", "mania", "버블", "과열", "투기", "열풍"],
            "열격증": ["trading halt", "market disruption", "circuit breaker", "거래 중단", "시장 교란", "서킷브레이커"]
        },
        "태음인": {
            "배추표병": ["stagflation", "inflation", "recession", "economic stagnation", "스태그플레이션", "경기 침체", "경제 정체"],
            "위완수한표한": ["wealth gap", "inequality", "poverty", "빈부격차", "불평등", "빈곤"]
        },
        "소양인": {
            "망음증": ["liquidity crisis", "credit crunch", "debt crisis", "유동성 위기", "신용 경색", "부채 위기"],
            "등척소장병": ["supply chain disruption", "shortage", "supply crisis", "공급망 붕괴", "부족", "공급 위기"]
        },
        "소음인": {
            "망양증": [
                "fake recovery", "liquidity flood", "real economy freeze", "fear", "panic",
                "가짜 회복", "유동성 폭주", "실물 경제 동결", "공포", "공황"
            ]
        }
    }
    
    def __init__(self, newsapi_key: Optional[str] = None):
        """
        Args:
            newsapi_key: NewsAPI 키 (환경 변수 NEWSAPI_KEY에서도 읽음)
        """
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        self.newsapi_client = None
        
        if NEWSAPI_AVAILABLE and self.newsapi_key:
            try:
                self.newsapi_client = NewsApiClient(api_key=self.newsapi_key)
                logger.info("✅ NewsAPI 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ NewsAPI 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ NewsAPI 사용 불가 (키 없음 또는 라이브러리 미설치)")
    
    def collect_pathology_news(
        self,
        days: int = 7,
        limit_per_keyword: int = 10
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        4체질 병증 관련 뉴스 수집
        
        Args:
            days: 최근 며칠간의 뉴스
            limit_per_keyword: 키워드당 수집할 뉴스 개수
            
        Returns:
            {
                "태양인": {
                    "상한": [뉴스 리스트],
                    "해역증": [뉴스 리스트],
                    "열격증": [뉴스 리스트]
                },
                "태음인": {...},
                "소양인": {...},
                "소음인": {...}
            }
        """
        result = {}
        
        if not self.newsapi_client:
            logger.warning("⚠️ NewsAPI 클라이언트가 없습니다. 샘플 데이터 반환")
            return self._get_sample_pathology_news()
        
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # 4체질별로 뉴스 수집
            for constitution, pathologies in self.PATHOLOGY_KEYWORDS.items():
                result[constitution] = {}
                
                for pathology_name, keywords in pathologies.items():
                    news_list = []
                    
                    # 키워드별로 뉴스 수집
                    for keyword in keywords[:3]:  # 상위 3개 키워드만 사용
                        try:
                            articles = self.newsapi_client.get_everything(
                                q=keyword,
                                from_param=from_date,
                                language="en",
                                sort_by="publishedAt",
                                page_size=min(limit_per_keyword, 20)
                            )
                            
                            if articles and articles.get("status") == "ok":
                                for article in articles.get("articles", [])[:limit_per_keyword]:
                                    news_list.append({
                                        "title": article.get("title", ""),
                                        "description": article.get("description", ""),
                                        "content": article.get("content", ""),
                                        "source": article.get("source", {}).get("name", ""),
                                        "published_at": article.get("publishedAt", ""),
                                        "url": article.get("url", ""),
                                        "keyword": keyword,
                                        "pathology": pathology_name,
                                        "constitution": constitution
                                    })
                        except Exception as e:
                            logger.warning(f"⚠️ 키워드 '{keyword}' 검색 실패: {e}")
                            continue
                    
                    # 중복 제거 (URL 기준)
                    seen_urls = set()
                    unique_news = []
                    for news in news_list:
                        url = news.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            unique_news.append(news)
                    
                    result[constitution][pathology_name] = unique_news[:limit_per_keyword]
                    logger.info(f"✅ {constitution} {pathology_name}: {len(unique_news)}개 뉴스 수집")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 병증 뉴스 수집 실패: {e}")
            return self._get_sample_pathology_news()
    
    def _get_sample_pathology_news(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """샘플 병증 뉴스 (NewsAPI 사용 불가 시)"""
        return {
            "태양인": {
                "상한": [{
                    "title": "Geopolitical tensions escalate in Middle East",
                    "description": "Rising tensions in the Middle East region",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "geopolitical",
                    "pathology": "상한",
                    "constitution": "태양인"
                }],
                "해역증": [{
                    "title": "Stock market bubble concerns grow",
                    "description": "Experts warn of market overheating",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "bubble",
                    "pathology": "해역증",
                    "constitution": "태양인"
                }],
                "열격증": [{
                    "title": "Trading halted due to market volatility",
                    "description": "Circuit breakers triggered",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "trading halt",
                    "pathology": "열격증",
                    "constitution": "태양인"
                }]
            },
            "태음인": {
                "배추표병": [{
                    "title": "Stagflation fears mount",
                    "description": "Economy faces stagnation and inflation",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "stagflation",
                    "pathology": "배추표병",
                    "constitution": "태음인"
                }],
                "위완수한표한": [{
                    "title": "Wealth gap widens",
                    "description": "Income inequality reaches new highs",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "wealth gap",
                    "pathology": "위완수한표한",
                    "constitution": "태음인"
                }]
            },
            "소양인": {
                "망음증": [{
                    "title": "Liquidity crisis looms",
                    "description": "Credit markets tighten",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "liquidity crisis",
                    "pathology": "망음증",
                    "constitution": "소양인"
                }],
                "등척소장병": [{
                    "title": "Supply chain disruptions continue",
                    "description": "Global supply shortages worsen",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "supply chain",
                    "pathology": "등척소장병",
                    "constitution": "소양인"
                }]
            },
            "소음인": {
                "망양증": [{
                    "title": "Fake recovery masks real economic freeze",
                    "description": "Liquidity flood hides underlying weakness",
                    "published_at": datetime.now().isoformat(),
                    "keyword": "fake recovery",
                    "pathology": "망양증",
                    "constitution": "소음인"
                }]
            }
        }
    
    def aggregate_news_to_market_data(
        self,
        pathology_news: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        """
        수집된 뉴스를 시장 데이터 형식으로 변환
        
        Args:
            pathology_news: 수집된 병증 뉴스
            
        Returns:
            시장 데이터 딕셔너리 (SasangConstitutionCrisisDetector 입력 형식)
        """
        market_data = {
            # 태양인 병증 지표
            "geopolitical_risk": 0.0,
            "policy_change_volatility": 0.0,
            "war_risk_index": 0.0,
            "asset_price_inflation": 0.0,
            "market_overheating": 0.0,
            "speculation_index": 0.0,
            "market_disruption": 0.0,
            "trading_halt_frequency": 0.0,
            
            # 태음인 병증 지표
            "stagflation_index": 0.0,
            "inflation_rate": 0.0,
            "economic_stagnation": 0.0,
            "real_economy_difficulty": 0.0,
            "asset_market_cooling": 0.0,
            "wealth_gap_index": 0.0,
            
            # 소양인 병증 지표
            "liquidity_crisis": 0.0,
            "credit_crunch": 0.0,
            "debt_crisis": 0.0,
            "supply_chain_disruption": 0.0,
            "shortage_index": 0.0,
            
            # 소음인 병증 지표
            "fake_recovery_index": 0.0,
            "liquidity_flood": 0.0,
            "real_economy_freeze": 0.0,
            "fear_index": 0.0,
            "panic_index": 0.0
        }
        
        # 뉴스 개수를 기반으로 지표 계산 (0.0 ~ 1.0)
        max_news_count = 20  # 최대 뉴스 개수 기준
        
        # 태양인
        if "태양인" in pathology_news:
            taeyang = pathology_news["태양인"]
            
            # 상한 (외부 충격)
            if "상한" in taeyang:
                news_count = len(taeyang["상한"])
                market_data["geopolitical_risk"] = min(news_count / max_news_count, 1.0)
                market_data["war_risk_index"] = min(news_count / max_news_count, 1.0)
            
            # 해역증 (상열)
            if "해역증" in taeyang:
                news_count = len(taeyang["해역증"])
                market_data["asset_price_inflation"] = min(news_count / max_news_count, 1.0)
                market_data["market_overheating"] = min(news_count / max_news_count, 1.0)
                market_data["speculation_index"] = min(news_count / max_news_count, 1.0)
            
            # 열격증 (시장 교란)
            if "열격증" in taeyang:
                news_count = len(taeyang["열격증"])
                market_data["market_disruption"] = min(news_count / max_news_count, 1.0)
                market_data["trading_halt_frequency"] = min(news_count / max_news_count, 1.0)
        
        # 태음인
        if "태음인" in pathology_news:
            taeum = pathology_news["태음인"]
            
            # 배추표병 (스태그플레이션)
            if "배추표병" in taeum:
                news_count = len(taeum["배추표병"])
                market_data["stagflation_index"] = min(news_count / max_news_count, 1.0)
                market_data["inflation_rate"] = min(news_count / max_news_count, 1.0)
                market_data["economic_stagnation"] = min(news_count / max_news_count, 1.0)
            
            # 위완수한표한 (빈부격차)
            if "위완수한표한" in taeum:
                news_count = len(taeum["위완수한표한"])
                market_data["real_economy_difficulty"] = min(news_count / max_news_count, 1.0)
                market_data["asset_market_cooling"] = min(news_count / max_news_count, 1.0)
                market_data["wealth_gap_index"] = min(news_count / max_news_count, 1.0)
        
        # 소양인
        if "소양인" in pathology_news:
            soyang = pathology_news["소양인"]
            
            # 망음증 (유동성 고갈)
            if "망음증" in soyang:
                news_count = len(soyang["망음증"])
                market_data["liquidity_crisis"] = min(news_count / max_news_count, 1.0)
                market_data["credit_crunch"] = min(news_count / max_news_count, 1.0)
                market_data["debt_crisis"] = min(news_count / max_news_count, 1.0)
            
            # 등척소장병 (공급망 붕괴)
            if "등척소장병" in soyang:
                news_count = len(soyang["등척소장병"])
                market_data["supply_chain_disruption"] = min(news_count / max_news_count, 1.0)
                market_data["shortage_index"] = min(news_count / max_news_count, 1.0)
        
        # 소음인
        if "소음인" in pathology_news:
            soeum = pathology_news["소음인"]
            
            # 망양증
            if "망양증" in soeum:
                news_count = len(soeum["망양증"])
                market_data["fake_recovery_index"] = min(news_count / max_news_count, 1.0)
                market_data["liquidity_flood"] = min(news_count / max_news_count, 1.0)
                market_data["real_economy_freeze"] = min(news_count / max_news_count, 1.0)
                market_data["fear_index"] = min(news_count / max_news_count, 1.0)
                market_data["panic_index"] = min(news_count / max_news_count, 1.0)
        
        return market_data


async def main():
    """테스트 함수"""
    collector = ApocalypseNewsCollector()
    
    print("\n📰 병증 뉴스 수집 중...")
    pathology_news = collector.collect_pathology_news(days=7, limit_per_keyword=10)
    
    print(f"\n✅ 수집 완료:")
    for constitution, pathologies in pathology_news.items():
        for pathology, news_list in pathologies.items():
            print(f"   {constitution} {pathology}: {len(news_list)}개")
    
    print("\n📊 시장 데이터 변환 중...")
    market_data = collector.aggregate_news_to_market_data(pathology_news)
    
    print(f"\n✅ 변환 완료:")
    print(f"   태양인 상한: {market_data['geopolitical_risk']:.2f}")
    print(f"   태음인 배추표병: {market_data['stagflation_index']:.2f}")
    print(f"   소양인 망음증: {market_data['liquidity_crisis']:.2f}")
    print(f"   소음인 망양증: {market_data['fake_recovery_index']:.2f}")
    
    return pathology_news, market_data


if __name__ == "__main__":
    asyncio.run(main())

