# Purpose: B-track interpret v4 wording sweep (calibration30 needs_edit).

from __future__ import annotations

from scripts.myeongri_interpret_envelope_views_v1 import (
    _hour_pillar_cited,
    soften_interpret_overconfidence_v1,
    sweep_interpret_insight_wording_v1,
)

COMPACT_SAMPLE = {
    "full_saju": {
        "saju": {"year": "신미", "month": "계사", "day": "계묘", "hour": "기미"},
        "ilgan": "계",
    },
    "resolution": {
        "birth_instant_utc": "1991-06-02T06:45:00Z",
        "iana_tz": "Asia/Seoul",
    },
}


def test_soften_overconfidence_phrases() -> None:
    raw = "[HYPO] 모든 정보가 일치하는 정확한 해석입니다. 확실합니다."
    out, notes = soften_interpret_overconfidence_v1(raw)
    assert "정확한 해석" not in out
    assert "확실" not in out
    assert notes


def test_sweep_rebuilds_missing_hour_from_compact() -> None:
    insight = "[HYPO] 년 신미, 월 계사, 일 계묘만 서술."
    out, notes = sweep_interpret_insight_wording_v1(
        insight,
        gold_insight_head="년 신미, 월 계사, 일 계묘, 시 기미",
        compact=COMPACT_SAMPLE,
        row_index=96,
        reviewer_comment="시주(기미) 누락 — 3주만 서술.",
    )
    assert "rebuilt_from_engine_compact" in notes or "appended_hour_pillar" in notes
    assert "기미" in out or _hour_pillar_cited(out)


def test_sweep_soft_only_when_comment_says_wording_only() -> None:
    insight = "[HYPO] 신미·계사·계묘·기미 정합. 정확한 해석입니다."
    out, notes = sweep_interpret_insight_wording_v1(
        insight,
        gold_insight_head="4주 신미·계사·계묘·기미",
        compact=COMPACT_SAMPLE,
        row_index=96,
        reviewer_comment="'정확한 해석' 과확신 — wording만 완화 필요.",
    )
    assert "rebuilt_from_engine_compact" not in notes
    assert "정확한 해석" not in out
    assert "softened:" in str(notes)
