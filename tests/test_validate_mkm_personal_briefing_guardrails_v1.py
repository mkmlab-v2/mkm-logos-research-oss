"""Contract tests for scripts/validate_mkm_personal_briefing_guardrails_v1.py helpers."""

from __future__ import annotations

import scripts.validate_mkm_personal_briefing_guardrails_v1 as v


def test_ops_stage_detected() -> None:
    text = "당신의 단계는 S1_SHADOW 입니다."
    err, warn = v.evaluate(text, strict_paragraph_bleed=False)
    assert any("operational_stage_token:S1_SHADOW" in e for e in err)
    assert not warn


def test_clean_personal_briefing_passes() -> None:
    text = (
        "일간 경금 국면에서는 보수적 현금흐름 점검이 우선입니다.\n\n"
        "부채 구조는 금리·상환 스케줄과 함께 전문가와 조정하십시오.\n"
    )
    err, warn = v.evaluate(text, strict_paragraph_bleed=False)
    assert err == []
    assert warn == []


def test_market_debt_same_paragraph_warn_by_default() -> None:
    text = (
        "KOSPI 방어 구간과 개인 부채 압박이 겹치므로 레버리지를 줄이십시오.\n"
    )
    err, warn = v.evaluate(text, strict_paragraph_bleed=False)
    assert err == []
    assert warn


def test_market_debt_same_paragraph_error_when_strict() -> None:
    text = "BTC 급락 시 부채 비용이 커질 수 있습니다."
    err, warn = v.evaluate(text, strict_paragraph_bleed=True)
    assert err
    assert not warn
