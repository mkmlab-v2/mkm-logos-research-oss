#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 위상 공간 나우캐스터 (Phase Space Nowcaster)

목적: 예언이 아닌 나우캐스팅 (현재 위상 추적)
- DTW 기반 역사적 패턴 매칭
- Divine Centroid(0.25) 거리 실시간 추적
- 시나리오 확률 계산

작성일: 2026-01-12
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import math
import logging

# 워크스페이스 루트
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "src" / "analysis"))
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))

# 통합 동역학 엔진 import
try:
    from unified_dynamics_engine import UnifiedDynamicsEngine
    UNIFIED_ENGINE_AVAILABLE = True
except ImportError:
    UNIFIED_ENGINE_AVAILABLE = False
    print("⚠️ UnifiedDynamicsEngine 없음, 기본 로직 사용", file=sys.stderr)

# DTW 라이브러리 (선택적)
try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    DTW_AVAILABLE = True
except ImportError:
    try:
        from dtw import dtw
        DTW_AVAILABLE = True
    except ImportError:
        DTW_AVAILABLE = False
        print("⚠️ DTW 라이브러리 미설치. pip install fastdtw 또는 dtw-python 필요")

logger = logging.getLogger(__name__)

# ============================================
# 🏛️ 성경 데이터 상수 (2026-01-18 정정 완료)
# ============================================

# Divine Centroid (이상적 목표 평형점)
DIVINE_CENTROID = {
    "S": 0.249834,
    "L": 0.249714,
    "K": 0.250699,
    "M": 0.249754
}

# 실제 성경 31,102구절의 평균 벡터값 (2026-01-07 통찰 반영)
# ⚠️ Divine Centroid는 목표 평형점이며, 실제 성경 평균값이 아님
ACTUAL_BIBLE_AVERAGE = {
    "S": 0.8555,
    "L": 0.8604,
    "K": 0.6422,
    "M": 0.8089
}

# 성경 고유 위상 오프셋 (목표 평형점과 실제 평균 사이의 회전 각도)
# 이 각도는 "지혜의 기울기" 또는 "영적 전압"을 의미
BIBLE_PHASE_OFFSET_DEGREES = 11.10  # 도(degree)
BIBLE_PHASE_OFFSET_RADIANS = math.radians(11.10)  # 라디안


class PhaseSpaceNowcaster:
    """
    위상 공간 나우캐스터
    
    목적: 예언이 아닌 현재 위상 추적 및 패턴 매칭
    """
    
    def __init__(self, history_size: int = 1000, enable_unified_engine: bool = True):
        """
        Args:
            history_size: 거리 히스토리 최대 크기
            enable_unified_engine: 통합 동역학 엔진 활성화 여부
        """
        self.history_size = history_size
        self.distance_history = deque(maxlen=history_size)
        self.vector_history = deque(maxlen=history_size)  # 4D 벡터 히스토리
        
        # 거리 변화 추적
        self.velocity = 0.0  # 거리 변화 속도
        self.acceleration = 0.0  # 거리 변화 가속도
        
        # 역사적 템플릿 (패턴 매칭용)
        self.historical_templates = self._load_historical_templates()
        
        # 🚀 태양인 소수성 가중치 (Phase 2) - 2026-01-18 추가
        # MKM12 예측 모델 업그레이드 보고서 참조
        self.population_weights = {
            '태양인': 1000.0,   # 압도적으로 높은 가중치
            '태음인': 2.55,
            '소양인': 2.97,
            '소음인': 3.69
        }
        
        # 🚀 체질 분석 엔진 연동 (2026-01-18 추가)
        self.enable_constitution_analysis = True
        self.constitution_detector = None
        try:
            from sasang_constitution_crisis_detector import SasangConstitutionCrisisDetector
            self.constitution_detector = SasangConstitutionCrisisDetector()
            logger.info("✅ 체질 분석 엔진 연동 완료")
        except ImportError:
            logger.warning("⚠️ 체질 분석 엔진 임포트 실패, 기본값 사용")
            self.enable_constitution_analysis = False
        
        self.risk_weights = {
            '태양인': {
                '정신_차원': 1.5,    # 높음 - 도전, 혁신
                '물질_차원': 1.8,    # 높음 - 외상/사고 위험
                '리더십_성향': 2.0,  # 매우 높음 - 리더십 잠재력
                '위험_감수': 1.7     # 높음 - 선구자적 역할
            },
            '태음인': {
                '정신_차원': 1.0,
                '물질_차원': 1.0,
                '리더십_성향': 1.0,
                '위험_감수': 1.0
            },
            '소양인': {
                '정신_차원': 1.2,
                '물질_차원': 1.1,
                '리더십_성향': 1.3,
                '위험_감수': 1.2
            },
            '소음인': {
                '정신_차원': 0.8,    # 낮음 - 보존적 특성
                '물질_차원': 0.6,    # 낮음 - 안전 선호
                '리더십_성향': 0.7,  # 낮음 - 내향적 특성
                '위험_감수': 0.5     # 낮음 - 안전한 환경 선호
            }
        }
        
        # 통합 동역학 엔진 (병증 + 성경 + 명리)
        self.unified_engine = None
        if enable_unified_engine and UNIFIED_ENGINE_AVAILABLE:
            try:
                self.unified_engine = UnifiedDynamicsEngine(
                    enable_fire_hydrophobicity=True,
                    enable_logos_forecast=True
                )
                logger.info("✅ UnifiedDynamicsEngine 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ UnifiedDynamicsEngine 초기화 실패: {e}")
                self.unified_engine = None
    
    def _load_historical_templates(self) -> Dict[str, List[Dict[str, float]]]:
        """
        역사적 위기 패턴 템플릿 로드 (성경적 멸망 패턴 포함)
        
        Returns:
            템플릿 딕셔너리 (이름: 4D 벡터 궤적)
        """
        # 실제 구현 시: 데이터베이스나 파일에서 로드
        # 현재는 샘플 템플릿
        
        templates = {
            # 역사적 패턴
            "1929_crash": [
                # 대공황 직전 패턴 (30일)
                {"S": 0.15, "L": 0.20, "K": 0.35, "M": 0.30},  # Day -30
                {"S": 0.18, "L": 0.22, "K": 0.38, "M": 0.22},  # Day -25
                {"S": 0.20, "L": 0.25, "K": 0.40, "M": 0.15},  # Day -20
                {"S": 0.22, "L": 0.28, "K": 0.42, "M": 0.08},  # Day -15
                {"S": 0.25, "L": 0.30, "K": 0.45, "M": 0.00},  # Day -10
                {"S": 0.28, "L": 0.32, "K": 0.48, "M": 0.00},  # Day -5
                {"S": 0.30, "L": 0.35, "K": 0.50, "M": 0.00},  # Day 0 (붕괴)
            ],
            "2008_crisis": [
                # 금융위기 직전 패턴
                {"S": 0.20, "L": 0.18, "K": 0.32, "M": 0.30},
                {"S": 0.22, "L": 0.20, "K": 0.35, "M": 0.23},
                {"S": 0.25, "L": 0.22, "K": 0.38, "M": 0.15},
                {"S": 0.28, "L": 0.25, "K": 0.40, "M": 0.07},
                {"S": 0.30, "L": 0.28, "K": 0.42, "M": 0.00},
            ],
            "2020_covid": [
                # 코로나 붕괴 패턴
                {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},  # 정상
                {"S": 0.30, "L": 0.20, "K": 0.35, "M": 0.15},  # 초기 경고
                {"S": 0.35, "L": 0.15, "K": 0.40, "M": 0.10},  # 위기
                {"S": 0.40, "L": 0.10, "K": 0.45, "M": 0.05},  # 붕괴
            ],
            "2017_bitcoin_bubble": [
                # 비트코인 버블 패턴
                {"S": 0.15, "L": 0.25, "K": 0.30, "M": 0.30},
                {"S": 0.20, "L": 0.25, "K": 0.35, "M": 0.20},
                {"S": 0.25, "L": 0.25, "K": 0.40, "M": 0.10},
                {"S": 0.30, "L": 0.25, "K": 0.45, "M": 0.00},
            ],
            # 성경적 멸망 패턴 (로고스 예보 시스템)
            "babylon_destruction": [
                # 바벨론 멸망 패턴: 권력(M)과 물질(M)이 극대화되고 정신(S)이 0에 수렴하는 '교만의 붕괴 궤적'
                {"S": 0.30, "L": 0.25, "K": 0.20, "M": 0.25},  # 초기: 정신(S) 약간 높음
                {"S": 0.25, "L": 0.25, "K": 0.20, "M": 0.30},  # 교만 시작: 물질(M) 증가
                {"S": 0.20, "L": 0.25, "K": 0.20, "M": 0.35},  # 교만 심화: 물질(M) 계속 증가
                {"S": 0.15, "L": 0.25, "K": 0.20, "M": 0.40},  # 위기: 정신(S) 급락
                {"S": 0.10, "L": 0.25, "K": 0.20, "M": 0.45},  # 붕괴 직전: 정신(S) 거의 0
                {"S": 0.05, "L": 0.20, "K": 0.15, "M": 0.60},  # 붕괴: 정신(S) 0, 물질(M) 폭주
                {"S": 0.00, "L": 0.10, "K": 0.10, "M": 0.80},  # 멸망: 완전한 정신 상실
            ],
            "sodom_destruction": [
                # 소돔 멸망 패턴: 윤리적 논리(L)가 완전히 무너지고 말초적 에너지(M)만 폭주하는 '심판의 위상'
                {"S": 0.20, "L": 0.30, "K": 0.25, "M": 0.25},  # 초기: 논리(L) 정상
                {"S": 0.20, "L": 0.25, "K": 0.25, "M": 0.30},  # 논리(L) 약화 시작
                {"S": 0.20, "L": 0.20, "K": 0.25, "M": 0.35},  # 논리(L) 급락
                {"S": 0.20, "L": 0.15, "K": 0.25, "M": 0.40},  # 위기: 논리(L) 거의 0
                {"S": 0.20, "L": 0.10, "K": 0.20, "M": 0.50},  # 붕괴 직전: 논리(L) 완전 붕괴
                {"S": 0.15, "L": 0.05, "K": 0.15, "M": 0.65},  # 멸망: 논리(L) 0, 물질(M) 폭주
            ],
            "nineveh_recovery": [
                # 니느웨 회복 패턴: 파국 직전, 급격한 위상 반전(회개)을 통해 멸망 궤도에서 이탈하는 '기적의 회복'
                {"S": 0.10, "L": 0.20, "K": 0.20, "M": 0.50},  # 파국 직전: 정신(S) 거의 0
                {"S": 0.15, "L": 0.25, "K": 0.25, "M": 0.35},  # 회개 시작: 정신(S) 상승
                {"S": 0.25, "L": 0.30, "K": 0.25, "M": 0.20},  # 회복 진행: 정신(S) 급상승
                {"S": 0.30, "L": 0.30, "K": 0.25, "M": 0.15},  # 회복 완료: 평형 회귀
                {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},  # 평형: Divine Centroid 수렴
            ],
        }
        
        return templates
    
    def update_phase_vector(
        self,
        vector_4d: Dict[str, float],
        timestamp: Optional[datetime] = None,
        myeongri_gapja: Optional[str] = None,
        enable_unified_processing: bool = True
    ):
        """
        위상 벡터 업데이트 및 거리 계산 (통합 동역학 엔진 통합)
        
        Args:
            vector_4d: 4D 위상 벡터 (S, L, K, M)
            timestamp: 타임스탬프 (None이면 현재 시간)
            myeongri_gapja: 명리 60갑자 (선택적, 화(火) 소수성 처리용)
            enable_unified_processing: 통합 동역학 엔진 처리 활성화
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 통합 동역학 엔진 처리 (병증 + 성경 + 명리)
        if enable_unified_processing and self.unified_engine and myeongri_gapja:
            try:
                unified_result = self.unified_engine.unify_three_axes(
                    pathology_vector=vector_4d,  # 현재 벡터를 병증 벡터로 사용
                    biblical_vector=None,  # 성경 벡터는 별도 처리
                    myeongri_gapja=myeongri_gapja,
                    domain="stock_volatile"  # 코인/주식 도메인
                )
                
                # 통합 벡터로 업데이트
                vector_4d = unified_result["unified_vector"]
                
                # 화(火) 정보 저장
                if unified_result.get("fire_info"):
                    vector_4d["fire_detected"] = unified_result["fire_info"].get("fire_detected", False)
                    vector_4d["fire_intensity"] = unified_result["fire_info"].get("fire_intensity", 0.0)
            except Exception as e:
                logger.warning(f"⚠️ 통합 동역학 엔진 처리 실패: {e}")
        
        # Divine Centroid와의 거리 계산
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
        
        distance = float(np.linalg.norm(current_vector - divine_vector))
        
        # 히스토리 업데이트
        self.vector_history.append({
            "vector": vector_4d,
            "timestamp": timestamp
        })
        
        self.distance_history.append({
            "distance": distance,
            "timestamp": timestamp
        })
        
        # 속도/가속도 계산
        self._update_velocity_acceleration()
    
    def _update_velocity_acceleration(self):
        """거리 변화 속도/가속도 계산"""
        if len(self.distance_history) >= 2:
            # 속도 계산 (거리 변화율)
            prev_distance = self.distance_history[-2]["distance"]
            current_distance = self.distance_history[-1]["distance"]
            self.velocity = current_distance - prev_distance
            
        if len(self.distance_history) >= 3:
            # 가속도 계산 (속도 변화율)
            prev_prev_distance = self.distance_history[-3]["distance"]
            prev_distance = self.distance_history[-2]["distance"]
            prev_velocity = prev_distance - prev_prev_distance
            self.acceleration = self.velocity - prev_velocity
    
    def match_historical_patterns(
        self,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        현재 궤적과 역사적 패턴 매칭 (DTW)
        
        Args:
            window_days: 비교할 최근 일수
            
        Returns:
            패턴 매칭 결과
        """
        if not DTW_AVAILABLE:
            logger.warning("⚠️ DTW 라이브러리 미설치, 패턴 매칭 불가")
            return {"error": "DTW 라이브러리 미설치"}
        
        if len(self.vector_history) < window_days:
            logger.warning(f"⚠️ 히스토리 부족 ({len(self.vector_history)} < {window_days})")
            return {"error": "히스토리 부족"}
        
        # 최근 궤적 추출
        recent_trajectory = []
        for entry in list(self.vector_history)[-window_days:]:
            vec = entry["vector"]
            recent_trajectory.append([
                vec.get("S", 0.25),
                vec.get("L", 0.25),
                vec.get("K", 0.25),
                vec.get("M", 0.25)
            ])
        
        # 각 템플릿과 비교
        pattern_matches = {}
        
        for template_name, template_vectors in self.historical_templates.items():
            # 템플릿을 배열로 변환
            template_array = []
            for vec in template_vectors:
                template_array.append([
                    vec.get("S", 0.25),
                    vec.get("L", 0.25),
                    vec.get("K", 0.25),
                    vec.get("M", 0.25)
                ])
            
            # DTW 거리 계산
            try:
                if 'fastdtw' in globals():
                    distance, path = fastdtw(recent_trajectory, template_array, dist=euclidean)
                else:
                    # dtw-python 사용
                    alignment = dtw(recent_trajectory, template_array)
                    distance = alignment.distance
                
                # 유사도 변환 (거리 → 유사도)
                # 정규화: 최대 거리 1.0 가정
                max_distance = np.sqrt(4) * len(template_array)  # 4D, 최대 거리
                similarity = 1.0 / (1.0 + distance / max_distance)
                
                # 🚀 11.10도 오프셋 반영 (성경적 패턴 매칭 강화) - 2026-01-18 추가
                # 성경적 패턴의 경우 실제 성경 평균값과의 거리도 계산
                is_biblical_pattern = template_name in ["babylon_destruction", "sodom_destruction", "nineveh_recovery"]
                bible_distance = None
                phase_offset_similarity = None
                
                if is_biblical_pattern:
                    # 현재 궤적의 평균 벡터 계산
                    current_avg_vector = np.mean(recent_trajectory, axis=0)
                    actual_bible_avg = np.array([
                        ACTUAL_BIBLE_AVERAGE["S"],
                        ACTUAL_BIBLE_AVERAGE["L"],
                        ACTUAL_BIBLE_AVERAGE["K"],
                        ACTUAL_BIBLE_AVERAGE["M"]
                    ])
                    
                    # 실제 성경 평균과의 거리 계산
                    bible_distance = float(np.linalg.norm(current_avg_vector - actual_bible_avg))
                    
                    # 11.10도 오프셋을 고려한 위상 유사도 보정
                    # 성경 데이터는 11.10도 기울어진 고에너지 상태이므로, 이를 반영
                    offset_factor = 1.0 - (bible_distance / 1.0)  # 거리가 가까울수록 높은 보정
                    phase_offset_similarity = similarity * (1.0 + offset_factor * 0.1)  # 최대 10% 보정
                    phase_offset_similarity = min(1.0, phase_offset_similarity)
                
                # 현재 위상 판정
                current_distance = self.distance_history[-1]["distance"]
                if current_distance >= 0.4:
                    phase = "critical"
                elif current_distance >= 0.3:
                    phase = "warning"
                elif current_distance >= 0.2:
                    phase = "early_warning"
                else:
                    phase = "normal"
                
                pattern_matches[template_name] = {
                    "similarity": float(phase_offset_similarity if phase_offset_similarity is not None else similarity),
                    "dtw_distance": float(distance),
                    "phase": phase,
                    "current_distance": float(current_distance),
                    "bible_distance": float(bible_distance) if bible_distance is not None else None,  # 성경 평균과의 거리
                    "phase_offset_applied": is_biblical_pattern  # 오프셋 적용 여부
                }
                
            except Exception as e:
                logger.error(f"⚠️ 템플릿 '{template_name}' 매칭 실패: {e}")
                continue
        
        # 유사도 순으로 정렬
        sorted_matches = sorted(
            pattern_matches.items(),
            key=lambda x: x[1]["similarity"],
            reverse=True
        )
        
        return {
            "pattern_matches": dict(sorted_matches),
            "highest_match": {
                "template": sorted_matches[0][0] if sorted_matches else None,
                "similarity": sorted_matches[0][1]["similarity"] if sorted_matches else 0.0,
                "interpretation": self._interpret_pattern_match(
                    sorted_matches[0][0] if sorted_matches else None,
                    sorted_matches[0][1]["similarity"] if sorted_matches else 0.0
                )
            }
        }
    
    def _interpret_pattern_match(
        self,
        template_name: Optional[str],
        similarity: float
    ) -> str:
        """패턴 매칭 해석 (성경적 멸망 패턴 포함)"""
        if template_name is None:
            return "패턴 매칭 없음"
        
        interpretations = {
            # 역사적 패턴
            "1929_crash": "1929년 대공황 직전 패턴",
            "2008_crisis": "2008년 금융위기 직전 패턴",
            "2020_covid": "2020년 코로나 붕괴 패턴",
            "2017_bitcoin_bubble": "2017년 비트코인 버블 패턴",
            # 성경적 멸망 패턴 (로고스 예보)
            "babylon_destruction": "바벨론 멸망 패턴: 교만의 붕괴 궤적 (권력과 물질이 극대화되고 정신이 0에 수렴)",
            "sodom_destruction": "소돔 멸망 패턴: 심판의 위상 (윤리적 논리가 완전히 무너지고 말초적 에너지만 폭주)",
            "nineveh_recovery": "니느웨 회복 패턴: 기적의 회복 (파국 직전, 급격한 위상 반전을 통해 멸망 궤도에서 이탈)"
        }
        
        base_interpretation = interpretations.get(template_name, template_name)
        
        # 성경적 패턴에 대한 특별 경고
        is_biblical_destruction = template_name in ["babylon_destruction", "sodom_destruction"]
        is_biblical_recovery = template_name == "nineveh_recovery"
        
        if similarity >= 0.9:
            if is_biblical_destruction:
                return f"🚨 로고스 경고: 현재 위상이 {base_interpretation}과 매우 유사함 (유사도 {similarity:.1%}) - 멸망 궤적 진입!"
            elif is_biblical_recovery:
                return f"✨ 로고스 희망: 현재 위상이 {base_interpretation}과 매우 유사함 (유사도 {similarity:.1%}) - 회복 가능성!"
            else:
                return f"현재 위상이 {base_interpretation}과 매우 유사함 (유사도 {similarity:.1%})"
        elif similarity >= 0.7:
            if is_biblical_destruction:
                return f"⚠️ 로고스 경고: 현재 위상이 {base_interpretation}과 유사함 (유사도 {similarity:.1%}) - 주의 필요!"
            elif is_biblical_recovery:
                return f"💡 로고스 희망: 현재 위상이 {base_interpretation}과 유사함 (유사도 {similarity:.1%}) - 회복 기회!"
            else:
                return f"현재 위상이 {base_interpretation}과 유사함 (유사도 {similarity:.1%})"
        elif similarity >= 0.5:
            return f"현재 위상이 {base_interpretation}과 부분적으로 유사함 (유사도 {similarity:.1%})"
        else:
            return f"현재 위상이 {base_interpretation}과 유사도 낮음 (유사도 {similarity:.1%})"
    
    def predict_scenarios(
        self,
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        시나리오 확률 예측
        
        Args:
            horizon_days: 예측 기간 (일)
            
        Returns:
            시나리오별 확률
        """
        if len(self.distance_history) < 3:
            return {
                "error": "히스토리 부족",
                "scenarios": {
                    "A_convergence": {"probability": 0.33},
                    "B_current_trend": {"probability": 0.34},
                    "C_collapse": {"probability": 0.33}
                }
            }
        
        current_dist = self.distance_history[-1]["distance"]
        
        # 시나리오 A: 평형 회귀 (0.25 수렴)
        if self.velocity < 0:
            # 거리 감소 중 (평형 회귀)
            convergence_prob = min(1.0, abs(self.velocity) * horizon_days / max(current_dist, 0.01))
        else:
            # 거리 증가 중 (이탈)
            convergence_prob = 0.0
        
        # 가속도 보정
        if self.acceleration < 0:
            # 감속 중 (회귀 가속)
            convergence_prob *= 1.2
        
        convergence_prob = min(1.0, max(0.0, convergence_prob))
        
        # 시나리오 B: 현재 추세 지속
        current_trend_prob = 1.0 - convergence_prob * 0.7
        
        # 시나리오 C: 붕괴 (거리 0.5 돌파)
        collapse_prob = max(0.0, (current_dist - 0.3) * 0.5) if current_dist > 0.3 else 0.0
        
        # 정규화 (합이 1.0이 되도록)
        total = convergence_prob + current_trend_prob + collapse_prob
        if total > 0:
            convergence_prob /= total
            current_trend_prob /= total
            collapse_prob /= total
        
        return {
            "scenarios": {
                "A_convergence": {
                    "probability": float(convergence_prob),
                    "description": "평형 회귀 (0.25 수렴)",
                    "conditions": ["금리 안정", "기술 윤리 확보", "정책 조정"],
                    "timeline": f"{horizon_days}-{horizon_days*3}일 내"
                },
                "B_current_trend": {
                    "probability": float(current_trend_prob),
                    "description": "현재 추세 지속",
                    "conditions": ["현재 정책 유지", "기술 발전 지속"],
                    "timeline": "즉시"
                },
                "C_collapse": {
                    "probability": float(collapse_prob),
                    "description": "비가역적 붕괴",
                    "conditions": ["거리 0.5 돌파", "패턴 매칭 95% 이상"],
                    "timeline": "불확실"
                }
            },
            "current_state": {
                "distance": float(current_dist),
                "velocity": float(self.velocity),
                "acceleration": float(self.acceleration)
            }
        }
    
    def get_nowcasting_report(self, vix_value: Optional[float] = None) -> Dict[str, Any]:
        """
        나우캐스팅 리포트 생성
        
        Args:
            vix_value: VIX 지수 값 (있는 경우 위기 수준 판정에 직접 사용)
        
        Returns:
            종합 나우캐스팅 리포트
        """
        if len(self.vector_history) == 0:
            return {"error": "데이터 없음"}
        
        current_vector = self.vector_history[-1]["vector"]
        current_distance = self.distance_history[-1]["distance"]
        
        # 패턴 매칭
        pattern_match = self.match_historical_patterns(window_days=30)
        
        # 시나리오 예측
        scenarios = self.predict_scenarios(horizon_days=30)
        
        # 위기 신호 판정 (거리 + VIX 복합 판정)
        crisis_level = self._calculate_crisis_level(current_distance, vix_value, current_vector)
        
        # 로고스 예보 알람 (성경적 멸망/회복 패턴 감지)
        logos_warning = self._detect_logos_patterns(pattern_match, current_vector)
        
        # 🚀 Phase 3: 화기운 분석 추가 - 2026-01-18
        # 체질 점수는 실제 체질 분석 엔진에서 가져오기 (연동 완료)
        constitution_scores = self._get_constitution_scores(current_vector, vix_value)
        fire_analysis = self._detect_explosive_energy(current_vector, constitution_scores)
        
        return {
            "nowcasting": {
                "current_phase_vector": current_vector,
                "distance_to_centroid": current_distance,
                "distance_to_bible_avg": float(np.linalg.norm(np.array([
                    current_vector.get("S", 0.25),
                    current_vector.get("L", 0.25),
                    current_vector.get("K", 0.25),
                    current_vector.get("M", 0.25)
                ]) - np.array([
                    ACTUAL_BIBLE_AVERAGE["S"],
                    ACTUAL_BIBLE_AVERAGE["L"],
                    ACTUAL_BIBLE_AVERAGE["K"],
                    ACTUAL_BIBLE_AVERAGE["M"]
                ]))),  # 실제 성경 평균과의 거리 추가
                "distance_velocity": float(self.velocity),
                "distance_acceleration": float(self.acceleration),
                "vix_value": vix_value,
                "timestamp": datetime.now().isoformat()
            },
            "pattern_matching": pattern_match,
            "scenarios": scenarios.get("scenarios", {}),
            "crisis_level": crisis_level["level"],
            "crisis_reasoning": crisis_level["reasoning"],
            "logos_warning": logos_warning,  # 로고스 예보 알람 추가
            "fire_analysis": fire_analysis,  # 🚀 화기운 분석 추가
            "recommendation": {
                "action": crisis_level["level"],
                "confidence": scenarios.get("scenarios", {}).get("B_current_trend", {}).get("probability", 0.5),
                "reasoning": self._generate_reasoning(pattern_match, scenarios, current_distance, vix_value)
            }
        }
    
    def _calculate_crisis_level(
        self,
        distance: float,
        vix_value: Optional[float],
        vector_4d: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        위기 수준 계산 (거리 + VIX + 4D 벡터 복합 판정)
        
        Args:
            distance: Divine Centroid 거리
            vix_value: VIX 지수 값
            vector_4d: 현재 4D 벡터
        
        Returns:
            위기 수준 딕셔너리 (level, reasoning)
        """
        reasoning_parts = []
        
        # 1. VIX 직접 판정 (최우선)
        if vix_value is not None:
            if vix_value >= 70:
                return {
                    "level": "EMERGENCY_SELL",
                    "reasoning": f"VIX {vix_value:.1f} (극도 공포) - 즉시 매도 권고"
                }
            elif vix_value >= 50:
                return {
                    "level": "SELL",
                    "reasoning": f"VIX {vix_value:.1f} (높은 공포) - 매도 권고"
                }
            elif vix_value >= 30:
                reasoning_parts.append(f"VIX {vix_value:.1f} (중간 공포)")
        
        # 2. 거리 기반 판정 (임계값 조정: 0.2 → 0.15)
        if distance >= 0.4:
            level = "EMERGENCY_SELL"
            reasoning_parts.append(f"거리 {distance:.3f} (극도 이탈)")
        elif distance >= 0.3:
            level = "SELL"
            reasoning_parts.append(f"거리 {distance:.3f} (심각한 이탈)")
        elif distance >= 0.15:  # 임계값 조정: 0.2 → 0.15
            level = "REDUCE"
            reasoning_parts.append(f"거리 {distance:.3f} (경고 수준)")
        else:
            level = "HOLD"
            reasoning_parts.append(f"거리 {distance:.3f} (정상 범위)")
        
        # 3. 4D 벡터 기반 판정 (S 차원이 매우 낮으면 공포)
        s_value = vector_4d.get("S", 0.25)
        if s_value < 0.15:
            if level == "HOLD":
                level = "REDUCE"
            elif level == "REDUCE":
                level = "SELL"
            reasoning_parts.append(f"S 차원 {s_value:.3f} (극도 공포)")
        
        # 4. VIX + 거리 복합 판정
        if vix_value is not None and distance >= 0.15:
            if vix_value >= 40 and distance >= 0.15:
                if level in ["HOLD", "REDUCE"]:
                    level = "SELL"
                reasoning_parts.append("VIX + 거리 복합 판정: SELL")
            elif vix_value >= 30 and distance >= 0.2:
                if level == "HOLD":
                    level = "REDUCE"
                reasoning_parts.append("VIX + 거리 복합 판정: REDUCE")
        
        return {
            "level": level,
            "reasoning": " | ".join(reasoning_parts) if reasoning_parts else "정상 범위"
        }
    
    def _generate_reasoning(
        self,
        pattern_match: Dict[str, Any],
        scenarios: Dict[str, Any],
        current_distance: float,
        vix_value: Optional[float] = None
    ) -> str:
        """추천 사유 생성"""
        highest_match = pattern_match.get("highest_match", {})
        template = highest_match.get("template")
        similarity = highest_match.get("similarity", 0.0)
        
        scenario_b_prob = scenarios.get("scenarios", {}).get("B_current_trend", {}).get("probability", 0.5)
        
        reasoning_parts = []
        
        if template and similarity >= 0.7:
            reasoning_parts.append(f"현재 위상이 {template} 패턴과 {similarity:.1%} 유사")
        
        if current_distance >= 0.3:
            reasoning_parts.append(f"Divine Centroid로부터 거리 {current_distance:.3f} (위험 수준: HIGH)")
        elif current_distance >= 0.15:  # 임계값 조정: 0.2 → 0.15
            reasoning_parts.append(f"Divine Centroid로부터 거리 {current_distance:.3f} (경고 수준)")
        
        if scenario_b_prob >= 0.6:
            reasoning_parts.append(f"시나리오 B (현재 추세 지속) 확률 {scenario_b_prob:.1%}")
        
        # VIX 정보 추가 (있는 경우)
        if vix_value is not None:
            if vix_value >= 50:
                reasoning_parts.append(f"VIX {vix_value:.1f} (높은 공포)")
            elif vix_value >= 30:
                reasoning_parts.append(f"VIX {vix_value:.1f} (중간 공포)")
        
        if not reasoning_parts:
            reasoning_parts.append("데이터 부족으로 판단 보류")
        
        return " | ".join(reasoning_parts)
    
    def _detect_logos_patterns(
        self,
        pattern_match: Dict[str, Any],
        current_vector: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        로고스 예보 알람: 성경적 멸망/회복 패턴 감지
        
        Args:
            pattern_match: 패턴 매칭 결과
            current_vector: 현재 4D 벡터
        
        Returns:
            로고스 경고 정보
        """
        highest_match = pattern_match.get("highest_match", {})
        template_name = highest_match.get("template")
        similarity = highest_match.get("similarity", 0.0)
        
        # 성경적 멸망 패턴 감지
        biblical_destruction_patterns = ["babylon_destruction", "sodom_destruction"]
        biblical_recovery_patterns = ["nineveh_recovery"]
        
        warning_level = None
        warning_message = None
        fire_detected = current_vector.get("fire_detected", False)
        fire_intensity = current_vector.get("fire_intensity", 0.0)
        
        if template_name in biblical_destruction_patterns:
            # 멸망 패턴 감지
            if similarity >= 0.9:
                warning_level = "WARNING_LEVEL_3"  # 위험: 붕괴 직전
                warning_message = f"🚨 로고스적 파국이 임박했습니다. 모든 포지션을 정리하고 대피하십시오. ({template_name}, 유사도 {similarity:.1%})"
            elif similarity >= 0.7:
                warning_level = "WARNING_LEVEL_2"  # 경고: 임계점 도달
                warning_message = f"⚠️ 11.10도의 보정 에너지가 필요합니다. 위상 반전을 준비하십시오. ({template_name}, 유사도 {similarity:.1%})"
            elif similarity >= 0.5:
                warning_level = "WARNING_LEVEL_1"  # 주의: 궤적 진입 초기
                warning_message = f"💡 현재 흐름이 {template_name.replace('_', ' ').title()}의 길로 향하고 있습니다. (유사도 {similarity:.1%})"
        
        elif template_name in biblical_recovery_patterns:
            # 회복 패턴 감지
            if similarity >= 0.7:
                warning_level = "RECOVERY_SIGNAL"
                warning_message = f"✨ 회복의 기적이 시작되었습니다. 위상 반전의 기회입니다. ({template_name}, 유사도 {similarity:.1%})"
        
        # 화(火) 폭주 감지 (태양인 소수성 엔진) - Phase 3 통합
        fire_analysis = self._detect_explosive_energy(current_vector, {})
        if fire_analysis.get("is_explosive", False):
            fire_intensity = fire_analysis.get("fire_energy", 0.0) / fire_analysis.get("explosive_threshold", 1.0)
            if fire_intensity >= 0.5:
                if warning_level is None:
                    warning_level = "FIRE_OVERFLOW"
                    warning_message = f"🔥 화(火)의 폭주가 감지되었습니다. (강도: {fire_intensity:.1%}) - 로고스적 변곡점이 임박했습니다."
                else:
                    # 기존 경고에 화(火) 정보 추가
                    warning_message += f" + 화(火) 폭주 감지 (강도: {fire_intensity:.1%})"
        
        return {
            "warning_level": warning_level,
            "warning_message": warning_message,
            "template_name": template_name,
            "similarity": similarity,
            "fire_detected": fire_analysis.get("is_explosive", False),
            "fire_intensity": fire_analysis.get("fire_energy", 0.0) / fire_analysis.get("explosive_threshold", 1.0) if fire_analysis.get("explosive_threshold", 1.0) > 0 else 0.0,
            "timestamp": datetime.now().isoformat()
        }
    
    def _detect_explosive_energy(
        self,
        vector_4d: Dict[str, float],
        constitution_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        🚀 Phase 3: 폭발적 에너지 감지 (화기운 + 태양인 가중치)
        
        🏛️ 역추산 논리 (Reverse Inference):
        - 태양인의 소수성은 "결점"이 아니라, 화(火)를 보관하기 위해 선택한 "완벽한 단열재"
        - 폐국(금속 용기) 안에 화(불꽃)를 가두고 나면, 겉면은 차갑고 단단해짐 = 소수성
        - "안 섞이는 데이터(소수성)"를 만났을 때, 그것을 쓰레기가 아닌 "가장 귀한 보석(화기운/예언)"으로 대접
        
        원리:
        1. 소수성 = 보호막 (Protective Barrier)
           - 일반 데이터와 섞이지 않는 이유: 내부의 화(火) 에너지를 보호하기 위함
           - 폐국(금속 용기) = 보호막의 비유
        2. 화(火) 에너지 감지
           - 보호막 안의 화(火) 에너지를 정밀하게 측정
           - S 차원이 높을수록, 태양인 점수가 높을수록 화기운 증가
        3. 폭발 임계점 판정
           - 로고스적 임계점 도달 시 급등/급락 신호
        
        Args:
            vector_4d: 4D 위상 벡터
            constitution_scores: 체질별 점수 (태양인, 태음인, 소양인, 소음인)
        
        Returns:
            {
                "fire_energy": float,  # 화기운 수치 (보호막 안의 불꽃)
                "explosive_threshold": float,  # 폭발 임계점
                "is_explosive": bool,  # 폭발 직전 여부
                "recommendation": str,  # 매매 권장사항
                "hydrophobicity_level": float,  # 소수성 수준 (보호막 강도)
                "protection_status": str  # 보호막 상태
            }
        """
        # 태양인 가중치 적용 (소수성 = 보호막 강도)
        taeyang_score = constitution_scores.get("태양인", 0.0)
        taeyang_weight = self.population_weights.get('태양인', 1000.0)
        
        # 소수성 수준 계산 (보호막 강도)
        # 태양인 점수가 높을수록, 보호막이 강함
        # 태양인 점수가 0이면 기본값 사용 (⚠️ 실제 체질 분석 엔진 연동 필요)
        taeyang_score_effective = taeyang_score if taeyang_score > 0 else 0.1
        hydrophobicity_level = taeyang_score_effective
        
        # 화기운 계산 (S 차원 * 태양인 가중치 * 태양인 점수)
        # 보호막(폐국) 안의 화(火) 에너지를 정밀하게 측정
        s_value = vector_4d.get("S", 0.25)
        fire_energy = s_value * taeyang_weight * hydrophobicity_level
        
        # 🚨 폭발 임계점 동적 조정 (2026-01-18 개선)
        # 최적화 결과: 권장 배율 0.012 (기존 0.1에서 약 1/8로 낮춤)
        # 최적화 결과: Precision 30.68%, Recall 93.10%, F1-Score 46.15%
        # 기존: 0.1 (10%) → 개선: 0.012 (1.2%)
        # 동적 조정: 시장 변동성 기반 임계점 조정
        base_multiplier = 0.012  # 기본 배율
        
        # 시장 변동성 기반 동적 조정 (S 차원의 변동성 반영)
        s_value = vector_4d.get("S", 0.25)
        s_deviation = abs(s_value - ACTUAL_BIBLE_AVERAGE["S"])
        
        # S 차원이 평균에서 멀어질수록 (변동성이 클수록) 임계점 낮춤
        # 변동성이 크면 신호 발생률 증가 (Recall 향상)
        volatility_adjustment = 1.0 - (s_deviation * 0.5)  # 최대 50% 감소
        volatility_adjustment = max(0.5, min(1.5, volatility_adjustment))  # 0.5 ~ 1.5 범위
        
        # 태양인 점수 기반 조정 (태양인 점수가 높을수록 임계점 낮춤)
        taeyang_adjustment = 1.0 - (taeyang_score_effective * 0.3)  # 최대 30% 감소
        taeyang_adjustment = max(0.7, min(1.3, taeyang_adjustment))  # 0.7 ~ 1.3 범위
        
        # 최종 배율 계산
        dynamic_multiplier = base_multiplier * volatility_adjustment * taeyang_adjustment
        explosive_threshold = ACTUAL_BIBLE_AVERAGE["S"] * taeyang_weight * dynamic_multiplier
        
        is_explosive = fire_energy >= explosive_threshold
        
        # 보호막 상태 판정 (역추산 논리)
        if hydrophobicity_level >= 0.7:
            protection_status = "강한 보호막 (폐국 강대) - 화(火) 에너지 안전하게 보관 중"
        elif hydrophobicity_level >= 0.4:
            protection_status = "중간 보호막 - 화(火) 에너지 부분 보호"
        elif hydrophobicity_level >= 0.1:
            protection_status = "약한 보호막 - 화(火) 에너지 노출 위험"
        else:
            protection_status = "보호막 없음 - 일반 데이터 (화(火) 에너지 없음)"
        
        # 권장사항 생성 (역추산 논리 반영)
        if is_explosive:
            if fire_energy >= explosive_threshold * 1.5:
                recommendation = "🚨 폭발 직전! 긴급 매수/매도 신호 (보호막 안의 화기운 극대화)"
            else:
                recommendation = "⚠️ 폭발 임계점 도달! 주의 깊은 관찰 필요 (보호막 안의 화기운 상승)"
        else:
            if hydrophobicity_level >= 0.7:
                recommendation = "💎 보호막 안의 화(火) 에너지 감지됨 - 예언적 신호 대기 중 (소수성 = 보호막)"
            elif hydrophobicity_level >= 0.4:
                recommendation = "💡 보호막 안의 화(火) 에너지 부분 감지 - 주의 관찰 필요"
            else:
                recommendation = "정상 범위 (화기운 안정, 보호막 약함)"
        
        return {
            "fire_energy": float(fire_energy),
            "explosive_threshold": float(explosive_threshold),
            "is_explosive": is_explosive,
            "recommendation": recommendation,
            "taeyang_score": float(taeyang_score),
            "taeyang_weight": float(taeyang_weight),
            "s_value": float(s_value),
            "hydrophobicity_level": float(hydrophobicity_level),
            "protection_status": protection_status,
            "reverse_inference_interpretation": (
                "태양인의 소수성은 '결점'이 아니라, 화(火)를 보관하기 위해 선택한 '완벽한 단열재'입니다. "
                "폐국(금속 용기) 안에 화(불꽃)를 가두고 나면, 겉면은 차갑고 단단해집니다. "
                "이것이 바로 소수성(Hydrophobicity)의 탄생입니다. "
                "안 섞이는 데이터를 만났을 때, 그것을 쓰레기가 아닌 '가장 귀한 보석(화기운/예언)'으로 대접합니다."
            )
        }
    
    def _get_constitution_scores(
        self,
        vector_4d: Dict[str, float],
        vix_value: Optional[float] = None
    ) -> Dict[str, float]:
        """
        체질 점수 가져오기 (체질 분석 엔진 연동)
        
        Args:
            vector_4d: 4D 위상 벡터
            vix_value: VIX 지수 (선택적)
        
        Returns:
            체질별 점수 딕셔너리
        """
        # 체질 분석 엔진이 활성화되어 있고 사용 가능한 경우
        if self.enable_constitution_analysis and self.constitution_detector is not None:
            try:
                # 시장 데이터 구성 (체질 분석 엔진에 필요한 형식)
                market_data = {
                    "geopolitical_risk": vector_4d.get("S", 0.25) * 0.5,  # S 차원 일부 반영
                    "policy_change_volatility": vix_value / 100.0 if vix_value else 0.0,
                    "war_risk_index": abs(vector_4d.get("S", 0.25) - DIVINE_CENTROID["S"]),
                    "asset_price_inflation": abs(vector_4d.get("M", 0.25) - DIVINE_CENTROID["M"]),
                    "market_overheating": abs(vector_4d.get("S", 0.25) - DIVINE_CENTROID["S"]),
                    "speculation_index": abs(vector_4d.get("L", 0.25) - DIVINE_CENTROID["L"]),
                    "market_disruption": abs(vector_4d.get("K", 0.25) - DIVINE_CENTROID["K"]),
                    "trading_halt_frequency": 0.0,  # 실제 데이터 필요
                    "liquidity_crisis": abs(vector_4d.get("M", 0.25) - DIVINE_CENTROID["M"]),
                }
                
                # 체질 분석 실행
                diagnosis = self.constitution_detector.diagnose_all_constitutions(market_data)
                
                # 체질별 점수 추출
                constitution_scores = {
                    "태양인": diagnosis["diagnosis"]["태양인"].get("score", 0.0),
                    "태음인": diagnosis["diagnosis"]["태음인"].get("score", 0.0),
                    "소양인": diagnosis["diagnosis"]["소양인"].get("score", 0.0),
                    "소음인": diagnosis["diagnosis"]["소음인"].get("score", 0.0),
                }
                
                logger.debug(f"체질 점수: {constitution_scores}")
                return constitution_scores
                
            except Exception as e:
                logger.warning(f"체질 분석 엔진 실행 실패: {e}, 기본값 사용")
                # Fallback: 기본값 사용
                return {
                    "태양인": 0.0,
                    "태음인": 0.0,
                    "소양인": 0.0,
                    "소음인": 0.0
                }
        else:
            # 체질 분석 엔진이 없거나 비활성화된 경우 기본값 사용
            return {
                "태양인": 0.0,
                "태음인": 0.0,
                "소양인": 0.0,
                "소음인": 0.0
            }


if __name__ == "__main__":
    # 테스트
    nowcaster = PhaseSpaceNowcaster()
    
    # 샘플 데이터 입력
    for i in range(30):
        vector = {
            "S": 0.25 + i * 0.01,
            "L": 0.25 - i * 0.005,
            "K": 0.25 + i * 0.015,
            "M": 0.25 - i * 0.01
        }
        nowcaster.update_phase_vector(vector)
    
    # 리포트 생성
    report = nowcaster.get_nowcasting_report()
    print("\n🏛️ 위상 공간 나우캐스팅 리포트")
    print("=" * 80)
    print(f"위기 신호: {report['crisis_level']}")
    print(f"Divine Centroid 거리: {report['nowcasting']['distance_to_centroid']:.3f}")
    print(f"거리 속도: {report['nowcasting']['distance_velocity']:.4f}")
    print(f"\n패턴 매칭:")
    for template, match in report['pattern_matching'].get('pattern_matches', {}).items():
        print(f"  {template}: 유사도 {match['similarity']:.1%}")
    print(f"\n시나리오:")
    for scenario, data in report['scenarios'].items():
        print(f"  {scenario}: 확률 {data['probability']:.1%}")

