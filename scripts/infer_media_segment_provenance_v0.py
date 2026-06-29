#!/usr/bin/env python3
"""B-track [HYPO] — auto-tag media transcript segments by provenance (v0.2)."""

from __future__ import annotations

from typing import Any

PROVENANCE_VALUES = frozenset(
    {"scholarly_fact", "debunked_fake", "mixed", "multilens_hypo", "unknown"}
)

_DEBUNK_CONTEXT_MARKERS: tuple[str, ...] = (
    "인정받지",
    "상상력",
    "작가일 뿐",
    "학문적 자격",
    "뇌피셜",
    "헛소리",
    "명백히 아니",
    "받아들여지지",
    "가짜",
)

_SCHOLAR_CONTEXT_MARKERS: tuple[str, ...] = (
    "종교학",
    "학자",
    "주류",
    "엄연히 다르",
    "일부 인정",
    "비교종교",
    "연준",
    "그린스폰",
    "생산성",
    "인플레이션",
    "부채 비율",
    "GDP",
)

_MULTILENS_MARKERS: tuple[str, ...] = (
    "뱀",
    "에덴",
    "릴리스",
    "프로메테우스",
    "오피",
    "기노스",
    "루시퍼",
    "다른 의미",
    "일본",
    "디플레이션",
    "다컴버블",
    "칩플레이션",
    "구슬리",
)


def _keyword_hits(text: str, keywords: list[str] | None) -> int:
    return sum(1 for kw in (keywords or []) if kw and kw in text)


def infer_provenance_hint_v0(
    text: str,
    *,
    theme_keywords: list[str] | None = None,
    negative_keywords: list[str] | None = None,
) -> str:
    body = str(text or "").strip()
    if not body:
        return "unknown"

    neg = _keyword_hits(body, negative_keywords)
    pos = _keyword_hits(body, theme_keywords)
    debunk_ctx = any(m in body for m in _DEBUNK_CONTEXT_MARKERS)
    scholar_ctx = any(m in body for m in _SCHOLAR_CONTEXT_MARKERS)
    multilens_ctx = any(m in body for m in _MULTILENS_MARKERS)

    if neg >= 2 or (neg >= 1 and debunk_ctx):
        return "debunked_fake"
    if neg >= 1 and pos >= 1:
        return "mixed"
    if neg >= 1:
        return "debunked_fake"
    if multilens_ctx and not scholar_ctx:
        return "multilens_hypo"
    if pos >= 1 or scholar_ctx:
        return "scholarly_fact"
    if multilens_ctx:
        return "multilens_hypo"
    return "unknown"


def enrich_segments_provenance_v0(
    segments: list[dict[str, Any]],
    *,
    theme_keywords: list[str] | None = None,
    negative_keywords: list[str] | None = None,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        row = dict(seg)
        existing = str(row.get("provenance_hint") or "").strip()
        if existing and not overwrite and existing in PROVENANCE_VALUES:
            out.append(row)
            continue
        row["provenance_hint"] = infer_provenance_hint_v0(
            str(row.get("text") or ""),
            theme_keywords=theme_keywords,
            negative_keywords=negative_keywords,
        )
        out.append(row)
    return out
