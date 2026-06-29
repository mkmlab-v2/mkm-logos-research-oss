#!/usr/bin/env python3
"""Parse messy YouTube auto-caption transcript blocks into timed segments [HYPO]."""

from __future__ import annotations

import re
from typing import Any

from scripts.media_stt_transcription_lib_v1 import format_timestamp

# Korean 분/초 first so "2:512분 51초" is not captured as bare "2:512".
_TIME_HEAD = re.compile(
    r"(?P<head>"
    r"\d{1,2}:\d{2,4}분\s*\d{1,2}\s*초"
    r"|\d{1,2}:\d{2}\d{2}초"
    r"|\d{1,2}:\d{2}"
    r")",
)


def _parse_time_head(token: str) -> float | None:
    raw = token.strip()
    if not raw:
        return None

    m_ko = re.match(r"^(\d{1,2}):(\d{2,4})분\s*(\d{1,2})\s*초$", raw)
    if m_ko:
        head_min, _middle, tail_sec = m_ko.groups()
        return float(int(head_min) * 60 + int(tail_sec))

    m_dup = re.match(r"^(\d{1,2}):(\d{2})\2초$", raw)
    if m_dup:
        minutes, seconds = m_dup.groups()
        return float(int(minutes) * 60 + int(seconds))

    m_plain = re.match(r"^(\d{1,2}):(\d{2})$", raw)
    if m_plain:
        minutes, seconds = m_plain.groups()
        return float(int(minutes) * 60 + int(seconds))

    return None


def split_youtube_transcript_blocks(text: str) -> list[tuple[float, str]]:
    """Return (start_sec, body_text) sorted by time."""
    blob = text.replace("\r\n", "\n").strip()
    if not blob:
        return []

    parts = _TIME_HEAD.split(blob)
    if len(parts) < 3:
        return []

    out: list[tuple[float, str]] = []
    i = 1
    while i + 1 < len(parts):
        head = parts[i]
        body = parts[i + 1]
        start = _parse_time_head(head)
        if start is not None:
            cleaned = re.sub(r"\s+", " ", body).strip()
            if cleaned:
                out.append((start, cleaned))
        i += 2

    out.sort(key=lambda x: x[0])
    deduped: list[tuple[float, str]] = []
    for start, body in out:
        if deduped and abs(deduped[-1][0] - start) < 0.5:
            deduped[-1] = (start, f"{deduped[-1][1]} {body}".strip())
        else:
            deduped.append((start, body))
    return deduped


def merge_youtube_blocks_to_segments(
    blocks: list[tuple[float, str]],
    *,
    min_chars: int = 40,
    max_chars: int = 280,
    default_tail_sec: float = 18.0,
) -> list[dict[str, Any]]:
    if not blocks:
        return []

    merged: list[tuple[float, str]] = []
    buf_start: float | None = None
    buf_text: list[str] = []

    def _flush(end_hint: float | None = None) -> None:
        nonlocal buf_start, buf_text
        if buf_start is None or not buf_text:
            buf_start = None
            buf_text = []
            return
        merged.append((buf_start, " ".join(buf_text).strip()))
        buf_start = None
        buf_text = []

    for start, body in blocks:
        if buf_start is None:
            buf_start = start
            buf_text = [body]
            continue
        candidate = " ".join(buf_text + [body]).strip()
        if len(candidate) <= max_chars:
            buf_text.append(body)
            if len(candidate) >= min_chars:
                _flush()
        else:
            _flush()
            buf_start = start
            buf_text = [body]
    _flush()

    segments: list[dict[str, Any]] = []
    for idx, (start, body) in enumerate(merged):
        if idx + 1 < len(merged):
            end_sec = merged[idx + 1][0]
        else:
            end_sec = start + max(default_tail_sec, min(45.0, len(body) / 8.0))
        if end_sec <= start:
            end_sec = start + 8.0
        segments.append(
            {
                "id": f"seg_{len(segments) + 1:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end_sec),
                "duration_sec": round(end_sec - start, 3),
                "text": body,
            }
        )
    return segments


def parse_youtube_transcript_to_segments(
    text: str,
    *,
    min_chars: int = 40,
    max_chars: int = 280,
) -> list[dict[str, Any]]:
    blocks = split_youtube_transcript_blocks(text)
    return merge_youtube_blocks_to_segments(blocks, min_chars=min_chars, max_chars=max_chars)
