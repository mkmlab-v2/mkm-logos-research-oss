"""Commander user_condition + advisory tilt P31c."""

from __future__ import annotations

import scripts.build_commander_user_condition_v1 as uc


def test_build_user_condition_schema() -> None:
    profile = {
        "sasang_reference": {"label": "태양인"},
        "cognition_hypothesis": {"patterns": ["test"]},
    }
    report = {"structure_analysis": {"element_profile": {"dominant_element_visible": "토"}}}
    lifestyle = {"sasang_label": "태양인", "weakest_element": "화", "weather_band": "mild", "meals": {}}
    world = {"macro": {"risk_warning_level": "elevated"}, "kospi": {"today_action": "WATCH"}}
    hypo = {"market_tone": "caution", "myeongni_tags": {"month_ten_god": "상관"}, "branches": []}
    doc = uc.build_user_condition(
        profile=profile,
        report=report,
        lifestyle=lifestyle,
        world_pulse=world,
        hypothesis_stream=hypo,
        calendar_kst="2026-05-22",
    )
    assert doc["schema"] == "commander_user_condition_v1"
    tilt = doc["advisory_investment_bias_tilt"]
    assert tilt["research_only"] is True
    assert tilt["track_a_auto_order_forbidden"] is True
    assert "live_order" in tilt["forbidden"]


def test_sync_context_schema() -> None:
    import scripts.sync_mkm_one_question_context_v1 as sync

    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "city_default": "Seoul",
        "myeongni_lines": ["▸ 오늘 한 줄: 테스트"],
        "world_pulse_fusion": {"fusion_one_liner_ko": "융합"},
        "hypothesis_stream": {"synthesis_ko": "초론", "branches": [], "market_tone": "caution"},
        "user_condition": {
            "energy_band": "good",
            "advisory_investment_bias_tilt": {"tilt_ko": "관측", "tilt_label": "observe"},
        },
    }
    ctx = sync.build_context(fortune)
    assert ctx["schema"] == "commander_one_question_context_v1"
    assert ctx["preview_only"] is True
