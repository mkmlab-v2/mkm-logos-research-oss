#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수익 확정 및 잠금 타입 정의 (Type-First Development)

작성일: 2026-01-21
목적: 비트코인 트레이딩 봇의 수익 확정 로직을 타입 안전하게 구현
"""

from typing import Dict, Optional, Literal
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProfitRealizationResult:
    """
    수익 확정 결과
    
    Attributes:
        success: 수익 확정 성공 여부
        realized_profit: 확정된 수익 (USDT)
        entry_price: 진입 가격
        exit_price: 청산 가격
        position_size: 포지션 크기
        profit_percentage: 수익률 (%)
        timestamp: 확정 시각
        transaction_id: 거래 ID (선택적)
        error_message: 에러 메시지 (선택적)
    """
    success: bool
    realized_profit: float
    entry_price: float
    exit_price: float
    position_size: float
    profit_percentage: float
    timestamp: datetime
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "realized_profit": self.realized_profit,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "position_size": self.position_size,
            "profit_percentage": self.profit_percentage,
            "timestamp": self.timestamp.isoformat(),
            "transaction_id": self.transaction_id,
            "error_message": self.error_message
        }


@dataclass
class ProfitLockStatus:
    """
    수익 잠금 상태
    
    Attributes:
        is_locked: 잠금 여부
        locked_profit: 잠금된 수익 (USDT)
        lock_timestamp: 잠금 시각
        unlock_conditions: 잠금 해제 조건
    """
    is_locked: bool
    locked_profit: float
    lock_timestamp: datetime
    unlock_conditions: Dict[str, any]
    
    def to_dict(self) -> Dict[str, any]:
        """딕셔너리로 변환"""
        return {
            "is_locked": self.is_locked,
            "locked_profit": self.locked_profit,
            "lock_timestamp": self.lock_timestamp.isoformat(),
            "unlock_conditions": self.unlock_conditions
        }


@dataclass
class PositionInfo:
    """
    포지션 정보
    
    Attributes:
        symbol: 거래 심볼
        side: 포지션 방향 ("LONG" 또는 "SHORT")
        size: 포지션 크기
        entry_price: 진입 가격
        current_price: 현재 가격
        unrealized_pnl: 미실현 손익
        leverage: 레버리지
    """
    symbol: str
    side: Literal["LONG", "SHORT"]
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    leverage: float
    
    def calculate_profit_percentage(self) -> float:
        """수익률 계산 (%)"""
        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100 * self.leverage
        else:  # SHORT
            return ((self.entry_price - self.current_price) / self.entry_price) * 100 * self.leverage
    
    def to_dict(self) -> Dict[str, any]:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "leverage": self.leverage,
            "profit_percentage": self.calculate_profit_percentage()
        }


@dataclass
class ProfitConfirmationRequest:
    """
    수익 확정 요청
    
    Attributes:
        symbol: 거래 심볼
        position_side: 포지션 방향
        min_profit_percentage: 최소 수익률 (%)
        require_confirmation: 수동 확인 필요 여부
    """
    symbol: str
    position_side: Literal["LONG", "SHORT"]
    min_profit_percentage: float = 0.0
    require_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, any]:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "position_side": self.position_side,
            "min_profit_percentage": self.min_profit_percentage,
            "require_confirmation": self.require_confirmation
        }

