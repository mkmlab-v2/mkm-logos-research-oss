#!/usr/bin/env python3
"""
뉴스/공시 → 전략 필드(JSON) 추출을 위한 표준 스키마 정의 모듈.

Phase 5.3 P1 세로 슬라이스의 핵심: 비정형 텍스트(뉴스, 공시)를
트레이딩 엔진이 직접 사용할 수 있는 "전략 필드" 구조로 정규화한다.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


EventType = Literal[
    "LISTING",
    "DELISTING",
    "HACK",
    "REGULATION",
    "PARTNERSHIP",
    "EARNINGS",
    "UPGRADE",
    "OUTAGE",
    "OTHER",
]

DirectionType = Literal["BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"]

ImpactScope = Literal["MARKET_WIDE", "SECTOR", "SINGLE_ASSET"]

TimeHorizon = Literal["INTRADAY", "SWING", "POSITION", "LONG_TERM"]


class StrategicNewsEvent(BaseModel):
    """
    P1 (뉴스/공시)용 표준 전략 필드 스키마.

    최소 필드 셋은 트레이딩 엔진과 리스크/전략 레이어가 공통으로
    해석할 수 있는 수준으로 설계되었다.
    """

    event_id: str = Field(
        ...,
        description="내부용 유니크 ID (예: hash 또는 file_based_memory의 key)",
    )
    source: str = Field(
        ...,
        description="이벤트 출처 (예: binance_announcement, upbit_notice, news_api 등)",
    )
    symbol: str = Field(
        ...,
        description="주요 대상 심볼 (예: BTCUSDT, ETHUSDT, 또는 MULTI)",
    )
    event_type: EventType = Field(
        ...,
        description="이벤트 유형 (LISTING, DELISTING, HACK, REGULATION, ...)",
    )
    urgency: int = Field(
        ...,
        ge=1,
        le=5,
        description="긴급도 (1=낮음, 5=초긴급)",
    )
    direction: DirectionType = Field(
        ...,
        description="시장 영향 방향 (BULLISH, BEARISH, NEUTRAL, UNKNOWN)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="이 해석에 대한 신뢰도 (0.0~1.0)",
    )
    headline: str = Field(
        ...,
        description="한 줄 요약 제목",
    )
    summary: str = Field(
        ...,
        description="2~4문장 수준의 자연어 요약",
    )
    published_at: datetime = Field(
        ...,
        description="이벤트 발생/발표 시각 (UTC)",
    )

    # 확장 필드 (선택)
    impact_scope: Optional[ImpactScope] = Field(
        None,
        description="영향 범위 (MARKET_WIDE, SECTOR, SINGLE_ASSET)",
    )
    time_horizon: Optional[TimeHorizon] = Field(
        None,
        description="전략적 시간 축 (INTRADAY, SWING, POSITION, LONG_TERM)",
    )
    market_sentiment_latent: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="시장 심리의 잠복 점수 (-1.0=극단적 공포, 0=중립, 1.0=극단적 탐욕)",
    )
    actor_intent_latent: Optional[str] = Field(
        None,
        description="주요 행위자 의도의 잠복 해석 (예: 'whale_accumulation', 'retail_exit')",
    )
    risk_tags: List[str] = Field(
        default_factory=list,
        description="리스크 관련 태그 (예: REGULATORY, SECURITY, LIQUIDITY 등)",
    )
    strategy_hint: Optional[str] = Field(
        None,
        description="전략적 힌트 (예: 단기 급등 후 조정 가능, 추격 매수 주의)",
    )
    raw_url: Optional[HttpUrl] = Field(
        None,
        description="원문 URL (있다면)",
    )
    raw_ref_id: Optional[str] = Field(
        None,
        description="원문 저장소 키 (file_based_memory ID 등)",
    )

    @validator("symbol")
    def normalize_symbol(cls, v: str) -> str:
        # 심볼 표기를 상위 레이어에서 일관되게 쓰도록 대문자로 통일
        return v.upper()

