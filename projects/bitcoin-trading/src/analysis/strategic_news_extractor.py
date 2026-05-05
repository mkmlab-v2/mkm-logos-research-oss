#!/usr/bin/env python3
"""
뉴스/공시 원문 텍스트 → StrategicNewsEvent 변환기 (P1 세로 슬라이스 초안).

Phase 5.3 P1 단계에서 사용할 "전략 필드 추출"의 최소 동작 버전이다.
현재는 키워드 기반 휴리스틱으로 동작하며, 추후 14B/제5회로 기반
고급 추론기로 교체될 수 있도록 순수 함수 형태로 분리해 두었다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .strategic_news_event import (
    StrategicNewsEvent,
    EventType,
    DirectionType,
    ImpactScope,
    TimeHorizon,
)
from .sasang_emotion_bridge import build_emotion_weight

from tools.tools.core.file_based_memory import FileBasedMemory


def _classify_event_type(raw_text: str) -> EventType:
    t = raw_text.lower()
    if any(k in t for k in ["상장", "listing", "list on", "will list", "new spot pair"]):
        return "LISTING"
    if any(k in t for k in ["상폐", "delisting", "delist"]):
        return "DELISTING"
    if any(k in t for k in ["해킹", "hack", "exploit", "security breach"]):
        return "HACK"
    if any(k in t for k in ["규제", "regulation", "sec ", "fined", "제재"]):
        return "REGULATION"
    if any(k in t for k in ["제휴", "파트너십", "partnership", "collaborat"]):
        return "PARTNERSHIP"
    if any(k in t for k in ["earnings", "실적", "분기보고서"]):
        return "EARNINGS"
    if any(k in t for k in ["업그레이드", "upgrade", "hardfork", "hard fork"]):
        return "UPGRADE"
    if any(k in t for k in ["장애", "outage", "service disruption", "downtime"]):
        return "OUTAGE"
    return "OTHER"


def _infer_direction(event_type: EventType, raw_text: str) -> DirectionType:
    t = raw_text.lower()
    if event_type in ("LISTING", "PARTNERSHIP", "UPGRADE", "EARNINGS"):
        # 악재 키워드가 같이 있으면 중립/음수로 내린다.
        if any(k in t for k in ["investigation", "probe", "fine", "penalty", "down"]):
            return "NEUTRAL"
        return "BULLISH"
    if event_type in ("DELISTING", "HACK", "OUTAGE", "REGULATION"):
        return "BEARISH"
    # 기타는 텍스트 분위기에 따라 간단 분류
    if any(k in t for k in ["soars", "jumps", "surges", "급등"]):
        return "BULLISH"
    if any(k in t for k in ["plunges", "drops", "crash", "급락"]):
        return "BEARISH"
    return "UNKNOWN"


def _infer_urgency(event_type: EventType, raw_text: str) -> int:
    t = raw_text.lower()
    if event_type in ("HACK", "DELISTING", "OUTAGE", "REGULATION"):
        return 5
    if event_type in ("LISTING", "UPGRADE", "PARTNERSHIP"):
        return 4
    if "urgent" in t or "긴급" in t:
        return 4
    return 3


def _infer_impact_scope(event_type: EventType) -> ImpactScope:
    if event_type in ("REGULATION", "OUTAGE"):
        return "MARKET_WIDE"
    if event_type in ("LISTING", "DELISTING", "HACK", "UPGRADE"):
        return "SINGLE_ASSET"
    return "SECTOR"


def _infer_time_horizon(event_type: EventType) -> TimeHorizon:
    if event_type in ("HACK", "OUTAGE"):
        return "INTRADAY"
    if event_type in ("LISTING", "DELISTING", "UPGRADE"):
        return "SWING"
    if event_type in ("REGULATION", "PARTNERSHIP", "EARNINGS"):
        return "POSITION"
    return "LONG_TERM"


def _extract_headline_and_summary(raw_text: str) -> Tuple[str, str]:
    text = raw_text.strip()
    if not text:
        return "", ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    headline = lines[0][:160]
    if len(lines) == 1:
        summary = lines[0][:512]
    else:
        summary = " ".join(lines)[:1024]
    return headline, summary


def _infer_market_sentiment_latent(raw_text: str) -> Optional[float]:
    """
    시장 심리 잠복 점수의 간단한 휴리스틱 버전.

    - 이후 14B/제5회로가 직접 이 값을 채우게 될 것이므로,
      지금은 극단적인 공포/탐욕 패턴만 거칠게 감지하는 수준으로 둔다.
    """
    t = raw_text.lower()
    score = 0.0
    # 공포 단어
    if any(k in t for k in ["panic", "fear", "capitulation", "패닉", "공포", "투매"]):
        score -= 0.6
    if any(k in t for k in ["crash", "plunge", "급락", "폭락"]):
        score -= 0.4
    # 탐욕 단어
    if any(k in t for k in ["euphoria", "mania", "fomo", "탐욕", "광풍"]):
        score += 0.6
    if any(k in t for k in ["surge", "soars", "jumps", "all-time high", "사상 최고가"]):
        score += 0.4

    # 범위 클리핑
    if score == 0.0:
        return None
    return max(-1.0, min(1.0, score))


def _infer_actor_intent_latent(raw_text: str) -> Optional[str]:
    """
    주요 행위자 의도의 잠복 해석에 대한 가벼운 키워드 분류기.

    - 이후 14B/제5회로 기반 추론기로 교체될 수 있도록 문자열 라벨만 반환한다.
    """
    t = raw_text.lower()
    if any(k in t for k in ["whale", "large holder", "기관", "institutional"]):
        if any(k in t for k in ["accumulate", "buying", "매수", "매집"]):
            return "whale_accumulation"
        if any(k in t for k in ["sell", "dump", "매도", "투매"]):
            return "whale_distribution"
    if any(k in t for k in ["retail", "개인 투자자"]):
        if any(k in t for k in ["exit", "sell", "매도", "손절"]):
            return "retail_exit"
    return None


def build_strategic_news_event_from_text(
    raw_text: str,
    *,
    event_id: str,
    source: str,
    symbol_hint: Optional[str] = None,
    published_at: Optional[datetime] = None,
    raw_url: Optional[str] = None,
    raw_ref_id: Optional[str] = None,
    panic_ratio: Optional[float] = None,
    fomo_index: Optional[float] = None,
    market_volatility: Optional[float] = None,
    llm_sentiment_score: Optional[float] = None,
) -> StrategicNewsEvent:
    """
    뉴스/공시 원문 텍스트를 StrategicNewsEvent로 변환하는 최소 구현.

    현재는 키워드 휴리스틱 기반이며, 이후 14B/제5회로 기반 추론기로
    교체되더라도 상위 코드는 이 함수 시그니처만 따르면 된다.
    """
    event_type = _classify_event_type(raw_text)
    direction = _infer_direction(event_type, raw_text)
    urgency = _infer_urgency(event_type, raw_text)
    impact_scope = _infer_impact_scope(event_type)
    time_horizon = _infer_time_horizon(event_type)
    headline, summary = _extract_headline_and_summary(raw_text)
    market_sentiment_latent = _infer_market_sentiment_latent(raw_text)
    actor_intent_latent = _infer_actor_intent_latent(raw_text)
    emotion = build_emotion_weight(
        panic_ratio=panic_ratio,
        fomo_index=fomo_index,
        market_volatility=market_volatility,
        market_sentiment_latent=market_sentiment_latent,
        llm_sentiment_score=llm_sentiment_score,
    )

    created_at = published_at or datetime.now(timezone.utc)

    return StrategicNewsEvent(
        event_id=event_id,
        source=source,
        symbol=symbol_hint or "MULTI",
        event_type=event_type,
        urgency=urgency,
        direction=direction,
        confidence=0.6,  # 휴리스틱 기본값 (이후 모델/엔진이 조정)
        headline=headline,
        summary=summary,
        published_at=created_at,
        impact_scope=impact_scope,
        time_horizon=time_horizon,
        market_sentiment_latent=market_sentiment_latent,
        valence=emotion.valence,
        arousal=emotion.arousal,
        uncertainty=emotion.uncertainty,
        emotion_weight_source=emotion.source_mode,
        sasang_emotion_axes={
            "ae": emotion.ae,
            "no": emotion.no,
            "hui": emotion.hui,
            "rak": emotion.rak,
        },
        actor_intent_latent=actor_intent_latent,
        risk_tags=[],
        strategy_hint=None,
        raw_url=raw_url,
        raw_ref_id=raw_ref_id,
    )


def store_strategic_news_event(
    event: StrategicNewsEvent,
    *,
    collection: str = "strategic_news_events",
    category: str = "news",
) -> str:
    """
    StrategicNewsEvent를 파일 기반 메모리에 저장하는 헬퍼.

    content: 인간이 읽기 좋은 요약 텍스트
    metadata: 원본 JSON 전체 및 검색용 필드 포함
    """
    # 워크스페이스 루트 기준 메모리 경로
    workspace_root = Path(__file__).resolve().parents[4]
    memory_root = workspace_root / "memory"
    fbm = FileBasedMemory(memory_root=memory_root)

    # 검색·리포트용으로 유용한 자연어 content 구성
    content = (
        f"[{event.source}] {event.symbol} {event.event_type} "
        f"(urgency={event.urgency}, direction={event.direction})\n"
        f"{event.headline}\n\n{event.summary}"
    )

    metadata = {
        "event_id": event.event_id,
        "source": event.source,
        "symbol": event.symbol,
        "event_type": event.event_type,
        "urgency": event.urgency,
        "direction": event.direction,
        "confidence": event.confidence,
        "impact_scope": event.impact_scope,
        "time_horizon": event.time_horizon,
        "valence": event.valence,
        "arousal": event.arousal,
        "uncertainty": event.uncertainty,
        "emotion_weight_source": event.emotion_weight_source,
        "sasang_emotion_axes": event.sasang_emotion_axes,
        "risk_tags": event.risk_tags,
        "strategy_hint": event.strategy_hint,
        "published_at": event.published_at.isoformat(),
        "raw_url": str(event.raw_url) if event.raw_url else None,
        "raw_ref_id": event.raw_ref_id,
        # Pydantic v2: mode='json'으로 직렬화 가능한 형태로 변환
        "raw_event": event.model_dump(mode="json"),
    }

    memory_id = fbm.store_memory(
        content=content,
        vector_4d=None,  # 자동 라벨링 엔진에 위임
        collection=collection,
        category=category,
        tags=["strategic_news", event.symbol, event.event_type.lower()],
        metadata=metadata,
    )

    return memory_id

