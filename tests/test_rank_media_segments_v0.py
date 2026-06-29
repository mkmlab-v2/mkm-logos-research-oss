"""rank_media_segments_v0 — v0 scoring rules."""

from __future__ import annotations

from scripts.rank_media_segments_v0 import compute_segment_rank_v0


def test_segment_rank_v0_prefers_theme_keywords() -> None:
    segments = [
        {"id": "a", "text": "어... 회고 문화 시스템", "duration_sec": 12.0, "start": "00:00:00", "end": "00:00:12"},
        {"id": "b", "text": "음 그냥 짧은 구어", "duration_sec": 3.0, "start": "00:00:12", "end": "00:00:15"},
    ]
    ranked = compute_segment_rank_v0(segments, ["회고", "시스템"])
    assert len(ranked) == 2
    assert ranked[0]["id"] == "a"
    assert ranked[0]["v0_score"] > ranked[1]["v0_score"]


def test_short_closing_segment_scores_low() -> None:
    segments = [
        {
            "id": "gold",
            "text": "회고 문화와 시스템 팩트 장부",
            "duration_sec": 15.0,
            "start": "00:01:00",
            "end": "00:01:15",
        },
        {
            "id": "bye",
            "text": "그럼 이만 마칠게요",
            "duration_sec": 5.0,
            "start": "00:02:40",
            "end": "00:02:45",
        },
    ]
    ranked = compute_segment_rank_v0(segments, ["회고", "시스템", "팩트"])
    assert ranked[0]["id"] == "gold"


def test_negative_keywords_demote_polluted_segments() -> None:
    from pathlib import Path
    import json

    from scripts.infer_media_segment_provenance_v0 import enrich_segments_provenance_v0

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
    ranked = compute_segment_rank_v0(
        segments,
        doc["theme_keywords"],
        negative_keywords=doc.get("negative_keywords"),
    )
    # scholarly lane excludes debunked_fake
    from scripts.rank_media_segments_v0 import compute_scholarly_rank_v0

    scholarly = compute_scholarly_rank_v0(
        segments,
        doc["theme_keywords"],
        negative_keywords=doc.get("negative_keywords"),
    )
    top3 = scholarly[:3]
    top3_ids = {s["id"] for s in top3}
    assert top3_ids <= {"seg_02", "seg_03", "seg_04", "seg_11", "seg_17"}
    assert all(s.get("provenance_hint") != "debunked_fake" for s in top3)
    fake_ids = {"seg_14", "seg_15", "seg_16", "seg_18"}
    assert fake_ids.isdisjoint(top3_ids)
    assert all(float(s.get("v0_score") or 0) < 0 for s in ranked if s["id"] in {"seg_15", "seg_18"})
