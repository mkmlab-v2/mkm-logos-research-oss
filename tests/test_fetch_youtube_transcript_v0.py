"""fetch_youtube_transcript_v0 — id parse + snippet formatting."""

from __future__ import annotations

from scripts.fetch_youtube_transcript_v0 import (
    extract_youtube_video_id,
    fetch_youtube_transcript_v0,
    format_transcript_snippets,
)


def test_extract_video_id_from_url_and_raw() -> None:
    assert extract_youtube_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert (
        extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == "dQw4w9WgXcQ"
    )
    assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("not-a-url") is None


def test_format_transcript_snippets_mm_ss() -> None:
    text = format_transcript_snippets(
        [
            {"start": 0.0, "text": "hello"},
            {"start": 65.0, "text": "world"},
        ]
    )
    assert text.startswith("0:00hello")
    assert "1:05world" in text


def test_fetch_dry_run_no_network() -> None:
    out = fetch_youtube_transcript_v0(
        "https://youtu.be/dQw4w9WgXcQ",
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["video_id"] == "dQw4w9WgXcQ"
    assert out.get("dry_run") is True
