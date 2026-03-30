from __future__ import annotations

from typing import Literal, TypedDict


DomainName = Literal["finance", "health", "life", "study"]


class LogosVector4D(TypedDict):
    s: float
    l: float
    k: float
    m: float


class LogosSignal(TypedDict):
    name: str
    score: float
    rationale: str


class LogosCoreInsight(TypedDict):
    ts_utc: str
    source: str
    summary: str
    vector_4d: LogosVector4D
    confidence: float
    risk_band: Literal["low", "medium", "high"]
    signals: list[LogosSignal]
    high_signal: bool


class DomainInsight(TypedDict):
    ts_utc: str
    domain: DomainName
    summary: str
    actions: list[str]
    constraints: list[str]
    confidence: float
