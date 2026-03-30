#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛡️ 리스크 가디언 모듈

목적: MDD를 강제로 억제하면서 수익률을 최적화
- 포지션 크기 동적 조정 (Drawdown 기반)
- 일일 손실 한도
- 연속 손실 제한
- 거래 중단 메커니즘

작성일: 2026-02-06
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RiskGuardian:
    """
    리스크 가디언 클래스
    
    핵심 기능:
    1. Drawdown 기반 동적 포지션 크기 조정
    2. 일일 손실 한도 관리
    3. 연속 손실 제한
    4. 거래 중단 메커니즘
    """
    
    def __init__(
        self,
        base_position_size: float = 0.30,
        daily_loss_limit: float = 0.05,
        max_consecutive_losses: int = 3,
        drawdown_thresholds: Optional[Dict[float, float]] = None
    ):
        """
        Args:
            base_position_size: 기본 포지션 크기 (자본 대비, 0.0-1.0)
            daily_loss_limit: 일일 손실 한도 (자본 대비, 0.0-1.0)
            max_consecutive_losses: 최대 연속 손실 횟수
            drawdown_thresholds: Drawdown 기반 포지션 축소 임계값
                예: {0.20: 0.5, 0.15: 0.6, 0.10: 0.7, 0.05: 0.85}
        """
        self.base_position_size = base_position_size
        self.daily_loss_limit = daily_loss_limit
        self.max_consecutive_losses = max_consecutive_losses
        
        # Drawdown 기반 포지션 축소 설정 (기본값)
        if drawdown_thresholds is None:
            self.drawdown_thresholds = {
                0.20: 0.5,   # 20% 하락 시 포지션 50% 축소
                0.15: 0.6,   # 15% 하락 시 포지션 60% 축소
                0.10: 0.7,   # 10% 하락 시 포지션 70% 축소
                0.05: 0.85   # 5% 하락 시 포지션 85% 축소
            }
        else:
            self.drawdown_thresholds = drawdown_thresholds
        
        # 상태 변수
        self.consecutive_losses = 0
        self.trading_paused = False
        self.pause_until: Optional[datetime] = None
        
        # 일일 손실 추적
        self.current_date: Optional[datetime.date] = None
        self.daily_pnl = 0.0
        self.initial_daily_capital = 0.0
        
        logger.info("🛡️ 리스크 가디언 초기화 완료")
        logger.info(f"   기본 포지션 크기: {base_position_size:.2%}")
        logger.info(f"   일일 손실 한도: {daily_loss_limit:.2%}")
        logger.info(f"   최대 연속 손실: {max_consecutive_losses}회")
    
    def calculate_dynamic_position_size(
        self,
        current_drawdown: float,
        current_capital: float
    ) -> float:
        """
        Drawdown 기반 동적 포지션 크기 계산
        
        Args:
            current_drawdown: 현재 Drawdown (0.0-1.0, 절대값)
            current_capital: 현재 자본
        
        Returns:
            동적 포지션 크기 (0.0-1.0)
        """
        # Drawdown 기반 포지션 축소
        position_multiplier = 1.0
        for threshold, multiplier in sorted(
            self.drawdown_thresholds.items(),
            reverse=True
        ):
            if current_drawdown >= threshold:
                position_multiplier = multiplier
                break
        
        dynamic_size = self.base_position_size * position_multiplier
        
        # 일일 손실 한도 확인
        if self.current_date is not None:
            daily_loss_ratio = abs(self.daily_pnl) / self.initial_daily_capital if self.initial_daily_capital > 0 else 0.0
            if daily_loss_ratio >= self.daily_loss_limit:
                # 일일 손실 한도 도달 시 포지션 크기 추가 축소
                dynamic_size *= 0.5
        
        return max(0.0, min(dynamic_size, 1.0))
    
    def check_trading_allowed(self, current_time: datetime) -> tuple[bool, Optional[str]]:
        """
        거래 허용 여부 확인
        
        Args:
            current_time: 현재 시간
        
        Returns:
            (거래 허용 여부, 이유)
        """
        # 거래 중단 확인
        if self.trading_paused:
            if self.pause_until and current_time >= self.pause_until:
                # 거래 재개
                self.trading_paused = False
                self.pause_until = None
                self.consecutive_losses = 0
                logger.info("✅ 거래 재개: 일시 중단 기간 종료")
                return True, None
            else:
                return False, f"거래 중단 중 (재개: {self.pause_until})"
        
        # 일일 손실 한도 확인
        if self.current_date is not None:
            daily_loss_ratio = abs(self.daily_pnl) / self.initial_daily_capital if self.initial_daily_capital > 0 else 0.0
            if daily_loss_ratio >= self.daily_loss_limit:
                if not self.trading_paused:
                    self.trading_paused = True
                    self.pause_until = current_time + timedelta(hours=24)
                    logger.warning(f"⚠️ 일일 손실 한도 도달: {daily_loss_ratio:.2%} (한도: {self.daily_loss_limit:.2%})")
                return False, f"일일 손실 한도 도달 ({daily_loss_ratio:.2%})"
        
        return True, None
    
    def update_daily_tracking(
        self,
        current_time: datetime,
        current_capital: float
    ):
        """
        일일 추적 업데이트
        
        Args:
            current_time: 현재 시간
            current_capital: 현재 자본
        """
        current_date = current_time.date()
        
        # 날짜 변경 확인
        if self.current_date != current_date:
            if self.current_date is not None:
                # 전날 일일 손실 확인
                daily_loss_ratio = abs(self.daily_pnl) / self.initial_daily_capital if self.initial_daily_capital > 0 else 0.0
                if daily_loss_ratio >= self.daily_loss_limit:
                    logger.warning(f"⚠️ 전날 일일 손실 한도 도달: {daily_loss_ratio:.2%}")
            
            # 새 날 시작
            self.current_date = current_date
            self.daily_pnl = 0.0
            self.initial_daily_capital = current_capital
            logger.debug(f"📅 새 날 시작: {current_date}, 초기 자본: ${current_capital:,.2f}")
    
    def record_trade_result(
        self,
        pnl: float,
        current_time: datetime
    ):
        """
        거래 결과 기록
        
        Args:
            pnl: 거래 손익
            current_time: 거래 시간
        """
        self.daily_pnl += pnl
        
        # 연속 손실 추적
        if pnl < 0:
            self.consecutive_losses += 1
            logger.debug(f"연속 손실: {self.consecutive_losses}회")
            
            if self.consecutive_losses >= self.max_consecutive_losses:
                if not self.trading_paused:
                    self.trading_paused = True
                    self.pause_until = current_time + timedelta(hours=24)
                    logger.warning(f"⚠️ 연속 손실 {self.consecutive_losses}회: 거래 중단 (재개: {self.pause_until})")
        else:
            # 수익 거래 시 연속 손실 리셋
            if self.consecutive_losses > 0:
                logger.info(f"✅ 수익 거래로 연속 손실 리셋 (이전: {self.consecutive_losses}회)")
            self.consecutive_losses = 0
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            상태 정보 딕셔너리
        """
        return {
            "trading_paused": self.trading_paused,
            "pause_until": self.pause_until.isoformat() if self.pause_until else None,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl,
            "daily_loss_ratio": abs(self.daily_pnl) / self.initial_daily_capital if self.initial_daily_capital > 0 else 0.0,
            "base_position_size": self.base_position_size,
            "daily_loss_limit": self.daily_loss_limit,
            "max_consecutive_losses": self.max_consecutive_losses
        }
    
    def reset(self):
        """상태 리셋 (새 백테스트 시작 시)"""
        self.consecutive_losses = 0
        self.trading_paused = False
        self.pause_until = None
        self.current_date = None
        self.daily_pnl = 0.0
        self.initial_daily_capital = 0.0
        logger.info("🔄 리스크 가디언 상태 리셋 완료")

