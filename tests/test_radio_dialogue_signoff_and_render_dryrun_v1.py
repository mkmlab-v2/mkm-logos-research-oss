"""Sign-off + render dry-run."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_radio_dialogue_script_morning_shorts_v1 as builder
import scripts.record_radio_dialogue_signoff_v1 as signoff_mod
import scripts.radio_dialogue_render_edge_tts_v1 as render_mod


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
        "myeongni_lines": ["▸ 페이싱 우선"],
    }
    lp = tmp_path / "logos.json"
    bp = tmp_path / "briefing.json"
    fp = tmp_path / "fortune.json"
    lp.write_text(json.dumps(logos), encoding="utf-8")
    bp.write_text(json.dumps(briefing), encoding="utf-8")
    fp.write_text(json.dumps(fortune), encoding="utf-8")
    return lp, bp, fp


def test_signoff_matches_briefing_id(tmp_path: Path) -> None:
    lp, bp, fp = _fixture_bundle(tmp_path)
    doc = builder.build_morning_shorts_doc(tmp_path, logos_path=lp, briefing_path=bp, fortune_path=fp)
    sig = signoff_mod.build_signoff(doc, approved_by="tester")
    assert signoff_mod.check_signoff(doc, sig) == []


def test_render_dry_run_plan(tmp_path: Path, monkeypatch) -> None:
    lp, bp, fp = _fixture_bundle(tmp_path)
    doc = builder.build_morning_shorts_doc(tmp_path, logos_path=lp, briefing_path=bp, fortune_path=fp)
    (tmp_path / "script.json").write_text(json.dumps(doc), encoding="utf-8")
    sig = signoff_mod.build_signoff(doc, approved_by="tester")
    (tmp_path / "signoff.json").write_text(json.dumps(sig), encoding="utf-8")

    argv = [
        "radio_dialogue_render_edge_tts_v1.py",
        "--script-json",
        str(tmp_path / "script.json"),
        "--signoff-json",
        str(tmp_path / "signoff.json"),
        "--dry-run",
    ]
    monkeypatch.setattr(sys := __import__("sys"), "argv", argv)
    assert render_mod.main() == 0
