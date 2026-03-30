#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Historical Pattern Analyzer (역사적 패턴 분석기)

30년 데이터를 활용한 역사적 이벤트 패턴 분석:
- 닷컴 버블 (2000)
- 금융 위기 (2008)
- 팬데믹 (2020)
- 비트코인 반감기 주기

작성일: 2026-02-14
버전: v1.0
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class HistoricalPatternAnalyzer:
    """
    역사적 패턴 분석기
    
    30년 데이터를 활용하여 거대한 부의 이전 패턴을 분석
    """
    
    # 역사적 이벤트 정의
    HISTORICAL_EVENTS = {
        "2000-DOTCOM-BUBBLE": {
            "date": datetime(2000, 3, 10),  # NASDAQ 최고점
            "description": "닷컴 버블 붕괴",
            "type": "bubble_burst",
            "expected_4d": {
                "S": 0.300,  # 극도의 공포
                "L": 0.387,  # 급격한 하락 패턴
                "K": 0.850,  # 거시 경제 충격
                "M": 0.300   # 유동성 급감
            }
        },
        "2008-FINANCIAL-CRISIS": {
            "date": datetime(2008, 9, 15),  # 리먼 브라더스 파산
            "description": "금융 위기",
            "type": "financial_crisis",
            "expected_4d": {
                "S": 0.200,  # 극도의 공포
                "L": 0.400,  # 급격한 하락
                "K": 0.900,  # 거시 경제 충격
                "M": 0.200   # 유동성 급감
            }
        },
        "2020-PANDEMIC": {
            "date": datetime(2020, 3, 23),  # 시장 최저점
            "description": "팬데믹 충격",
            "type": "pandemic",
            "expected_4d": {
                "S": 0.250,  # 공포
                "L": 0.350,  # 급격한 변동
                "K": 0.800,  # 거시 경제 충격
                "M": 0.300   # 유동성 변동
            }
        },
        "2024-BITCOIN-HALVING": {
            "date": datetime(2024, 4, 20),  # 4차 반감기
            "description": "비트코인 4차 반감기",
            "type": "halving",
            "expected_4d": {
                "S": 0.400,  # 기대감
                "L": 0.300,  # 안정적 패턴
                "K": 0.600,  # 공급 감소
                "M": 0.500   # 거래량 증가
            }
        }
    }
    
    def __init__(
        self,
        multi_layer_timeline,
        sovereign_data_infusion=None
    ):
        """
        Args:
            multi_layer_timeline: MultiLayerTimeline 인스턴스
            sovereign_data_infusion: SovereignDataInfusion 인스턴스 (선택적)
        """
        self.multi_layer = multi_layer_timeline
        self.sovereign_data = sovereign_data_infusion
        
        logger.info("✅ Historical Pattern Analyzer 초기화 완료")
        logger.info(f"   분석 대상 이벤트: {len(self.HISTORICAL_EVENTS)}개")
    
    def analyze_event(
        self,
        event_name: str,
        price_data: Optional[pd.DataFrame] = None,
        days_before: int = 30,
        days_after: int = 30
    ) -> Dict[str, Any]:
        """
        역사적 이벤트 분석
        
        Args:
            event_name: 이벤트 이름 (예: "2000-DOTCOM-BUBBLE")
            price_data: 가격 데이터 (선택적)
            days_before: 이벤트 전 분석 기간 (일)
            days_after: 이벤트 후 분석 기간 (일)
        
        Returns:
            분석 결과
        """
        try:
            if event_name not in self.HISTORICAL_EVENTS:
                logger.warning(f"⚠️ 알 수 없는 이벤트: {event_name}")
                return {}
            
            event = self.HISTORICAL_EVENTS[event_name]
            event_date = event["date"]
            
            logger.info(f"\n🏛️ 역사적 이벤트 분석: {event_name}")
            logger.info(f"   날짜: {event_date.date()}")
            logger.info(f"   설명: {event['description']}")
            
            # 이벤트 시점의 4D 벡터 계산
            if self.multi_layer and price_data is not None:
                # 이벤트 시점의 데이터 추출
                event_start = event_date - timedelta(days=days_before)
                event_end = event_date + timedelta(days=days_after)
                
                event_data = price_data[
                    (price_data.index >= event_start) & 
                    (price_data.index <= event_end)
                ]
                
                if len(event_data) > 0:
                    # 이벤트 시점의 4D 벡터 계산
                    current_price = event_data.loc[event_date, 'close'] if event_date in event_data.index else event_data['close'].iloc[0]
                    
                    # 이벤트 전 데이터로 4D 벡터 계산
                    before_data = price_data[price_data.index < event_date].tail(365)  # 1년 전 데이터
                    
                    if len(before_data) > 0:
                        calculated_4d = self.multi_layer.calculate_hybrid_4d_vector(
                            current_date=event_date,
                            price_data=before_data,
                            macro_weight=0.2,
                            core_weight=0.6,
                            edge_weight=0.2
                        )
                        
                        # 예상 4D 벡터와 비교
                        expected_4d = event["expected_4d"]
                        
                        # 유사도 계산 (코사인 유사도)
                        similarity = self._calculate_similarity(
                            calculated_4d,
                            expected_4d
                        )
                        
                        # 위상차 계산 (일 단위)
                        phase_diff = self._calculate_phase_difference(
                            event_date,
                            calculated_4d,
                            expected_4d
                        )
                        
                        result = {
                            "event_name": event_name,
                            "event_date": event_date.isoformat(),
                            "description": event["description"],
                            "type": event["type"],
                            "calculated_4d": calculated_4d,
                            "expected_4d": expected_4d,
                            "similarity": similarity,
                            "phase_difference_days": phase_diff,
                            "analysis_period": {
                                "before": days_before,
                                "after": days_after
                            }
                        }
                        
                        logger.info(f"\n📊 분석 결과:")
                        logger.info(f"   계산된 4D: S={calculated_4d['S']:.3f}, L={calculated_4d['L']:.3f}, K={calculated_4d['K']:.3f}, M={calculated_4d['M']:.3f}")
                        logger.info(f"   예상 4D: S={expected_4d['S']:.3f}, L={expected_4d['L']:.3f}, K={expected_4d['K']:.3f}, M={expected_4d['M']:.3f}")
                        logger.info(f"   유사도: {similarity:.2%}")
                        logger.info(f"   위상차: {phase_diff}일")
                        
                        return result
                    else:
                        logger.warning(f"⚠️ 이벤트 전 데이터가 부족합니다: {event_name}")
                        return {}
                else:
                    logger.warning(f"⚠️ 이벤트 시점 데이터가 없습니다: {event_name}")
                    return {}
            else:
                logger.warning(f"⚠️ Multi-Layer Timeline 또는 가격 데이터가 없습니다")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 이벤트 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def analyze_all_events(
        self,
        price_data: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """
        모든 역사적 이벤트 분석
        
        Args:
            price_data: 가격 데이터 (선택적)
        
        Returns:
            분석 결과 리스트
        """
        results = []
        
        for event_name in self.HISTORICAL_EVENTS.keys():
            result = self.analyze_event(
                event_name=event_name,
                price_data=price_data
            )
            if result:
                results.append(result)
        
        return results
    
    def _calculate_similarity(
        self,
        vector1: Dict[str, float],
        vector2: Dict[str, float]
    ) -> float:
        """
        벡터 유사도 계산 (코사인 유사도)
        
        Args:
            vector1: 첫 번째 벡터
            vector2: 두 번째 벡터
        
        Returns:
            유사도 (0.0 ~ 1.0)
        """
        try:
            # 벡터 정규화
            v1 = np.array([vector1.get("S", 0), vector1.get("L", 0), vector1.get("K", 0), vector1.get("M", 0)])
            v2 = np.array([vector2.get("S", 0), vector2.get("L", 0), vector2.get("K", 0), vector2.get("M", 0)])
            
            # 코사인 유사도
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 > 0 and norm2 > 0:
                similarity = dot_product / (norm1 * norm2)
                return max(0.0, min(1.0, similarity))
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"⚠️ 유사도 계산 실패: {e}")
            return 0.0
    
    def _calculate_phase_difference(
        self,
        event_date: datetime,
        calculated_4d: Dict[str, float],
        expected_4d: Dict[str, float]
    ) -> int:
        """
        위상차 계산 (일 단위)
        
        Args:
            event_date: 이벤트 날짜
            calculated_4d: 계산된 4D 벡터
            expected_4d: 예상 4D 벡터
        
        Returns:
            위상차 (일)
        """
        try:
            # 벡터 차이 계산
            diff = {
                "S": abs(calculated_4d.get("S", 0) - expected_4d.get("S", 0)),
                "L": abs(calculated_4d.get("L", 0) - expected_4d.get("L", 0)),
                "K": abs(calculated_4d.get("K", 0) - expected_4d.get("K", 0)),
                "M": abs(calculated_4d.get("M", 0) - expected_4d.get("M", 0))
            }
            
            # 평균 차이를 일 단위로 변환 (임의의 스케일)
            avg_diff = sum(diff.values()) / len(diff)
            phase_diff = int(avg_diff * 100)  # 스케일 조정
            
            return phase_diff
            
        except Exception as e:
            logger.warning(f"⚠️ 위상차 계산 실패: {e}")
            return 0
    
    def predict_similar_event(
        self,
        current_4d: Dict[str, float],
        threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        유사한 역사적 이벤트 예측
        
        Args:
            current_4d: 현재 4D 벡터
            threshold: 유사도 임계값
        
        Returns:
            가장 유사한 이벤트 정보
        """
        try:
            best_match = None
            best_similarity = 0.0
            
            for event_name, event in self.HISTORICAL_EVENTS.items():
                expected_4d = event["expected_4d"]
                similarity = self._calculate_similarity(current_4d, expected_4d)
                
                if similarity > best_similarity and similarity >= threshold:
                    best_similarity = similarity
                    best_match = {
                        "event_name": event_name,
                        "description": event["description"],
                        "type": event["type"],
                        "event_date": event["date"].isoformat(),
                        "similarity": similarity,
                        "expected_4d": expected_4d
                    }
            
            if best_match:
                logger.info(f"\n🔮 유사한 역사적 이벤트 예측:")
                logger.info(f"   이벤트: {best_match['event_name']}")
                logger.info(f"   설명: {best_match['description']}")
                logger.info(f"   유사도: {best_similarity:.2%}")
            
            return best_match
            
        except Exception as e:
            logger.error(f"❌ 이벤트 예측 실패: {e}")
            return None

