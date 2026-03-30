#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사원수 기반 금융 시계열 분석기

QuaternionFinanceEngine을 활용한 시장 위상 분석
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
import numpy as np

# 사원수 엔진 import
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "finance"))

try:
    from quaternion_finance_engine import QuaternionFinanceEngine
    QUATERNION_AVAILABLE = True
except ImportError:
    QUATERNION_AVAILABLE = False
    QuaternionFinanceEngine = None
    logging.warning("⚠️ QuaternionFinanceEngine을 import할 수 없습니다.")

logger = logging.getLogger(__name__)


class QuaternionFinanceAnalyzer:
    """
    사원수 기반 금융 시계열 분석기
    
    MKM12 수학 헌법 v4.0 준수
    
    시장 데이터를 4D 위상 공간으로 변환하고 사원수 회전 연산으로 분석
    
    헌법 제2장 사원수 제3공식: 파라미터 75% 절감
    - 4차원 벡터를 사원수로 변환 시 파라미터가 75% 절감됩니다.
    - 실수 기반: 4x4 = 16 파라미터 필요
    - 사원수 기반: 1개 사원수 = 4 파라미터
    - 절감률: (1 - 4/16) × 100 = 75%
    """
    
    def __init__(self):
        """초기화"""
        if QUATERNION_AVAILABLE and QuaternionFinanceEngine:
            self.engine = QuaternionFinanceEngine()
            logger.info("✅ QuaternionFinanceEngine 초기화 완료")
        else:
            self.engine = None
            logger.warning("⚠️ QuaternionFinanceEngine 사용 불가, 분석 기능 제한")
    
    def analyze_market_phase(
        self,
        price_data: pd.DataFrame,
        window_size: int = 20
    ) -> Dict[str, Any]:
        """
        시장 위상 분석
        
        Args:
            price_data: 가격 데이터 DataFrame (close, volume 컬럼 필요)
            window_size: 이동 평균 윈도우 크기
        
        Returns:
            {
                "phase_rotation": Dict,  # 위상 회전 분석 결과
                "anomaly_detection": Dict,  # 이상 감지 결과
                "correlation_analysis": Dict,  # 상관관계 분석 결과
                "prediction": Dict  # 예측 결과
            }
        """
        if not self.engine:
            return {
                "phase_rotation": None,
                "anomaly_detection": None,
                "correlation_analysis": None,
                "prediction": None,
                "error": "QuaternionFinanceEngine 사용 불가"
            }
        
        try:
            # 가격 데이터 추출
            prices = price_data['close'].tolist()
            volumes = price_data.get('volume', pd.Series([1.0] * len(prices))).tolist()
            
            # 4D 벡터 시퀀스로 변환
            vector_sequence = self.engine.time_series_to_4d_vector(
                price_data=prices,
                volume_data=volumes,
                window_size=window_size
            )
            
            # 위상 회전 분석
            phase_rotation = self.engine.analyze_phase_rotation(
                vector_sequence=vector_sequence
            )
            
            # 이상 감지
            anomaly_detection = self.engine.detect_anomalies(
                vector_sequence=vector_sequence,
                threshold=0.3
            )
            
            # 예측 (최근 5개 시점)
            if len(vector_sequence) >= 5:
                recent_vectors = vector_sequence[-5:]
                prediction = self.engine.predict_future_phase(
                    vector_sequence=recent_vectors,
                    steps_ahead=3
                )
            else:
                prediction = None
            
            return {
                "phase_rotation": phase_rotation,
                "anomaly_detection": anomaly_detection,
                "correlation_analysis": None,  # 단일 시계열이므로 상관관계 분석 불가
                "prediction": prediction
            }
        except Exception as e:
            logger.error(f"❌ 시장 위상 분석 실패: {e}")
            return {
                "phase_rotation": None,
                "anomaly_detection": None,
                "correlation_analysis": None,
                "prediction": None,
                "error": str(e)
            }
    
    def get_phase_insight(
        self,
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        위상 분석 결과를 해석하여 인사이트 생성
        
        Args:
            analysis_result: analyze_market_phase()의 결과
        
        Returns:
            인사이트 텍스트
        """
        if not analysis_result or analysis_result.get("error"):
            return "위상 분석 불가"
        
        phase_rotation = analysis_result.get("phase_rotation")
        anomaly_detection = analysis_result.get("anomaly_detection")
        prediction = analysis_result.get("prediction")
        
        insights = []
        
        # 위상 회전 인사이트
        if phase_rotation:
            total_angle = phase_rotation.get("total_rotation_angle", 0)
            if total_angle > 0.5:
                insights.append(f"강한 위상 변화 감지 (회전 각도: {total_angle:.2f} 라디안)")
            elif total_angle > 0.2:
                insights.append(f"중간 위상 변화 감지 (회전 각도: {total_angle:.2f} 라디안)")
            else:
                insights.append(f"안정적인 위상 (회전 각도: {total_angle:.2f} 라디안)")
        
        # 이상 감지 인사이트
        if anomaly_detection:
            anomalies = anomaly_detection.get("anomalies", [])
            if anomalies:
                insights.append(f"이상 감지: {len(anomalies)}개 시점에서 이상 패턴 발견")
        
        # 예측 인사이트
        if prediction:
            future_vectors = prediction.get("future_vectors", [])
            if future_vectors:
                insights.append(f"예측: 향후 {len(future_vectors)}개 시점의 위상 변화 예측 완료")
        
        if not insights:
            return "위상 분석 결과 없음"
        
        return " | ".join(insights)

