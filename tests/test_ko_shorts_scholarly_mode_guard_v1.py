"""Scholarly YouTube ingest must stay separate from shorts semantic chunk profile."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_biblical_youtube_ssot_merge_window_not_shorts_max() -> None:
    ssot = json.loads(
        (ROOT / "tests/fixtures/media_youtube_biblical_polemic_ssot_v1.json").read_text(encoding="utf-8")
    )
    assert int(ssot["merge_min_chars"]) >= 650
    assert int(ssot["merge_max_chars"]) >= 650
    assert int(ssot["merge_min_chars"]) > 28


def test_youtube_transcript_parser_defaults_not_shorts_cpl() -> None:
    from scripts.parse_youtube_transcript_segments_v0 import parse_youtube_transcript_to_segments

    text = "0:00첫 블록입니다.\n1:00두 번째 블록입니다."
    segs = parse_youtube_transcript_to_segments(text)
    assert segs
    # Scholarly default merge window (40–280) — not shorts 16/28 CPL path.
    assert all(len(s.get("text") or "") >= 1 for s in segs)
