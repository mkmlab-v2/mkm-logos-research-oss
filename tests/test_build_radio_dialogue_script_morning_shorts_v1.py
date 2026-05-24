"""O-P31c morning Shorts dialogue builder."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_radio_dialogue_script_morning_shorts_v1 as builder
import scripts.check_radio_dialogue_script_v1 as gate


def _fixture_bundle(tmp_path: Path) -> tuple[Path, Path, Path]:
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
        "myeongni_lines": ["▸ 오늘 한 줄: 월운 상관 — 페이싱 우선"],
    }
    lp = tmp_path / "logos.json"
    bp = tmp_path / "briefing.json"
    fp = tmp_path / "fortune.json"
    lp.write_text(json.dumps(logos), encoding="utf-8")
    bp.write_text(json.dumps(briefing), encoding="utf-8")
    fp.write_text(json.dumps(fortune), encoding="utf-8")
    return lp, bp, fp


def test_build_morning_shorts_schema_and_gate(tmp_path: Path) -> None:
    lp, bp, fp = _fixture_bundle(tmp_path)
    doc = builder.build_morning_shorts_doc(
        tmp_path,
        logos_path=lp,
        briefing_path=bp,
        fortune_path=fp,
    )
    assert doc["schema"] == "radio_dialogue_script_v1"
    assert doc["program_style"] == "morning_shorts_60s"
    assert doc["gates"]["spoken_price_allowed"] is False
    texts = " ".join(
        d["audio_text"]
        for s in doc["segments"]
        for d in s["dialogue"]
    )
    assert "57.3" not in texts
    assert "77515" not in texts
    report = gate.check_radio_dialogue_script(doc)
    assert report["gate_ok"] is True


def test_gate_fails_on_price_injection(tmp_path: Path) -> None:
    lp, bp, fp = _fixture_bundle(tmp_path)
    doc = builder.build_morning_shorts_doc(tmp_path, logos_path=lp, briefing_path=bp, fortune_path=fp)
    doc["segments"][0]["dialogue"][0]["audio_text"] = "비트코인 90000달러 매수하세요"
    report = gate.check_radio_dialogue_script(doc)
    assert report["gate_ok"] is False
