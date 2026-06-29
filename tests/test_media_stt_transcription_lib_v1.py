"""media_stt_transcription_lib_v1 — proportional segments + ko semantic chunking."""

from __future__ import annotations

from scripts.media_stt_transcription_lib_v1 import (
    refine_stt_segments_semantic_ko_v1,
    semantic_chunk_ko_v1,
    split_transcript_proportional_segments,
)


def test_proportional_segments_cover_duration() -> None:
    segs = split_transcript_proportional_segments(
        "첫 문장입니다. 두 번째 회고 문화 문장입니다. 마무리.",
        90.0,
        min_seg_sec=3.0,
    )
    assert len(segs) == 3
    assert segs[0]["start"] == "00:00:00.00"
    assert segs[-1]["end"] == "00:01:30.00"
    assert "회고" in segs[1]["text"]


def test_semantic_chunk_merges_orphan_prefix() -> None:
    chunks = semantic_chunk_ko_v1("첫째, 잘한 것. 둘째, 개선할 점.")
    assert chunks == ["첫째, 잘한 것.", "둘째, 개선할 점."]
    assert not any(c.strip().endswith(",") and c.count(" ") == 0 for c in chunks)


def test_semantic_chunk_merges_orphan_ending() -> None:
    raw = ["오늘 회고 문화를", "짚어", "줍니다."]
    merged = semantic_chunk_ko_v1(" ".join(raw))
    assert merged == ["오늘 회고 문화를 짚어 줍니다."]
    assert not any(c in {"줍니다.", "짚어"} for c in merged)


def test_semantic_chunk_splits_long_sentence_under_max_chars() -> None:
    text = "그런데 더 놀라운 사실은 하나하나 보여 드리도록 하겠습니다."
    chunks = semantic_chunk_ko_v1(text, max_chars=28)
    assert len(chunks) >= 2
    assert all(len(c) <= 28 for c in chunks)
    assert "하겠습니다." in chunks[-1]
    chunks = semantic_chunk_ko_v1("회고 문화입니다.", max_chars=28)
    assert chunks == ["회고 문화입니다."]


def test_semantic_chunk_splits_long_by_eojeol() -> None:
    text = (
        "첫째 매일 짧은 회고를 팀과 나누는 습관을 만들었고 "
        "둘째 팩트 기반 장부를 함께 점검합니다."
    )
    chunks = semantic_chunk_ko_v1(text, max_chars=18)
    assert len(chunks) >= 2
    joined = " ".join(chunks)
    assert "회고" in joined
    assert "장부" in joined
    assert all(" " not in c or len(c) <= 22 for c in chunks)


def test_refine_stt_segments_preserves_span() -> None:
    segs = refine_stt_segments_semantic_ko_v1(
        [
            {
                "id": "seg_01",
                "start": "00:00:01.00",
                "end": "00:00:04.00",
                "duration_sec": 3.0,
                "text": "첫째,",
            },
            {
                "id": "seg_02",
                "start": "00:00:04.00",
                "end": "00:00:08.00",
                "duration_sec": 4.0,
                "text": "잘한 것.",
            },
            {
                "id": "seg_03",
                "start": "00:00:08.00",
                "end": "00:00:12.00",
                "duration_sec": 4.0,
                "text": "짚어",
            },
            {
                "id": "seg_04",
                "start": "00:00:12.00",
                "end": "00:00:15.00",
                "duration_sec": 3.0,
                "text": "줍니다.",
            },
        ]
    )
    assert len(segs) >= 1
    assert segs[0]["start"] == "00:00:01.00"
    assert segs[-1]["end"] == "00:00:15.00"
    texts = [s["text"] for s in segs]
    assert any("첫째, 잘한 것." in t for t in texts)
    assert not any(t.strip() == "줍니다." for t in texts)
