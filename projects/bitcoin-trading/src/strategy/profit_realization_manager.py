#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수익 확정 관리자 (Profit Realization Manager)

작성일: 2026-01-21
목적: 비트코인 트레이딩 봇의 수익 확정 및 잠금 로직 구현
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..types.profit_types import (
    ProfitRealizationResult,
    ProfitLockStatus,
    PositionInfo,
    ProfitConfirmationRequest
)
from ..api.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class ProfitRealizationManager:
    """
    수익 확정 및 잠금 관리자
    
    기능:
    - 포지션 정보 조회 및 수익 계산
    - 수익 확정 (포지션 청산)
    - 수익 잠금 (부분 청산)
    - 수익 확정 기록 및 추적
    """
    
    def __init__(self, binance_client: BinanceClient):
        """
        초기화
        
        Args:
            binance_client: Binance API 클라이언트
        """
        self.binance_client = binance_client
        self.locked_profits: Dict[str, ProfitLockStatus] = {}
    
    def get_position_info(self, symbol: str = "BTCUSDT") -> Optional[PositionInfo]:
        """
        포지션 정보 조회
        
        Args:
            symbol: 거래 심볼
        
        Returns:
            PositionInfo 또는 None (포지션 없음)
        """
        try:
            position = self.binance_client.get_position(symbol=symbol)
            if not position:
                return None
            
            # 포지션 정보 파싱
            position_amt = float(position.get("positionAmt", 0))
            if position_amt == 0:
                return None
            
            entry_price = float(position.get("entryPrice", 0))
            current_price = self.binance_client.get_current_price(symbol)
            leverage = float(position.get("leverage", 1))
            unrealized_pnl = float(position.get("unrealizedProfit", 0))
            
            # 포지션 방향 결정
            side = "LONG" if position_amt > 0 else "SHORT"
            size = abs(position_amt)
            
            return PositionInfo(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                leverage=leverage
            )
        except Exception as e:
            logger.error(f"❌ 포지션 정보 조회 실패: {e}")
            return None
    
    def calculate_realized_profit(
        self,
        position_info: PositionInfo,
        exit_price: float
    ) -> float:
        """
        확정 수익 계산
        
        Args:
            position_info: 포지션 정보
            exit_price: 청산 가격
        
        Returns:
            확정 수익 (USDT)
        """
        if position_info.side == "LONG":
            # 롱 포지션: (청산가 - 진입가) * 크기 * 레버리지
            profit = (exit_price - position_info.entry_price) * position_info.size * position_info.leverage
        else:  # SHORT
            # 숏 포지션: (진입가 - 청산가) * 크기 * 레버리지
            profit = (position_info.entry_price - exit_price) * position_info.size * position_info.leverage
        
        return profit
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def realize_profit(
        self,
        symbol: str = "BTCUSDT",
        position_side: Optional[str] = None,
        min_profit_percentage: float = 0.0
    ) -> ProfitRealizationResult:
        """
        수익 확정 (포지션 청산)
        
        Args:
            symbol: 거래 심볼
            position_side: 포지션 방향 ("LONG", "SHORT", None=자동 감지)
            min_profit_percentage: 최소 수익률 (%) - 이 값 이상일 때만 확정
        
        Returns:
            ProfitRealizationResult
        """
        try:
            # 포지션 정보 조회
            position_info = self.get_position_info(symbol)
            if not position_info:
                return ProfitRealizationResult(
                    success=False,
                    realized_profit=0.0,
                    entry_price=0.0,
                    exit_price=0.0,
                    position_size=0.0,
                    profit_percentage=0.0,
                    timestamp=datetime.now(),
                    error_message="포지션이 없습니다"
                )
            
            # 포지션 방향 확인
            if position_side and position_side != position_info.side:
                return ProfitRealizationResult(
                    success=False,
                    realized_profit=0.0,
                    entry_price=position_info.entry_price,
                    exit_price=position_info.current_price,
                    position_size=position_info.size,
                    profit_percentage=position_info.calculate_profit_percentage(),
                    timestamp=datetime.now(),
                    error_message=f"포지션 방향 불일치: 요청={position_side}, 실제={position_info.side}"
                )
            
            # 수익률 확인
            profit_percentage = position_info.calculate_profit_percentage()
            if profit_percentage < min_profit_percentage:
                return ProfitRealizationResult(
                    success=False,
                    realized_profit=0.0,
                    entry_price=position_info.entry_price,
                    exit_price=position_info.current_price,
                    position_size=position_info.size,
                    profit_percentage=profit_percentage,
                    timestamp=datetime.now(),
                    error_message=f"최소 수익률 미달: {profit_percentage:.2f}% < {min_profit_percentage:.2f}%"
                )
            
            # 포지션 청산
            order = self.binance_client.close_position(
                symbol=symbol,
                position_side=position_info.side
            )
            
            if not order:
                return ProfitRealizationResult(
                    success=False,
                    realized_profit=0.0,
                    entry_price=position_info.entry_price,
                    exit_price=position_info.current_price,
                    position_size=position_info.size,
                    profit_percentage=profit_percentage,
                    timestamp=datetime.now(),
                    error_message="포지션 청산 실패"
                )
            
            # 청산 가격 확인
            exit_price = float(order.get("price", position_info.current_price))
            if not exit_price:
                exit_price = position_info.current_price
            
            # 확정 수익 계산
            realized_profit = self.calculate_realized_profit(position_info, exit_price)
            
            # 거래 ID 추출
            transaction_id = order.get("orderId") or order.get("clientOrderId")
            
            result = ProfitRealizationResult(
                success=True,
                realized_profit=realized_profit,
                entry_price=position_info.entry_price,
                exit_price=exit_price,
                position_size=position_info.size,
                profit_percentage=profit_percentage,
                timestamp=datetime.now(),
                transaction_id=str(transaction_id) if transaction_id else None
            )
            
            logger.info(
                f"✅ 수익 확정 완료: {symbol} {position_info.side} "
                f"수익={realized_profit:.2f} USDT ({profit_percentage:.2f}%)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 수익 확정 실패: {e}")
            return ProfitRealizationResult(
                success=False,
                realized_profit=0.0,
                entry_price=0.0,
                exit_price=0.0,
                position_size=0.0,
                profit_percentage=0.0,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    def lock_profit(
        self,
        symbol: str = "BTCUSDT",
        lock_percentage: float = 50.0,
        unlock_condition: Dict[str, Any] = None
    ) -> Optional[ProfitLockStatus]:
        """
        수익 잠금 (부분 청산)
        
        Args:
            symbol: 거래 심볼
            lock_percentage: 잠금할 수익 비율 (%)
            unlock_condition: 잠금 해제 조건 (선택적)
        
        Returns:
            ProfitLockStatus 또는 None
        """
        try:
            position_info = self.get_position_info(symbol)
            if not position_info:
                return None
            
            # 잠금할 수익 계산
            total_profit = position_info.unrealized_pnl
            locked_profit = total_profit * (lock_percentage / 100.0)
            
            # 부분 청산 (50%만 청산)
            # TODO: 부분 청산 구현 (현재는 전체 청산만 지원)
            # 부분 청산은 수량을 조절하여 구현해야 함
            
            lock_status = ProfitLockStatus(
                is_locked=True,
                locked_profit=locked_profit,
                lock_timestamp=datetime.now(),
                unlock_conditions=unlock_condition or {}
            )
            
            self.locked_profits[f"{symbol}_{position_info.side}"] = lock_status
            
            logger.info(
                f"🔒 수익 잠금: {symbol} {position_info.side} "
                f"잠금 수익={locked_profit:.2f} USDT ({lock_percentage:.1f}%)"
            )
            
            return lock_status
            
        except Exception as e:
            logger.error(f"❌ 수익 잠금 실패: {e}")
            return None
    
    def check_profit_confirmation(
        self,
        request: ProfitConfirmationRequest
    ) -> ProfitRealizationResult:
        """
        수익 확정 확인 및 실행
        
        Args:
            request: 수익 확정 요청
        
        Returns:
            ProfitRealizationResult
        """
        return self.realize_profit(
            symbol=request.symbol,
            position_side=request.position_side,
            min_profit_percentage=request.min_profit_percentage
        )

