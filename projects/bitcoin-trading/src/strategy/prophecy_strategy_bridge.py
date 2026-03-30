#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 예언서 전략 브릿지

실제 비트코인 매매 엔진에 예언서 전략을 통합합니다.
심판/회복 벡터를 매매 신호의 보조 지표로 활용합니다.

작성일: 2026-02-06
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# 예언서 전략 모듈 import (안전하게)
PROPHECY_MODULES_AVAILABLE = {}

try:
    from tools.prophecy.prophecy_vector_definitions import get_prophecy_vector, ProphecyDomain
    PROPHECY_MODULES_AVAILABLE["prophecy_vectors"] = True
except Exception as e:
    PROPHECY_MODULES_AVAILABLE["prophecy_vectors"] = False
    logging.warning(f"⚠️ prophecy_vector_definitions import 실패: {e}")

try:
    from tools.prophecy.judgment_recovery_vector_calculator import (
        calculate_judgment_vector,
        calculate_recovery_vector,
        analyze_judgment_recovery_transition
    )
    PROPHECY_MODULES_AVAILABLE["judgment_recovery"] = True
except Exception as e:
    PROPHECY_MODULES_AVAILABLE["judgment_recovery"] = False
    logging.warning(f"⚠️ judgment_recovery_vector_calculator import 실패: {e}")

try:
    from tools.tools.core.harmonic_cycle_aligner import HarmonicCycleAligner
    PROPHECY_MODULES_AVAILABLE["harmonic_aligner"] = True
except Exception as e:
    PROPHECY_MODULES_AVAILABLE["harmonic_aligner"] = False
    logging.warning(f"⚠️ harmonic_cycle_aligner import 실패: {e}")

logger = logging.getLogger(__name__)


class ProphecyStrategyBridge:
    """
    예언서 전략 브릿지
    
    핵심 기능:
    1. 실시간 시장 데이터를 예언서 벡터로 변환
    2. 심판/회복 벡터 계산
    3. 엔트로피 임계 상태 감지
    4. 매매 신호 조정 (보조 지표)
    """
    
    def __init__(self):
        """초기화"""
        self.harmonic_aligner = None
        
        if PROPHECY_MODULES_AVAILABLE.get("harmonic_aligner", False):
            try:
                self.harmonic_aligner = HarmonicCycleAligner()
                logger.info("✅ HarmonicCycleAligner 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ HarmonicCycleAligner 초기화 실패: {e}")
        
        # 상태 저장
        self.last_judgment_vector = None
        self.last_recovery_vector = None
        self.last_entropy_status = None
    
    def analyze_market_data(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        시장 데이터를 예언서 벡터로 분석
        
        Args:
            market_data: 시장 데이터 (가격, 변동성, 거래량 등)
            
        Returns:
            예언서 전략 분석 결과
        """
        if not PROPHECY_MODULES_AVAILABLE.get("judgment_recovery", False):
            return {
                "available": False,
                "error": "judgment_recovery 모듈을 사용할 수 없습니다."
            }
        
        try:
            # 시장 데이터를 텍스트로 변환
            price = market_data.get("price", 0.0)
            volume = market_data.get("volume", 0.0)
            volatility = market_data.get("volatility", 0.0)
            price_change_24h = market_data.get("price_change_24h", 0.0)
            
            # 시장 상태 텍스트 생성
            market_text = self._create_market_text(
                price, volume, volatility, price_change_24h
            )
            
            # 심판/회복 벡터 계산
            judgment_vector = calculate_judgment_vector(market_text)
            recovery_vector = calculate_recovery_vector(market_text)
            transition_analysis = analyze_judgment_recovery_transition(market_text)
            
            # 엔트로피 임계 상태 판정
            entropy_max = self._detect_entropy_max(judgment_vector)
            
            # 회복 상태 판정
            recovery_detected = (
                transition_analysis.get("state") == "recovery"
                if transition_analysis else False
            )
            
            # 조화 모델 적용
            harmonic_info = None
            if self.harmonic_aligner:
                try:
                    current_year = datetime.now().year
                    alignment = self.harmonic_aligner.calculate_financial_cycle_alignment(current_year)
                    scheduled_chaos = self.harmonic_aligner.calculate_scheduled_chaos(current_year)
                    
                    harmonic_info = {
                        "alignment_score": alignment.get("alignment_score", 0.0),
                        "decoupling_risk": alignment.get("decoupling_risk", 0.0),
                        "scheduled_chaos_active": scheduled_chaos.get("scheduled_chaos_active", False),
                        "is_sabbath": scheduled_chaos.get("is_sabbath_year", False),
                        "is_jubilee": scheduled_chaos.get("is_jubilee_year", False)
                    }
                except Exception as e:
                    logger.warning(f"조화 모델 계산 오류: {e}")
            
            # 상태 저장
            self.last_judgment_vector = judgment_vector
            self.last_recovery_vector = recovery_vector
            self.last_entropy_status = entropy_max
            
            return {
                "available": True,
                "judgment_vector": judgment_vector,
                "recovery_vector": recovery_vector,
                "entropy_max_detected": entropy_max,
                "recovery_detected": recovery_detected,
                "transition_analysis": transition_analysis,
                "harmonic_info": harmonic_info,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"예언서 전략 분석 오류: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def _create_market_text(
        self,
        price: float,
        volume: float,
        volatility: float,
        price_change_24h: float
    ) -> str:
        """
        시장 데이터를 텍스트로 변환
        
        Args:
            price: 현재 가격
            volume: 거래량
            volatility: 변동성
            price_change_24h: 24시간 가격 변화율
            
        Returns:
            시장 상태 텍스트
        """
        # 변동성 기반 키워드
        if volatility > 0.05:
            volatility_keyword = "높은 변동성, 엔트로피 증가"
        elif volatility > 0.02:
            volatility_keyword = "중간 변동성"
        else:
            volatility_keyword = "낮은 변동성, 안정"
        
        # 가격 변화 기반 키워드
        if price_change_24h < -0.10:
            price_keyword = "급락, 붕괴 위험"
        elif price_change_24h < -0.05:
            price_keyword = "하락, 엔트로피 증가"
        elif price_change_24h > 0.10:
            price_keyword = "급등, 회복 신호"
        elif price_change_24h > 0.05:
            price_keyword = "상승, 회복 진행"
        else:
            price_keyword = "안정"
        
        # 거래량 기반 키워드
        if volume > 0:
            volume_keyword = "거래량 있음"
        else:
            volume_keyword = "거래량 부족"
        
        return f"{volatility_keyword}, {price_keyword}, {volume_keyword}"
    
    def _detect_entropy_max(self, judgment_vector: Dict[str, float]) -> bool:
        """
        엔트로피 임계 상태 감지
        
        Args:
            judgment_vector: 심판 벡터
            
        Returns:
            엔트로피 임계 상태 여부
        """
        if not judgment_vector:
            return False
        
        # L 차원이 낮을수록 엔트로피 높음
        l_value = judgment_vector.get("L", 0.5)
        entropy_threshold = 0.3  # L < 0.3이면 엔트로피 임계 상태
        
        return l_value < entropy_threshold
    
    def adjust_trading_signal(
        self,
        original_signal: Dict[str, Any],
        prophecy_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        매매 신호를 예언서 전략으로 조정
        
        Args:
            original_signal: 원본 매매 신호 (LONG, SHORT, HOLD)
            prophecy_analysis: 예언서 전략 분석 결과
            
        Returns:
            조정된 매매 신호
        """
        if not prophecy_analysis.get("available", False):
            # 예언서 전략을 사용할 수 없으면 원본 신호 반환
            return original_signal
        
        entropy_max = prophecy_analysis.get("entropy_max_detected", False)
        recovery_detected = prophecy_analysis.get("recovery_detected", False)
        
        signal_type = original_signal.get("signal", "HOLD")
        confidence = original_signal.get("confidence", 0.0)
        
        # 엔트로피 임계 상태 감지 시
        if entropy_max:
            # 신호 차단 또는 신뢰도 감소
            if signal_type in ["LONG", "SHORT"]:
                # 신뢰도 30% 감소
                adjusted_confidence = max(0.0, confidence - 0.3)
                
                # 신뢰도가 너무 낮으면 HOLD로 변경
                if adjusted_confidence < 0.5:
                    return {
                        "signal": "HOLD",
                        "confidence": 0.0,
                        "reason": "엔트로피 임계 상태 감지 - 거래 차단",
                        "original_signal": signal_type,
                        "original_confidence": confidence,
                        "prophecy_adjustment": True
                    }
                else:
                    return {
                        "signal": signal_type,
                        "confidence": adjusted_confidence,
                        "reason": "엔트로피 임계 상태 감지 - 신뢰도 감소",
                        "original_signal": signal_type,
                        "original_confidence": confidence,
                        "prophecy_adjustment": True
                    }
        
        # 회복 상태 감지 시
        if recovery_detected:
            # LONG 신호의 신뢰도 증가
            if signal_type == "LONG":
                adjusted_confidence = min(1.0, confidence + 0.1)
                return {
                    "signal": signal_type,
                    "confidence": adjusted_confidence,
                    "reason": "회복 상태 감지 - LONG 신호 강화",
                    "original_signal": signal_type,
                    "original_confidence": confidence,
                    "prophecy_adjustment": True
                }
        
        # 조정 없음
        return {
            **original_signal,
            "prophecy_adjustment": False
        }
    
    def get_prophecy_status(self) -> Dict[str, Any]:
        """예언서 전략 상태 조회"""
        return {
            "modules_available": PROPHECY_MODULES_AVAILABLE,
            "last_judgment_vector": self.last_judgment_vector,
            "last_recovery_vector": self.last_recovery_vector,
            "last_entropy_status": self.last_entropy_status
        }


