"""O-P31c summary — RTMP configured detection (plan, env, command file)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_radio_op31c_daily_summary_v1 import (
    _rtmp_command_live,
    _rtmp_url_configured,
    build_summary,
)


def test_rtmp_command_live_detects_placeholder(tmp_path: Path) -> None:
    cmd = tmp_path / "reports" / "ambient_stream_rtmp_command_latest.txt"
    cmd.parent.mkdir(parents=True)
    cmd.write_text("# Set YOUTUBE_RTMP_URL\n# ffmpeg ...\n", encoding="utf-8")
    assert _rtmp_command_live(tmp_path) is False

    cmd.write_text("ffmpeg -re -i video.mp4 -f flv rtmp://a.rtmp.youtube.com/live2/key\n", encoding="utf-8")
    meta = cmd.with_suffix(".meta.json")
    meta.write_text(json.dumps({"rtmp_configured": True}), encoding="utf-8")
    assert _rtmp_command_live(tmp_path) is True


def test_rtmp_url_configured_from_command_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_RTMP_URL", raising=False)
    rel = "reports/ambient_stream_rtmp_command_latest.txt"
    cmd = tmp_path / rel
    cmd.parent.mkdir(parents=True)
    cmd.write_text("ffmpeg -re -f flv rtmp://a.rtmp.youtube.com/live2/x\n", encoding="utf-8")
    meta = cmd.with_suffix(".meta.json")
    meta.write_text(json.dumps({"rtmp_configured": True}), encoding="utf-8")
    plan = {"rtmp_url_set": False}
    assert _rtmp_url_configured(tmp_path, plan) is True


def test_summary_zone_a_stage_l1(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_RTMP_URL", "rtmp://a.rtmp.youtube.com/live2/test-key")
    root = tmp_path
    for rel in (
        "reports/commander_daily_logos_anchor_latest.json",
        "reports/commander_daily_fortune_latest.json",
        "reports/commander_advanced_briefing_latest.json",
        "reports/radio_dialogue_script_morning_shorts_latest.json",
        "reports/radio_dialogue_script_gate_morning_latest.json",
        "reports/radio_dialogue_script_gate_friday_latest.json",
        "reports/radio_dialogue_script_health_shorts_latest.json",
        "reports/radio_dialogue_script_gate_health_latest.json",
        "reports/radio_dialogue_script_friday_vod_latest.json",
        "reports/audio/mkm_ambient_bed_loop_latest.wav",
        "reports/ambient_stream_manifest_latest.json",
        "reports/ambient_stream_ffmpeg_plan_latest.json",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"gate_ok": true}' if "gate" in rel else "{}", encoding="utf-8")

    doc = build_summary(root)
    assert doc["rtmp_url_configured"] is True
    assert doc["zone_a_live_stage"] == "L1_rtmp_wired"
