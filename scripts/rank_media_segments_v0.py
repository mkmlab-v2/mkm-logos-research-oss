#!/usr/bin/env python3
"""B-track [HYPO] — rank timestamped transcript segments for media handoff (v0).

Explicit keyword + filler-ratio + duration penalty. Not CompoundScore; not 41k MDL.
"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_FILLERS: tuple[str, ...] = (
    "어",
    "음",
    "그",
    "저",
    "저기",
    "그러니까",
    "뭐",
    "약간",
)
DEFAULT_THEME_KEYWORDS: tuple[str, ...] = ("회고", "시스템", "팩트", "에이전트", "장부")

_KW_WEIGHT = 3.0
_NEG_KW_WEIGHT = -4.0
_PROVENANCE_DEBUNK_PENALTY = -3.0
_PROVENANCE_MIXED_PENALTY = -1.0
_FILLER_WEIGHT = 2.0
_DURATION_PENALTY = -2.0
_MIN_DURATION_SEC = 8.0
_MAX_DURATION_SEC = 45.0


def _segment_duration_sec(seg: dict[str, Any]) -> float:
    if "duration_sec" in seg and seg["duration_sec"] is not None:
        return float(seg["duration_sec"])
    start = str(seg.get("start") or "")
    end = str(seg.get("end") or "")

    def _to_sec(ts: str) -> float | None:
        m = re.match(r"^(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$", ts.strip())
        if not m:
            return None
        h, mi, s, frac = m.groups()
        base = int(h) * 3600 + int(mi) * 60 + int(s)
        if frac:
            base += int(frac) / (10 ** len(frac))
        return float(base)

    s0, s1 = _to_sec(start), _to_sec(end)
    if s0 is not None and s1 is not None and s1 >= s0:
        return s1 - s0
    return 10.0


def _filler_ratio(text: str, fillers: tuple[str, ...] = DEFAULT_FILLERS) -> float:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return 1.0
    hits = sum(1 for w in words if any(f in w for f in fillers))
    return hits / len(words)


def score_segment_v0(
    seg: dict[str, Any],
    theme_keywords: list[str],
    *,
    negative_keywords: list[str] | None = None,
    fillers: tuple[str, ...] = DEFAULT_FILLERS,
    min_duration: float = _MIN_DURATION_SEC,
    max_duration: float = _MAX_DURATION_SEC,
) -> float:
    text = str(seg.get("text") or "")
    duration = _segment_duration_sec(seg)
    kw_hits = sum(1 for kw in theme_keywords if kw and kw in text)
    neg_hits = sum(1 for kw in (negative_keywords or []) if kw and kw in text)
    filler_ratio = _filler_ratio(text, fillers)
    duration_penalty = 0.0
    if duration < min_duration or duration > max_duration:
        duration_penalty = _DURATION_PENALTY
    provenance_penalty = 0.0
    hint = str(seg.get("provenance_hint") or "")
    if hint == "debunked_fake":
        provenance_penalty = _PROVENANCE_DEBUNK_PENALTY
    elif hint == "mixed":
        provenance_penalty = _PROVENANCE_MIXED_PENALTY
    return (
        (_KW_WEIGHT * kw_hits)
        + (_NEG_KW_WEIGHT * neg_hits)
        + (_FILLER_WEIGHT * (1.0 - filler_ratio))
        + duration_penalty
        + provenance_penalty
    )


def compute_segment_rank_v0(
    segments: list[dict[str, Any]],
    theme_keywords: list[str] | None = None,
    *,
    negative_keywords: list[str] | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    kws = theme_keywords or list(DEFAULT_THEME_KEYWORDS)
    ranked: list[dict[str, Any]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        row = dict(seg)
        row["v0_score"] = round(
            score_segment_v0(row, kws, negative_keywords=negative_keywords),
            3,
        )
        if "duration_sec" not in row:
            row["duration_sec"] = round(_segment_duration_sec(row), 3)
        ranked.append(row)
    ranked.sort(key=lambda x: float(x.get("v0_score") or 0.0), reverse=True)
    if top_k is not None and top_k > 0:
        return ranked[:top_k]
    return ranked


def compute_scholarly_rank_v0(
    segments: list[dict[str, Any]],
    theme_keywords: list[str] | None = None,
    *,
    negative_keywords: list[str] | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    pool = [
        s
        for s in segments
        if isinstance(s, dict) and str(s.get("provenance_hint") or "") != "debunked_fake"
    ]
    return compute_segment_rank_v0(
        pool,
        theme_keywords,
        negative_keywords=negative_keywords,
        top_k=top_k,
    )


def compute_multilens_rank_v0(
    segments: list[dict[str, Any]],
    multilens_keywords: list[str] | None = None,
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    kws = multilens_keywords or []
    pool: list[dict[str, Any]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        hint = str(seg.get("provenance_hint") or "")
        text = str(seg.get("text") or "")
        kw_hit = any(kw and kw in text for kw in kws)
        if hint in {"multilens_hypo", "mixed"} or kw_hit:
            pool.append(seg)
    return compute_segment_rank_v0(pool, kws, negative_keywords=[], top_k=top_k)
