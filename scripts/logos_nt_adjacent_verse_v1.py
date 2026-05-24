#!/usr/bin/env python3
"""MT verse_id adjacency helpers for NT textual-variant proxy (B-track)."""

from __future__ import annotations

import re
from typing import Any

_VERSE_RE = re.compile(r"^(.+?)\.(\d+)\.(\d+)$")


def parse_mt_verse_id(verse_id: str) -> tuple[str, int, int] | None:
    m = _VERSE_RE.match(verse_id.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3))


def format_mt_verse_id(book: str, chapter: int, verse: int) -> str:
    return f"{book}.{chapter}.{verse}"


def adjacent_mt_verse_ids(verse_id: str, *, span: int = 2) -> list[str]:
    """Return verse_id candidates at ±1..±span within the same chapter (deterministic order)."""
    parsed = parse_mt_verse_id(verse_id)
    if not parsed:
        return []
    book, chapter, verse = parsed
    out: list[str] = []
    for dv in range(-span, span + 1):
        if dv == 0:
            continue
        nv = verse + dv
        if nv >= 1:
            out.append(format_mt_verse_id(book, chapter, nv))
    return out


def pick_sblgnt_filled_neighbor(
    verse_id: str,
    corpus_index: dict[str, dict[str, Any]],
    *,
    span: int = 2,
    filled_decode_prefix: str = "bhs_sblgnt",
) -> tuple[str, dict[str, Any]] | None:
    """First adjacent row with lexical decode (not MT-only stub)."""
    for adj in adjacent_mt_verse_ids(verse_id, span=span):
        row = corpus_index.get(adj)
        if not row:
            continue
        status = str(row.get("decode_status") or "")
        if status.startswith("mt_canon_only"):
            continue
        if filled_decode_prefix and not status.startswith(filled_decode_prefix):
            if row.get("upstream_original_text_missing"):
                continue
        return adj, row
    return None
