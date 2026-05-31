# Purpose: template skeleton normalization for interpret narrative diversity audit.

from __future__ import annotations

from scripts.audit_myeongri_interpret_narrative_diversity_v1 import insight_to_template_skeleton


def test_insight_to_template_skeleton_collapses_pillar_variation() -> None:
    a = (
        "[HYPO] 결정론 엔진 기준 사주: 년주 갑술, 월주 계유, 일주 신축, 시주 갑오, 일간 신. "
        "가격·매매·의료 단정이 아닌 B-track 서술 초안. birth_instant_utc=1994-09-12T02:19:00Z, iana_tz=Asia/Seoul."
    )
    b = (
        "[HYPO] 결정론 엔진 기준 사주: 년주 무술, 월주 병진, 일주 신미, 시주 정유, 일간 신. "
        "가격·매매·의료 단정이 아닌 B-track 서술 초안. birth_instant_utc=1958-04-24T09:42:00Z, iana_tz=Asia/Seoul."
    )
    assert insight_to_template_skeleton(a) == insight_to_template_skeleton(b)
