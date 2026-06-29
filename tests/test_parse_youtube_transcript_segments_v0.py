"""parse_youtube_transcript_segments_v0 — messy caption ingest."""

from __future__ import annotations

from pathlib import Path

from scripts.parse_youtube_transcript_segments_v0 import (
    _parse_time_head,
    parse_youtube_transcript_to_segments,
    split_youtube_transcript_blocks,
)


def test_parse_time_head_variants() -> None:
    assert _parse_time_head("0:00") == 0.0
    assert _parse_time_head("0:1111초") == 11.0
    assert _parse_time_head("2:512분 51초") == 171.0
    assert _parse_time_head("1:041분 4초") == 64.0


def test_split_youtube_blocks_from_sample() -> None:
    sample = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/youtube_transcript_polluted_bench_v0.sample.txt"
    )
    blocks = split_youtube_transcript_blocks(sample.read_text(encoding="utf-8"))
    assert len(blocks) >= 10
    assert blocks[0][0] == 0.0
    assert "종교학자" in blocks[0][1]


def test_parse_to_segments_has_ids_and_timestamps() -> None:
    sample = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/youtube_transcript_polluted_bench_v0.sample.txt"
    )
    segments = parse_youtube_transcript_to_segments(sample.read_text(encoding="utf-8"))
    assert len(segments) >= 6
    assert segments[0]["id"] == "seg_01"
    assert segments[0]["start"].startswith("00:")


def test_multilens_rank_prefers_serpent_lilith() -> None:
    import json
    from pathlib import Path

    from scripts.infer_media_segment_provenance_v0 import enrich_segments_provenance_v0
    from scripts.rank_media_segments_v0 import compute_multilens_rank_v0

    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/media_stt_transcription_polluted_bench_v1.json"
    )
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    segments = enrich_segments_provenance_v0(
        doc["segments"],
        theme_keywords=doc["theme_keywords"],
        negative_keywords=doc.get("negative_keywords"),
    )
    ml = compute_multilens_rank_v0(segments, doc["multilens_keywords"], top_k=2)
    top_ids = {s["id"] for s in ml}
    assert top_ids <= {"seg_05", "seg_06", "seg_07", "seg_08", "seg_09", "seg_10"}
    assert "seg_06" in top_ids or "seg_10" in top_ids
