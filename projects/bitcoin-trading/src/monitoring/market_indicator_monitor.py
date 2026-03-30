#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 시장 지표 모니터링 시스템 (Market Indicator Monitor)

나스닥 지수 및 환율 실시간 모니터링
- 나스닥 23,500 기준선 모니터링
- 환율 1,480원 기준선 모니터링
- 점진적 청산 전략에 활용

작성일: 2026-02-08
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
import aiohttp
import json

logger = logging.getLogger(__name__)


class MarketIndicatorMonitor:
    """
    시장 지표 모니터링 시스템
    
    핵심 기능:
    1. 나스닥 지수 실시간 조회
    2. 환율 실시간 조회
    3. 기준선 모니터링 (나스닥 23,500, 환율 1,480)
    4. 점진적 청산 전략에 활용
    """
    
    def __init__(
        self,
        nasdaq_threshold: float = 23500.0,
        exchange_rate_threshold: float = 1480.0,
        update_interval: int = 300  # 5분마다 업데이트
    ):
        """
        초기화
        
        Args:
            nasdaq_threshold: 나스닥 기준선 (기본값: 23,500)
            exchange_rate_threshold: 환율 기준선 (기본값: 1,480원)
            update_interval: 업데이트 간격 (초)
        """
        self.nasdaq_threshold = nasdaq_threshold
        self.exchange_rate_threshold = exchange_rate_threshold
        self.update_interval = update_interval
        
        # 캐시된 데이터
        self.nasdaq_level: Optional[float] = None
        self.exchange_rate: Optional[float] = None
        self.last_update: Optional[datetime] = None
        
        logger.info(f"✅ 시장 지표 모니터링 시스템 초기화 완료")
        logger.info(f"   나스닥 기준선: {nasdaq_threshold:,.0f}")
        logger.info(f"   환율 기준선: {exchange_rate_threshold:,.0f}원")
    
    async def fetch_nasdaq_level(self) -> Optional[float]:
        """
        나스닥 지수 조회
        
        Returns:
            나스닥 지수 (없으면 None)
        """
        try:
            # Alpha Vantage API 사용 (무료 티어)
            # 또는 다른 무료 API 사용 가능
            # 여기서는 예시로 Alpha Vantage 사용
            
            # 실제로는 환경 변수에서 API 키를 가져와야 함
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
            
            if not api_key:
                # API 키가 없으면 대체 방법 사용
                # Yahoo Finance API 또는 다른 무료 API
                url = "https://query1.finance.yahoo.com/v8/finance/chart/^IXIC"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("chart") and data["chart"].get("result"):
                                result = data["chart"]["result"][0]
                                if result.get("meta"):
                                    nasdaq_level = result["meta"].get("regularMarketPrice")
                                    if nasdaq_level:
                                        return float(nasdaq_level)
            
            # Alpha Vantage API 사용 (API 키가 있는 경우)
            if api_key:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IXIC&apikey={api_key}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("Global Quote"):
                                quote = data["Global Quote"]
                                price = quote.get("05. price")
                                if price:
                                    return float(price)
            
            logger.warning("⚠️ 나스닥 지수 조회 실패 (API 키 없음 또는 네트워크 오류)")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ 나스닥 지수 조회 오류: {e}")
            return None
    
    async def fetch_exchange_rate(self) -> Optional[float]:
        """
        환율 조회 (USD/KRW)
        
        Returns:
            환율 (없으면 None)
        """
        try:
            # 한국은행 API 또는 다른 무료 API 사용
            # 여기서는 예시로 ExchangeRate-API 사용
            
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("rates"):
                            krw_rate = data["rates"].get("KRW")
                            if krw_rate:
                                return float(krw_rate)
            
            logger.warning("⚠️ 환율 조회 실패 (API 오류)")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ 환율 조회 오류: {e}")
            return None
    
    async def update_indicators(self) -> Dict[str, Optional[float]]:
        """
        시장 지표 업데이트
        
        Returns:
            업데이트된 지표 딕셔너리
        """
        try:
            # 나스닥 지수 조회
            nasdaq_level = await self.fetch_nasdaq_level()
            if nasdaq_level:
                self.nasdaq_level = nasdaq_level
                logger.info(f"📊 나스닥 지수: {nasdaq_level:,.2f}")
            
            # 환율 조회
            exchange_rate = await self.fetch_exchange_rate()
            if exchange_rate:
                self.exchange_rate = exchange_rate
                logger.info(f"💱 환율: {exchange_rate:,.2f}원")
            
            self.last_update = datetime.now()
            
            return {
                "nasdaq_level": self.nasdaq_level,
                "exchange_rate": self.exchange_rate,
                "last_update": self.last_update.isoformat() if self.last_update else None
            }
            
        except Exception as e:
            logger.error(f"❌ 시장 지표 업데이트 오류: {e}")
            return {
                "nasdaq_level": self.nasdaq_level,
                "exchange_rate": self.exchange_rate,
                "last_update": self.last_update.isoformat() if self.last_update else None
            }
    
    def check_thresholds(self) -> Dict[str, Any]:
        """
        기준선 확인
        
        Returns:
            기준선 확인 결과
        """
        result = {
            "nasdaq_above_threshold": False,
            "exchange_rate_above_threshold": False,
            "nasdaq_level": self.nasdaq_level,
            "exchange_rate": self.exchange_rate,
            "liquidation_recommended": False,
            "liquidation_ratio": 0.0,
            "liquidation_reason": None
        }
        
        # 나스닥 기준선 확인
        if self.nasdaq_level is not None:
            if self.nasdaq_level >= self.nasdaq_threshold:
                result["nasdaq_above_threshold"] = True
                result["liquidation_recommended"] = True
                result["liquidation_ratio"] = 0.3  # 30% 청산
                result["liquidation_reason"] = f"나스닥 {self.nasdaq_level:,.0f} 돌파"
                logger.warning(
                    f"⚠️ 나스닥 기준선 돌파: {self.nasdaq_level:,.2f} >= {self.nasdaq_threshold:,.0f}"
                )
        
        # 환율 기준선 확인
        if self.exchange_rate is not None:
            if self.exchange_rate >= self.exchange_rate_threshold:
                result["exchange_rate_above_threshold"] = True
                if not result["liquidation_recommended"]:
                    result["liquidation_recommended"] = True
                    result["liquidation_ratio"] = 0.2  # 20% 청산
                    result["liquidation_reason"] = f"환율 {self.exchange_rate:,.0f}원 돌파"
                else:
                    # 두 기준선 모두 돌파 시 청산 비율 증가
                    result["liquidation_ratio"] = min(result["liquidation_ratio"] + 0.2, 0.5)  # 최대 50%
                    result["liquidation_reason"] = f"나스닥 {self.nasdaq_level:,.0f} + 환율 {self.exchange_rate:,.0f}원 돌파"
                logger.warning(
                    f"⚠️ 환율 기준선 돌파: {self.exchange_rate:,.2f} >= {self.exchange_rate_threshold:,.0f}"
                )
        
        return result
    
    def get_indicators(self) -> Dict[str, Optional[float]]:
        """
        현재 지표 반환
        
        Returns:
            현재 지표 딕셔너리
        """
        return {
            "nasdaq_level": self.nasdaq_level,
            "exchange_rate": self.exchange_rate,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }


# 모듈 import를 위한 os 추가
import os

