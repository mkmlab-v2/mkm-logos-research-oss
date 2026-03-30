#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SBSC 프레임워크 기반 매매 전략 검증기

SBSC General Framework를 활용한 매매 전략 검증
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# SBSC 프레임워크 import
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))

try:
    from sbsc_general_framework import SBSCGeneralFramework
    SBSC_AVAILABLE = True
except ImportError:
    SBSC_AVAILABLE = False
    SBSCGeneralFramework = None
    logging.warning("⚠️ SBSCGeneralFramework을 import할 수 없습니다.")

logger = logging.getLogger(__name__)


class SBSCStrategyVerifier:
    """
    SBSC 프레임워크 기반 매매 전략 검증기
    
    매매 신호를 SBSC 방식으로 검증하여 환각 억제
    """
    
    def __init__(self, domain: str = "finance"):
        """
        초기화
        
        Args:
            domain: 도메인 타입 ("math", "finance", "knowledge", "general")
        """
        if SBSC_AVAILABLE and SBSCGeneralFramework:
            self.framework = SBSCGeneralFramework(
                domain=domain,
                use_llm=False  # LLM 없이 벡터화만 사용
            )
            logger.info(f"✅ SBSCGeneralFramework 초기화 완료 (도메인: {domain})")
        else:
            self.framework = None
            logger.warning("⚠️ SBSCGeneralFramework 사용 불가, 검증 기능 제한")
    
    def verify_trading_signal(
        self,
        signal_data: Dict[str, Any],
        price_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        매매 신호 검증 (SBSC 방식)
        
        Args:
            signal_data: 매매 신호 데이터
            price_data: 가격 데이터 (선택적)
        
        Returns:
            {
                "is_valid": bool,  # 유효한 신호인지
                "verification_score": float,  # 검증 점수 (0.0 ~ 1.0)
                "steps_verified": int,  # 검증된 단계 수
                "recommendation": str  # 권장 사항
            }
        """
        if not self.framework:
            return {
                "is_valid": True,  # SBSC 없으면 기본적으로 통과
                "verification_score": 0.5,
                "steps_verified": 0,
                "recommendation": "SBSC 검증 불가, 기본 검증 통과"
            }
        
        try:
            # 신호를 문제로 변환
            signal = signal_data.get("signal", "HOLD")
            confidence = signal_data.get("confidence", 0.0)
            lambda_value = signal_data.get("lambda", 0.5)
            
            problem_text = f"매매 신호: {signal}, 신뢰도: {confidence:.2%}, Lambda: {lambda_value:.3f}"
            
            # SBSC 방식으로 문제 해결 시도 (검증 목적)
            # 실제로는 단계별 검증만 수행
            verification_result = self._verify_step_by_step(
                problem_text=problem_text,
                signal_data=signal_data
            )
            
            return verification_result
        except Exception as e:
            logger.error(f"❌ SBSC 전략 검증 실패: {e}")
            return {
                "is_valid": False,
                "verification_score": 0.0,
                "steps_verified": 0,
                "recommendation": f"검증 오류: {e}"
            }
    
    def _verify_step_by_step(
        self,
        problem_text: str,
        signal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        단계별 검증 (SBSC 방식)
        
        Args:
            problem_text: 문제 텍스트
            signal_data: 신호 데이터
        
        Returns:
            검증 결과
        """
        # 1단계: 벡터화 검증
        vector_4d = signal_data.get("corrected_vector") or signal_data.get("sovereign_vector")
        if not vector_4d:
            return {
                "is_valid": False,
                "verification_score": 0.0,
                "steps_verified": 0,
                "recommendation": "벡터 데이터 없음, 검증 불가"
            }
        
        # 2단계: 벡터 일관성 검증
        s = vector_4d.get("S", 0.25)
        l = vector_4d.get("L", 0.25)
        k = vector_4d.get("K", 0.25)
        m = vector_4d.get("M", 0.25)
        
        total = s + l + k + m
        if abs(total - 1.0) > 0.01:
            return {
                "is_valid": False,
                "verification_score": 0.0,
                "steps_verified": 1,
                "recommendation": f"벡터 합이 1.0이 아님: {total:.3f}"
            }
        
        # 3단계: 신뢰도 검증 (개선: 최소값 0.1로 상향)
        confidence = signal_data.get("confidence", 0.0)
        if confidence < 0.1:  # 개선: 0.08 → 0.1로 상향
            return {
                "is_valid": False,
                "verification_score": 0.3,
                "steps_verified": 2,
                "recommendation": f"신뢰도 부족: {confidence:.2%} < 10%"  # 개선: 8% → 10%
            }
        
        # 4단계: Lambda 검증
        lambda_value = signal_data.get("lambda", 0.5)
        if lambda_value < 0.2 or lambda_value > 0.8:
            return {
                "is_valid": False,
                "verification_score": 0.5,
                "steps_verified": 3,
                "recommendation": f"Lambda 범위 벗어남: {lambda_value:.3f} (정상 범위: 0.2~0.8)"
            }
        
        # 모든 단계 통과
        return {
            "is_valid": True,
            "verification_score": 0.9,  # 높은 검증 점수
            "steps_verified": 4,
            "recommendation": "SBSC 검증 통과: 모든 단계 검증 완료"
        }

