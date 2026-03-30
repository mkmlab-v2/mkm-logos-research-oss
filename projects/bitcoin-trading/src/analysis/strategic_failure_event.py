#!/usr/bin/env python3
"""
전략/트레이딩/코딩 전반에서 발생한 "실패 사례"를
구조화하여 저장하기 위한 FailureEvent 스키마 및 저장 헬퍼.

Phase 5.3에서 지휘관님의 오답 노트(Failure Buffer) 역할을 하는
최소 단위 구현으로, 이후 14B/제5회로 재학습 및 규칙 보정에
사용될 수 있다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional
import sys

from pydantic import BaseModel, Field

# tools 패키지 임포트를 위해 워크스페이스 루트(C:/workspace)를 sys.path에 추가
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from tools.tools.core.file_based_memory import FileBasedMemory


FailureSource = Literal["TRADING", "NEWS_EXTRACTOR", "CODING", "SYSTEM", "OTHER"]

FailureOutcome = Literal["LOSS", "BUG", "BAD_PERFORMANCE", "RISK_EVENT", "OTHER"]


class FailureEvent(BaseModel):
    """
    P1 Failure Buffer용 표준 스키마.

    - 한 번 크게 실패한 매매/전략/코드 사례를 구조화해서 저장해 두고,
      이후 제5회로/14B가 재학습하거나 규칙을 보정할 때 참고한다.
    """

    failure_id: str = Field(
        ...,
        description="내부용 유니크 ID (예: hash 또는 file_based_memory의 key)",
    )
    source: FailureSource = Field(
        ...,
        description="실패가 발생한 소스 (TRADING, NEWS_EXTRACTOR, CODING, SYSTEM, OTHER)",
    )
    when: datetime = Field(
        ...,
        description="실패가 발생한 시각 (UTC)",
    )
    input_snapshot: str = Field(
        ...,
        description="실패 당시의 핵심 입력 요약 (뉴스/시그널/코드 등)",
    )
    engine_decision: Optional[str] = Field(
        None,
        description="당시 엔진/전략이 내린 주요 판단 또는 시그널",
    )
    outcome: FailureOutcome = Field(
        ...,
        description="실패 결과 유형 (LOSS, BUG, BAD_PERFORMANCE, RISK_EVENT, OTHER)",
    )
    severity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="실패의 심각도 (0.0~1.0, 1.0에 가까울수록 치명적)",
    )
    realized_pnl: Optional[float] = Field(
        None,
        description="트레이딩 실패의 경우 실현 손익 (USD 기준, 음수=손실)",
    )
    human_feedback: Optional[str] = Field(
        None,
        description="지휘관님의 사후 피드백/복기 내용 (무엇이 잘못되었는지에 대한 인간 판단)",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="검색/분석용 태그 (예: BTCUSDT, BREAKOUT, FOMO_ENTRY 등)",
    )


def store_failure_event(
    event: FailureEvent,
    *,
    collection: str = "failure_events",
    category: str = "failure",
) -> str:
    """
    FailureEvent를 파일 기반 메모리에 저장하는 헬퍼.

    - content: 사람이 읽기 좋은 한두 줄 요약
    - metadata: 원본 JSON 전체 및 검색용 필드 포함
    """

    # 워크스페이스 루트 기준 메모리 경로 사용 (기본값은 C:/workspace/memory/)
    workspace_root = Path(__file__).resolve().parents[3]
    memory_root = workspace_root / "memory"
    fbm = FileBasedMemory(memory_root=memory_root)

    # 검색·리포트용 자연어 content 구성
    when_iso = event.when.astimezone(timezone.utc).isoformat()
    content = (
        f"[{event.source}] {event.outcome} (severity={event.severity}) @ {when_iso}\n"
        f"{event.input_snapshot}\n\n"
        f"decision={event.engine_decision}, human_feedback={event.human_feedback}"
    )

    metadata = {
        "failure_id": event.failure_id,
        "source": event.source,
        "when": when_iso,
        "outcome": event.outcome,
        "severity": event.severity,
        "realized_pnl": event.realized_pnl,
        "tags": event.tags,
        # Pydantic v2: mode='json'으로 직렬화 가능한 형태로 변환
        "raw_event": event.model_dump(mode="json"),
    }

    memory_id = fbm.store_memory(
        content=content,
        vector_4d=None,  # 자동 라벨링 엔진에 위임
        collection=collection,
        category=category,
        tags=["failure_event", event.source.lower(), event.outcome.lower()],
        metadata=metadata,
    )

    return memory_id


def record_trading_failure_event(
    *,
    symbol: str,
    reason: str,
    realized_pnl: float,
    severity: float = 0.7,
    tags: Optional[List[str]] = None,
) -> str:
    """
    트레이딩 실패 사례를 간단히 기록하기 위한 편의 함수.

    - symbol: "BTCUSDT" 등 주요 종목
    - reason: 실패 원인에 대한 짧은 자연어 설명
    - realized_pnl: 손익 (USD 기준, 음수=손실)
    - severity: 0.0~1.0 범위의 심각도 (기본 0.7)
    """
    event = FailureEvent(
        failure_id=f"failure-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        source="TRADING",
        when=datetime.now(timezone.utc),
        input_snapshot=f"{symbol} 포지션 실패: {reason}",
        engine_decision=None,
        outcome="LOSS" if realized_pnl < 0 else "OTHER",
        severity=max(0.0, min(1.0, severity)),
        realized_pnl=realized_pnl,
        human_feedback=None,
        tags=[symbol] + (tags or []),
    )
    return store_failure_event(event)

