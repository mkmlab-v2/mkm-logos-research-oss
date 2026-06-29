"""media_segment_mdl_compress_v0 — scholarly segment compression."""

from __future__ import annotations

from scripts.media_segment_mdl_compress_v0 import compress_media_text_mdl_v0


def test_compress_strips_fillers_and_keeps_anchors() -> None:
    raw = "어... 종교학자들은 조로 아스터교와 바빌론 유수를 비교합니다. 음... 그냥 잡담입니다."
    out = compress_media_text_mdl_v0(raw, anchor_keywords=["종교학", "조로", "바빌론"])
    assert out["raw_chars"] > out["compressed_chars"]
    assert out["char_saving_rate"] > 0.0
    assert "종교학자" in out["compressed_text"]
    assert "잡담" not in out["compressed_text"]


def test_token_jaccard_high_when_anchor_filter() -> None:
    raw = "페르시아에서 조로 아스터교가 퍼졌습니다. 페르시아에서 조로 아스터교가 퍼졌습니다."
    out = compress_media_text_mdl_v0(raw, anchor_keywords=["조로", "페르시아"])
    assert out["token_jaccard"] >= 0.5
