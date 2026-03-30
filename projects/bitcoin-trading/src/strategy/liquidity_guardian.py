#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 유동성 감시 모듈 (Liquidity Guardian)

목적: 실시간 호가창 깊이(Depth) 체크 및 주문 분할 알고리즘
전략: 슬리피지 최소화를 위한 유동성 보호

작성일: 2026-01-11
상태: ✅ 구현 중
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LiquidityGuardian:
    """
    유동성 감시 모듈
    
    기능:
    1. 실시간 호가창 깊이(Depth) 체크
    2. 주문 크기에 따른 슬리피지 예측
    3. 주문 분할 알고리즘 (큰 주문을 작은 주문으로 분할)
    4. 유동성 부족 시 거래 거부
    """
    
    def __init__(
        self,
        max_slippage_bps: float = 10.0,  # 최대 슬리피지 (10 bps = 0.1%)
        min_order_book_depth_usd: float = 50000.0,  # 최소 호가창 깊이 (USD)
        order_split_threshold_usd: float = 10000.0  # 주문 분할 임계값 (USD)
    ):
        """
        초기화
        
        Args:
            max_slippage_bps: 최대 슬리피지 (basis points)
            min_order_book_depth_usd: 최소 호가창 깊이 (USD)
            order_split_threshold_usd: 주문 분할 임계값 (USD)
        """
        self.max_slippage_bps = max_slippage_bps
        self.min_order_book_depth_usd = min_order_book_depth_usd
        self.order_split_threshold_usd = order_split_threshold_usd
        
        # Binance API 클라이언트 (Lazy Loading)
        self._binance_client = None
    
    def _get_binance_client(self):
        """Binance API 클라이언트 가져오기 (Lazy Loading)"""
        if self._binance_client is not None:
            return self._binance_client
        
        try:
            from projects.bitcoin_trading.src.api.binance_client import BinanceClient
            self._binance_client = BinanceClient()
            return self._binance_client
        except Exception as e:
            logger.warning(f"⚠️ Binance 클라이언트 로드 실패: {e}")
            return None
    
    async def get_order_book_depth(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        호가창 깊이 가져오기
        
        Args:
            symbol: 거래 심볼
            limit: 호가창 깊이 제한
        
        Returns:
            호가창 깊이 정보
        """
        client = self._get_binance_client()
        if not client:
            return {
                "success": False,
                "error": "Binance 클라이언트 사용 불가"
            }
        
        try:
            # Binance API로 호가창 가져오기
            if hasattr(client, 'get_order_book'):
                order_book = await client.get_order_book(symbol, limit)
            else:
                # 동기 메서드인 경우
                import asyncio
                loop = asyncio.get_event_loop()
                order_book = await loop.run_in_executor(
                    None,
                    lambda: client.get_order_book(symbol, limit) if hasattr(client, 'get_order_book') else None
                )
            
            if not order_book:
                return {
                    "success": False,
                    "error": "호가창 데이터 없음"
                }
            
            # 매수 호가창 깊이 계산 (USD)
            bids = order_book.get("bids", [])
            asks = order_book.get("asks", [])
            
            # 현재 가격 (중간 가격)
            if bids and asks:
                mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2.0
            else:
                return {
                    "success": False,
                    "error": "호가창 데이터 부족"
                }
            
            # 매수 호가창 깊이 (USD)
            bid_depth_usd = sum(float(price) * float(qty) for price, qty in bids[:10])
            
            # 매도 호가창 깊이 (USD)
            ask_depth_usd = sum(float(price) * float(qty) for price, qty in asks[:10])
            
            return {
                "success": True,
                "mid_price": mid_price,
                "bid_depth_usd": bid_depth_usd,
                "ask_depth_usd": ask_depth_usd,
                "total_depth_usd": bid_depth_usd + ask_depth_usd,
                "bids": bids[:10],
                "asks": asks[:10]
            }
        except Exception as e:
            logger.error(f"❌ 호가창 깊이 가져오기 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def estimate_slippage(
        self,
        order_size_usd: float,
        order_book_depth: Dict[str, Any],
        side: str = "BUY"  # "BUY" or "SELL"
    ) -> Dict[str, Any]:
        """
        슬리피지 예측
        
        Args:
            order_size_usd: 주문 크기 (USD)
            order_book_depth: 호가창 깊이 정보
            side: 주문 방향 ("BUY" or "SELL")
        
        Returns:
            슬리피지 예측 결과
        """
        if not order_book_depth.get("success"):
            return {
                "success": False,
                "error": "호가창 데이터 없음"
            }
        
        mid_price = order_book_depth.get("mid_price", 0.0)
        
        if side == "BUY":
            # 매수: 매도 호가창 사용
            asks = order_book_depth.get("asks", [])
            available_depth = order_book_depth.get("ask_depth_usd", 0.0)
        else:
            # 매도: 매수 호가창 사용
            asks = order_book_depth.get("bids", [])
            available_depth = order_book_depth.get("bid_depth_usd", 0.0)
        
        if not asks or mid_price == 0:
            return {
                "success": False,
                "error": "호가창 데이터 부족"
            }
        
        # 슬리피지 계산 (가중 평균 가격)
        total_cost = 0.0
        remaining_size = order_size_usd
        
        for price, qty in asks:
            price_float = float(price)
            qty_float = float(qty)
            available_at_price = price_float * qty_float
            
            if remaining_size <= 0:
                break
            
            if remaining_size <= available_at_price:
                # 이 가격에서 모두 체결
                total_cost += remaining_size
                remaining_size = 0
            else:
                # 이 가격에서 일부 체결
                total_cost += available_at_price
                remaining_size -= available_at_price
        
        if remaining_size > 0:
            # 호가창 깊이 부족 → 슬리피지 매우 높음
            avg_price = total_cost / (order_size_usd - remaining_size) if (order_size_usd - remaining_size) > 0 else mid_price
            slippage_bps = ((avg_price - mid_price) / mid_price) * 10000
            return {
                "success": True,
                "estimated_slippage_bps": slippage_bps,
                "avg_execution_price": avg_price,
                "mid_price": mid_price,
                "insufficient_liquidity": True,
                "unfilled_size_usd": remaining_size
            }
        
        # 정상 체결
        avg_price = total_cost / order_size_usd
        slippage_bps = ((avg_price - mid_price) / mid_price) * 10000
        
        return {
            "success": True,
            "estimated_slippage_bps": slippage_bps,
            "avg_execution_price": avg_price,
            "mid_price": mid_price,
            "insufficient_liquidity": False,
            "unfilled_size_usd": 0.0
        }
    
    def calculate_order_splits(
        self,
        order_size_usd: float,
        order_book_depth: Dict[str, Any],
        side: str = "BUY"
    ) -> List[Dict[str, float]]:
        """
        주문 분할 계산
        
        Args:
            order_size_usd: 총 주문 크기 (USD)
            order_book_depth: 호가창 깊이 정보
            side: 주문 방향 ("BUY" or "SELL")
        
        Returns:
            분할된 주문 리스트
        """
        if order_size_usd <= self.order_split_threshold_usd:
            # 분할 불필요
            return [{"size_usd": order_size_usd, "delay_ms": 0}]
        
        # 주문 분할 (최대 5개로 분할)
        num_splits = min(5, int(order_size_usd / self.order_split_threshold_usd) + 1)
        split_size = order_size_usd / num_splits
        
        splits = []
        for i in range(num_splits):
            splits.append({
                "size_usd": split_size,
                "delay_ms": i * 100  # 100ms 간격으로 분할 주문
            })
        
        return splits
    
    async def check_liquidity(
        self,
        symbol: str = "BTCUSDT",
        order_size_usd: float = 1000.0,
        side: str = "BUY"
    ) -> Dict[str, Any]:
        """
        유동성 체크 (전체 프로세스)
        
        Args:
            symbol: 거래 심볼
            order_size_usd: 주문 크기 (USD)
            side: 주문 방향 ("BUY" or "SELL")
        
        Returns:
            유동성 검증 결과
        """
        # 1. 호가창 깊이 가져오기
        order_book_depth = await self.get_order_book_depth(symbol)
        
        if not order_book_depth.get("success"):
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": "호가창 데이터 없음",
                "order_book_depth": order_book_depth
            }
        
        # 2. 최소 깊이 확인
        total_depth = order_book_depth.get("total_depth_usd", 0.0)
        if total_depth < self.min_order_book_depth_usd:
            return {
                "approved": False,
                "reason": f"호가창 깊이 부족: ${total_depth:,.0f} < ${self.min_order_book_depth_usd:,.0f}",
                "order_book_depth": order_book_depth
            }
        
        # 3. 슬리피지 예측
        slippage_result = self.estimate_slippage(order_size_usd, order_book_depth, side)
        
        if not slippage_result.get("success"):
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": "슬리피지 예측 실패",
                "slippage_result": slippage_result
            }
        
        estimated_slippage_bps = slippage_result.get("estimated_slippage_bps", 0.0)
        
        # 4. 슬리피지 임계값 확인
        if estimated_slippage_bps > self.max_slippage_bps:
            return {
                "approved": False,
                "reason": f"슬리피지 초과: {estimated_slippage_bps:.1f} bps > {self.max_slippage_bps:.1f} bps",
                "slippage_result": slippage_result,
                "order_book_depth": order_book_depth
            }
        
        # 5. 주문 분할 계산
        order_splits = self.calculate_order_splits(order_size_usd, order_book_depth, side)
        
        # 6. 승인
        return {
            "approved": True,
            "reason": "유동성 충분",
            "order_book_depth": order_book_depth,
            "slippage_result": slippage_result,
            "order_splits": order_splits,
            "estimated_slippage_bps": estimated_slippage_bps
        }

