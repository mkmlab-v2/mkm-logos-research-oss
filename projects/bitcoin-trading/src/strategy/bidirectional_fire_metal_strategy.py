"""
양방향 매매 전략: 2026 Fire Crash + 2028 Metal Reset

작성일: 2026-01-18
목적: 화기 농도 기반 양방향 매매 전략 (롱/숏 동적 조정)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BidirectionalFireMetalStrategy:
    """
    양방향 매매 전략: 2026 Fire Crash + 2028 Metal Reset
    
    핵심 기능:
    1. 화기 농도 기반 롱/숏 포지션 크기 동적 조정
    2. 2026년 Fire Crash 전용 숏 포지션 전략
    3. 2028년 Metal Reset 전용 헤지 전략
    """
    
    def __init__(
        self,
        max_position_ratio: float = 0.40,  # 최대 포지션 비율 (40%)
        base_position_ratio: float = 0.30,  # 기본 포지션 비율 (30%)
        fire_threshold_high: float = 0.8,  # 화기 농도 높음 임계값
        fire_threshold_critical: float = 0.9,  # 화기 농도 극대 임계값
        interference_threshold: float = 0.95  # 간섭 강도 임계값 (2028년)
    ):
        self.max_position_ratio = max_position_ratio
        self.base_position_ratio = base_position_ratio
        self.fire_threshold_high = fire_threshold_high
        self.fire_threshold_critical = fire_threshold_critical
        self.interference_threshold = interference_threshold
    
    def calculate_bidirectional_position_size(
        self,
        fire_concentration: float,
        signal_confidence: float,
        total_assets: float,
        position_side: str,  # "LONG" or "SHORT"
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        양방향 매매 포지션 크기 계산
        
        Args:
            fire_concentration: 화기 농도 (0.0 ~ 1.0)
            signal_confidence: 신호 신뢰도 (0.0 ~ 1.0)
            total_assets: 총 자산
            position_side: 포지션 방향 ("LONG" or "SHORT")
            current_date: 현재 날짜 (2026-2028년 구분용)
        
        Returns:
            {
                "position_size": float,  # 포지션 크기 (USDT)
                "position_ratio": float,  # 포지션 비율 (0.0 ~ 1.0)
                "leverage": float,  # 레버리지
                "stop_loss_ratio": float,  # 손절 비율
                "take_profit_ratios": List[float],  # 익절 비율 리스트
                "strategy_type": str,  # 전략 타입 ("fire_crash", "metal_reset", "normal")
                "reasoning": str  # 판단 근거
            }
        """
        try:
            # 1. 연도별 전략 구분
            year = current_date.year if current_date else datetime.now().year
            strategy_type = self._determine_strategy_type(year, fire_concentration)
            
            # 2. 포지션 크기 계산
            if position_side == "SHORT":
                position_ratio, reasoning = self._calculate_short_position_ratio(
                    fire_concentration, signal_confidence, strategy_type
                )
            else:  # LONG
                position_ratio, reasoning = self._calculate_long_position_ratio(
                    fire_concentration, signal_confidence, strategy_type
                )
            
            # 3. 신뢰도 기반 조정
            position_ratio *= signal_confidence
            
            # 4. 최대 비율 제한
            position_ratio = min(self.max_position_ratio, position_ratio)
            
            # 5. 포지션 크기 계산
            position_size = total_assets * position_ratio
            
            # 6. 레버리지 및 손절/익절 계산
            leverage, stop_loss_ratio, take_profit_ratios = self._calculate_risk_params(
                fire_concentration, strategy_type, position_side
            )
            
            return {
                "position_size": position_size,
                "position_ratio": position_ratio,
                "leverage": leverage,
                "stop_loss_ratio": stop_loss_ratio,
                "take_profit_ratios": take_profit_ratios,
                "strategy_type": strategy_type,
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"❌ 양방향 매매 포지션 크기 계산 실패: {e}")
            # 기본값 반환
            return {
                "position_size": total_assets * self.base_position_ratio * signal_confidence,
                "position_ratio": self.base_position_ratio * signal_confidence,
                "leverage": 2.0,
                "stop_loss_ratio": 0.05,
                "take_profit_ratios": [0.10, 0.15, 0.20],
                "strategy_type": "normal",
                "reasoning": f"에러 발생: {str(e)}"
            }
    
    def _determine_strategy_type(
        self,
        year: int,
        fire_concentration: float
    ) -> str:
        """
        전략 타입 결정
        
        Returns:
            "fire_crash": 2026년 Fire Crash 전략
            "metal_reset": 2028년 Metal Reset 전략
            "normal": 일반 전략
        """
        if year == 2026 and fire_concentration >= self.fire_threshold_high:
            return "fire_crash"
        elif year == 2028:
            return "metal_reset"
        else:
            return "normal"
    
    def _calculate_short_position_ratio(
        self,
        fire_concentration: float,
        signal_confidence: float,
        strategy_type: str
    ) -> Tuple[float, str]:
        """
        숏 포지션 비율 계산 (비대칭성 부여)
        
        🔥 개선사항 (2026-01-18):
        - 공포 수치(S)보다 화기 잔류량(fire_concentration)에 더 높은 가중치
        - 화기 잔류량이 높을수록 숏 포지션 비율 증가 (비대칭성)
        
        Returns:
            (position_ratio, reasoning)
        """
        if strategy_type == "fire_crash":
            # 2026년 Fire Crash: 화기 농도 기반 확대 (비대칭성 부여)
            # 화기 잔류량에 더 높은 가중치 (공포 수치보다 중요)
            fire_residue_weight = fire_concentration  # 화기 잔류량 가중치 (0.0 ~ 1.0)
            
            if fire_concentration >= self.fire_threshold_critical:
                # 화기 농도 0.9 이상: 최대 확대 (40%)
                # 화기 잔류량 가중치 추가 적용 (비대칭성)
                ratio = self.max_position_ratio * (1.0 + fire_residue_weight * 0.1)  # 최대 44%
                ratio = min(self.max_position_ratio * 1.1, ratio)  # 최대 10% 추가
                reasoning = f"화기 폭발 감지 (농도: {fire_concentration:.2f}, 잔류량 가중치: {fire_residue_weight:.2f}) - 숏 포지션 최대 확대"
            elif fire_concentration >= self.fire_threshold_high:
                # 화기 농도 0.8 이상: 확대 (30-35%)
                # 화기 잔류량 가중치 추가 적용
                base_ratio = self.base_position_ratio * 1.17  # 35%
                ratio = base_ratio * (1.0 + fire_residue_weight * 0.08)  # 최대 37.8%
                reasoning = f"화기 극대화 감지 (농도: {fire_concentration:.2f}, 잔류량 가중치: {fire_residue_weight:.2f}) - 숏 포지션 확대"
            else:
                # 화기 농도 0.7-0.8: 기본 (25%)
                # 화기 잔류량 가중치 추가 적용
                base_ratio = self.base_position_ratio * 0.83  # 25%
                ratio = base_ratio * (1.0 + fire_residue_weight * 0.06)  # 최대 26.5%
                reasoning = f"화기 가속 감지 (농도: {fire_concentration:.2f}, 잔류량 가중치: {fire_residue_weight:.2f}) - 숏 포지션 진입"
        elif strategy_type == "metal_reset":
            # 2028년 Metal Reset: 헤지 전략 (10%)
            ratio = 0.10
            reasoning = "2028년 Metal Reset - 헤지 전략 (롱/숏 동시 진입)"
        else:
            # 일반 전략: 화기 농도 기반
            if fire_concentration >= self.fire_threshold_high:
                ratio = self.base_position_ratio * 0.83  # 25%
                reasoning = f"화기 농도 높음 (농도: {fire_concentration:.2f}) - 숏 포지션 진입"
            else:
                ratio = 0.0  # 숏 포지션 없음
                reasoning = f"화기 농도 낮음 (농도: {fire_concentration:.2f}) - 숏 포지션 없음"
        
        return ratio, reasoning
    
    def _calculate_long_position_ratio(
        self,
        fire_concentration: float,
        signal_confidence: float,
        strategy_type: str
    ) -> Tuple[float, str]:
        """
        롱 포지션 비율 계산
        
        Returns:
            (position_ratio, reasoning)
        """
        if strategy_type == "fire_crash":
            # 2026년 Fire Crash: 화기 폭발 시 롱 포지션 없음
            if fire_concentration >= self.fire_threshold_high:
                ratio = 0.0
                reasoning = f"화기 폭발 감지 (농도: {fire_concentration:.2f}) - 롱 포지션 없음"
            else:
                # 화기 농도 낮을 때만 롱 포지션
                ratio = self.base_position_ratio * (1.0 - fire_concentration)
                reasoning = f"화기 농도 낮음 (농도: {fire_concentration:.2f}) - 롱 포지션 축소"
        elif strategy_type == "metal_reset":
            # 2028년 Metal Reset: 헤지 전략 (10%)
            ratio = 0.10
            reasoning = "2028년 Metal Reset - 헤지 전략 (롱/숏 동시 진입)"
        else:
            # 일반 전략: 화기 농도 역가중
            if fire_concentration < 0.5:
                # 화기 농도 낮을수록 롱 포지션 증가
                ratio = self.base_position_ratio * (1.0 + (0.5 - fire_concentration))
                reasoning = f"화기 농도 낮음 (농도: {fire_concentration:.2f}) - 롱 포지션 확대"
            else:
                ratio = self.base_position_ratio * (1.0 - fire_concentration)
                reasoning = f"화기 농도 중간 (농도: {fire_concentration:.2f}) - 롱 포지션 기본"
        
        # 최대 비율 제한
        ratio = min(self.max_position_ratio, ratio)
        return ratio, reasoning
    
    def _calculate_risk_params(
        self,
        fire_concentration: float,
        strategy_type: str,
        position_side: str
    ) -> Tuple[float, float, list]:
        """
        리스크 파라미터 계산 (레버리지, 손절, 익절)
        
        Returns:
            (leverage, stop_loss_ratio, take_profit_ratios)
        """
        if strategy_type == "fire_crash" and position_side == "SHORT":
            # 2026년 Fire Crash 숏 포지션: 공격적 전략
            if fire_concentration >= self.fire_threshold_critical:
                # 화기 폭발 시: 더 타이트한 손절, 더 공격적인 익절
                leverage = 2.0
                stop_loss_ratio = 0.03  # 3% 손절
                take_profit_ratios = [0.10, 0.15, 0.20]  # 10%, 15%, 20% 익절
            else:
                leverage = 2.0
                stop_loss_ratio = 0.05  # 5% 손절
                take_profit_ratios = [0.10, 0.15, 0.20]
        elif strategy_type == "metal_reset":
            # 2028년 Metal Reset: 보수적 헤지 전략
            leverage = 1.0  # 낮은 레버리지
            stop_loss_ratio = 0.10  # 10% 손절
            take_profit_ratios = [0.10, 0.15]  # 10%, 15% 익절
        else:
            # 일반 전략: 기본 파라미터
            leverage = 2.0
            stop_loss_ratio = 0.05  # 5% 손절
            take_profit_ratios = [0.10, 0.15, 0.20]  # 10%, 15%, 20% 익절
        
        return leverage, stop_loss_ratio, take_profit_ratios
    
    def should_increase_short_position(
        self,
        fire_concentration: float,
        current_short_ratio: float,
        signal_confidence: float,
        current_date: Optional[datetime] = None
    ) -> Tuple[bool, float]:
        """
        숏 포지션 확대 여부 판단
        
        Returns:
            (should_increase, target_ratio)
        """
        year = current_date.year if current_date else datetime.now().year
        
        if year == 2026 and fire_concentration >= self.fire_threshold_high:
            # 2026년 Fire Crash: 화기 농도 기반 확대
            target_ratio, _ = self._calculate_short_position_ratio(
                fire_concentration, signal_confidence, "fire_crash"
            )
            
            if current_short_ratio < target_ratio * 0.9:  # 90% 미만이면 확대
                return True, target_ratio
            else:
                return False, current_short_ratio
        else:
            return False, current_short_ratio
    
    def should_close_short_position(
        self,
        fire_concentration: float,
        pnl_percentage: float,
        current_date: Optional[datetime] = None,
        nasdaq_level: Optional[float] = None,
        exchange_rate: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        숏 포지션 청산 여부 판단
        
        팩트체크 권고 반영: 점진적 청산 전략 + 나스닥/환율 기준선 검증
        
        Returns:
            (should_close, close_ratio)  # close_ratio: 0.0 ~ 1.0
        """
        year = current_date.year if current_date else datetime.now().year
        
        if year == 2026:
            # 2026년 Fire Crash: 수익 실현 후 점진적 청산
            if pnl_percentage >= 0.20:  # 20% 수익 시
                return True, 1.0  # 완전 청산
            elif pnl_percentage >= 0.15:  # 15% 수익 시
                return True, 0.3  # 30% 청산
            elif pnl_percentage >= 0.10:  # 10% 수익 시
                return True, 0.5  # 50% 청산
            elif pnl_percentage >= 0.05:  # 5% 수익 시 (팩트체크 권고 추가)
                return True, 0.2  # 20% 청산
            # 손실 구간: 손절 기준 (팩트체크 권고 추가)
            elif pnl_percentage <= -0.20:  # -20% 손실 시
                return True, 1.0  # 강제 손절
            elif pnl_percentage <= -0.15:  # -15% 손실 시
                return True, 0.5  # 50% 청산
            elif pnl_percentage <= -0.10:  # -10% 손실 시
                return True, 0.2  # 20% 청산
            # 나스닥 23,500 돌파 시 (팩트체크 권고 추가)
            elif nasdaq_level and nasdaq_level >= 23500:
                return True, 0.3  # 30% 청산 (85% 축소 대신 점진적)
            elif fire_concentration < 0.7:  # 화기 약화 시
                return True, 0.2  # 20% 청산
            else:
                return False, 0.0
        else:
            # 일반 전략: 기본 청산 로직
            if pnl_percentage >= 0.15:
                return True, 1.0
            else:
                return False, 0.0
    
    def should_enter_hedge_position(
        self,
        interference_strength: float,
        current_date: Optional[datetime] = None
    ) -> Tuple[bool, Dict[str, float]]:
        """
        2028년 Metal Reset 헤지 전략 진입 여부 판단
        
        Returns:
            (should_hedge, {"long_ratio": float, "short_ratio": float})
        """
        year = current_date.year if current_date else datetime.now().year
        
        if year == 2028 and interference_strength >= self.interference_threshold:
            # 2028년 Metal Reset: 헤지 전략
            return True, {
                "long_ratio": 0.10,
                "short_ratio": 0.10
            }
        else:
            return False, {
                "long_ratio": 0.0,
                "short_ratio": 0.0
            }

