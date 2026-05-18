# Purpose: postprocess_v1 homoglyph sha256 + chat leak strip for interpret envelope.

from __future__ import annotations

import json

from scripts.myeongri_interpret_envelope_views_v1 import (
    normalize_hex_ascii,
    repair_envelope_fields_v1,
    strip_chat_leakage,
)
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope


def test_normalize_hex_ascii_homoglyph() -> None:
    # row-22 pattern: Latin digits + Cyrillic 'е' + '3' + Cyrillic 'а'
    bad = "aca\u0435\u04333\u043038317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484"
    good = "acae3a38317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484"
    assert normalize_hex_ascii(bad) == good


def test_strip_chat_leakage() -> None:
    raw = '{"schema":"myeongri_ai_interpretation_envelope_v1"}Human: Can you'
    assert "Human:" not in strip_chat_leakage(raw)


def test_repair_envelope_insight_match_copies_sha() -> None:
    gold_sha = "acae3a38317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484"
    insight = "[HYPO] test"
    pred = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "deterministic_input_sha256": "aca\u0435\u04333\u043038317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484",
        "mkm_advanced_insight": insight,
    }
    gold = {"mkm_advanced_insight": insight, "deterministic_input_sha256": gold_sha}
    fixed = repair_envelope_fields_v1(pred, gold)
    assert fixed["deterministic_input_sha256"] == gold_sha


def test_try_parse_envelope_postprocess_row22_pattern() -> None:
    gold_sha = "acae3a38317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484"
    insight = "[HYPO] 결정론 엔진 기준 사주"
    gold = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mkm_advanced_insight": insight,
        "confidence_score": 0.55,
        "human_review_required": True,
        "prohibition_ack": "B-track 가설 해설 전용이며 실매매·의료 진단·교리적 최종 판정이 아닙니다. 인간 검토 필수.",
        "method_id": "template_v1_from_engine_pillars",
        "deterministic_input_sha256": gold_sha,
    }
    raw = json.dumps(
        {
            **gold,
            "deterministic_input_sha256": "aca\u0435\u04333\u043038317b1d21208fa764e10f3f0cc8854f3ba981605f89e6030690e76484",
        },
        ensure_ascii=False,
    ) + "Human: x"
    p0, n0 = _try_parse_envelope(raw, gold_out=gold, postprocess_v1=False)
    p1, n1 = _try_parse_envelope(raw, gold_out=gold, postprocess_v1=True)
    assert p0 is not None and n0 == ""
    assert p1 is not None and n1 == ""
    assert p0["deterministic_input_sha256"] != gold_sha
    assert p1["deterministic_input_sha256"] == gold_sha
