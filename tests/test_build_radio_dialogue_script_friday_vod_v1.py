"""Friday VOD dialogue builder."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_radio_dialogue_script_friday_vod_v1 as fri
import scripts.check_radio_dialogue_script_v1 as gate


def test_friday_vod_build_and_gate(tmp_path: Path) -> None:
    story = {
        "schema": "listener_story_v1",
        "title_ko": "테스트 사연",
        "body_ko": "번아웃과 조급함이 겹칩니다. 리듬 조언만 원합니다.",
    }
    logos = {
        "schema": "commander_daily_logos_anchor_v1",
        "calendar_kst": "2026-05-22",
        "golden_anchor": {"ref": "잠언 3:5", "text": "신뢰하라", "theme": "잠언 길"},
    }
    briefing = {
        "schema": "commander_telegram_advanced_briefing_v1",
        "calendar_kst": "2026-05-22",
        "world_pulse": {
            "kospi": {"today_action": "WATCH"},
            "macro": {"risk_warning_level": "elevated", "operator_posture": "watch_tighten"},
        },
        "hypothesis_stream": {
            "synthesis_ko": "페이싱 우선",
            "branches": [{"predicted_bias_ko": "회복·수면 우선"}],
        },
        "user_condition": {"stress_band": "high"},
    }
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "myeongni_lines": ["▸ 오늘 한 줄: 페이싱 우선"],
    }
    sp = tmp_path / "story.json"
    lp = tmp_path / "logos.json"
    bp = tmp_path / "briefing.json"
    fp = tmp_path / "fortune.json"
    for p, doc in [(sp, story), (lp, logos), (bp, briefing), (fp, fortune)]:
        p.write_text(json.dumps(doc), encoding="utf-8")

    doc = fri.build_friday_vod_doc(
        tmp_path,
        logos_path=lp,
        briefing_path=bp,
        fortune_path=fp,
        story_path=sp,
    )
    assert doc["program_style"] == "friday_vod_20m"
    assert doc["upstream_inputs"]["listener_story"]
    report = gate.check_radio_dialogue_script(doc)
    assert report["gate_ok"] is True


def test_friday_vod_with_narrative_fuel(tmp_path: Path) -> None:
    fuel_src = Path(__file__).resolve().parents[1] / "data" / "radio" / "narrative_fuel_science_v1.example.json"
    story = {
        "schema": "listener_story_v1",
        "title_ko": "테스트",
        "body_ko": "리듬만 원합니다.",
    }
    logos = {
        "schema": "commander_daily_logos_anchor_v1",
        "calendar_kst": "2026-05-22",
        "golden_anchor": {"ref": "잠언 3:5", "text": "신뢰", "theme": "잠언"},
    }
    briefing = {
        "schema": "commander_telegram_advanced_briefing_v1",
        "calendar_kst": "2026-05-22",
        "world_pulse": {
            "kospi": {"today_action": "WATCH"},
            "macro": {"risk_warning_level": "elevated", "operator_posture": "watch"},
        },
        "hypothesis_stream": {"synthesis_ko": "페이싱", "branches": []},
        "user_condition": {"stress_band": "mid"},
    }
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "myeongni_lines": ["▸ 페이싱"],
    }
    sp = tmp_path / "story.json"
    sp.write_text(json.dumps(story), encoding="utf-8")
    lp = tmp_path / "logos.json"
    lp.write_text(json.dumps(logos), encoding="utf-8")
    bp = tmp_path / "briefing.json"
    bp.write_text(json.dumps(briefing), encoding="utf-8")
    fp = tmp_path / "fortune.json"
    fp.write_text(json.dumps(fortune), encoding="utf-8")

    doc = fri.build_friday_vod_doc(
        tmp_path,
        logos_path=lp,
        briefing_path=bp,
        fortune_path=fp,
        story_path=sp,
        narrative_fuel_path=fuel_src,
    )
    names = [s.get("segment_name") for s in doc["segments"]]
    assert "science_narrative_fuel_pack" in names
    assert doc["upstream_inputs"].get("narrative_fuel")
    report = gate.check_radio_dialogue_script(doc)
    assert report["gate_ok"] is True
    assert report["n_dialogue_lines"] >= 9
