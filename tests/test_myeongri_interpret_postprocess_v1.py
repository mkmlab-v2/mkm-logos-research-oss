# Purpose: postprocess_v1 homoglyph sha256 + chat leak strip for interpret envelope.

from __future__ import annotations

import json

from scripts.myeongri_interpret_envelope_views_v1 import (
    extract_insight_from_raw_leak_truncated,
    normalize_hex_ascii,
    normalize_json_punctuation_for_parse,
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


def test_normalize_json_punctuation_curly_quotes() -> None:
    assert normalize_json_punctuation_for_parse("\u201chuman_review_required\u201d") == '"human_review_required"'


def test_augment_parsed_recovers_insight_after_json_key() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import augment_parsed_with_recovered_insight

    raw = (
        '{"schema":"myeongri_ai_interpretation_envelope_v1","mkm_advanced_insight":'
        '"[HYPO] narrative body. LEAK rest"}'
    ).replace("LEAK", "若要提供")
    out = augment_parsed_with_recovered_insight(None, raw)
    assert out is not None
    ins = str(out.get("mkm_advanced_insight") or "")
    assert ins.startswith("[HYPO]")
    assert "若要提供" not in ins
    assert "narrative body" in ins


def test_try_parse_envelope_curly_quote_row42_pattern() -> None:
    raw = (
        '{\n  "schema": "myeongri_ai_interpretation_envelope_v1",\n'
        '  "mkm_advanced_insight": "[HYPO] 1994년 9월 16일 해석.",\n'
        '  "confidence_score": 0.95,\n'
        '  \u201chuman_review_required\u201d: true\n}'
    )
    parsed, note, coerced = _try_parse_envelope(raw, postprocess_v1=True)
    assert parsed is not None
    assert parsed["mkm_advanced_insight"].startswith("[HYPO]")
    assert parsed.get("human_review_required") is True or coerced


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


def test_merge_llm_envelope_nested_interpretation() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import merge_llm_envelope_with_template_v1

    compact = {
        "full_saju": {"saju": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}, "ilgan": "丙"},
        "resolution": {"birth_instant_utc": "1992-03-12T17:00:00Z", "iana_tz": "Asia/Seoul"},
    }
    sha = "abc123" * 10 + "abcd"
    parsed = {
        "$schema": "myeongri_ai_interpretation_envelope_v1",
        "interpretation": {"summary": "Engine pillars suggest balanced wood-metal tension in B-track reading."},
    }
    env, note, used = merge_llm_envelope_with_template_v1(
        parsed, compact=compact, lang="ko", deterministic_input_sha256=sha
    )
    assert note == ""
    assert used is True
    assert env["hypothesis_tier"] == "B"
    assert env["mkm_advanced_insight"].startswith("[HYPO]")
    assert env["deterministic_input_sha256"] == sha


def test_insight_variants_differ_by_sample_id() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import (
        build_mkm_insight_ko_v1,
        insight_variant_index,
        template_envelope_from_compact,
    )

    compact = {
        "full_saju": {"saju": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}, "ilgan": "丙"},
        "resolution": {
            "birth_instant_utc": "1992-03-12T17:00:00Z",
            "iana_tz": "Asia/Seoul",
            "local_iso": "1992-03-13T02:00:00+09:00",
        },
    }
    a = template_envelope_from_compact(compact, sample_id="mdl-gs-v1-5001")
    b = template_envelope_from_compact(compact, sample_id="mdl-gs-v1-5099")
    assert a["mkm_advanced_insight"] != b["mkm_advanced_insight"]
    variants = {
        template_envelope_from_compact(compact, sample_id=f"id-{i}")["mkm_advanced_insight"]
        for i in range(24)
    }
    assert len(variants) >= 3
    v0 = build_mkm_insight_ko_v1(y="甲", mo="乙", d="丙", h="丁", ilgan="丙", utc="u", tz="t", variant=0)
    v1 = build_mkm_insight_ko_v1(y="甲", mo="乙", d="丙", h="丁", ilgan="丙", utc="u", tz="t", variant=1)
    assert v0 != v1


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
    p0, n0, _ = _try_parse_envelope(raw, gold_out=gold, postprocess_v1=False)
    p1, n1, _ = _try_parse_envelope(raw, gold_out=gold, postprocess_v1=True)
    assert p0 is not None and n0 == ""
    assert p1 is not None and n1 == ""
    assert p0["deterministic_input_sha256"] != gold_sha
    assert p1["deterministic_input_sha256"] == gold_sha


def test_validate_envelope_missing_governance() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import validate_envelope_required_fields

    assert validate_envelope_required_fields({"schema": "myeongri_ai_interpretation_envelope_v1"}) == "missing_hypothesis_tier"


def test_try_parse_envelope_lora_payload_echo_without_compact() -> None:
    """LoRA post-train pattern: flat schema + nested engine payload, no governance keys."""
    raw = json.dumps(
        {
            "schema": "myeongri_ai_interpretation_envelope_v1",
            "version": "1.0.0",
            "payload": {
                "schema": "saju_global_birth_result_v1",
                "version": "1.0.0",
                "resolution": {
                    "birth_instant_utc": "1971-05-20T08:13:00Z",
                    "iana_tz": "Asia/Seoul",
                },
                "full_saju": {
                    "saju": {"year": "辛亥", "month": "癸巳", "day": "乙巳", "hour": "乙酉"},
                    "ilgan": "乙",
                },
            },
        },
        ensure_ascii=False,
    )
    parsed, note, coerced = _try_parse_envelope(raw)
    assert parsed is not None
    assert note == ""
    assert coerced is True
    assert parsed["hypothesis_tier"] == "B"
    assert parsed["boundary_ack"] is True
    assert parsed["mkm_advanced_insight"].startswith("[HYPO]")
