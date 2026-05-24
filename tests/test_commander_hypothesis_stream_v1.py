"""Commander hypothesis stream P31a — branches + archive + assemble."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_commander_hypothesis_stream_v1 as hs

ROOT = Path(__file__).resolve().parents[1]


def test_build_hypothesis_stream_schema() -> None:
    world = {
        "schema": "commander_world_pulse_fusion_v1",
        "kospi": {"today_action": "WATCH"},
        "macro": {"decision_state": "WATCH"},
        "headlines_top_ko": ["Headline A"],
        "news": {"confidence": 0.2},
    }
    myeongni = [
        "▸ 오늘 한 줄: 월운 상관 — 말·결정",
        "월운 5월 庚午(상관) — 힌트",
        "오행 우세 목 / 약 화",
    ]
    doc = hs.build_hypothesis_stream(
        myeongni_lines=myeongni,
        world_pulse=world,
        calendar_kst="2026-05-22",
    )
    assert doc["schema"] == "commander_hypothesis_stream_v1"
    assert doc["non_gating"] is True
    assert 3 <= len(doc["branches"]) <= 5
    assert doc["track_a_auto_order_forbidden"] is True
    text = json.dumps(doc, ensure_ascii=False)
    assert "10:00" not in text and "10–12" not in text


def test_write_hypothesis_log(tmp_path: Path, monkeypatch) -> None:
    import scripts.build_commander_hypothesis_stream_v1 as mod

    log_dir = tmp_path / "hypothesis_log"
    monkeypatch.setattr(mod, "LOG_DIR", log_dir)
    stream = {
        "schema": "commander_hypothesis_stream_v1",
        "calendar_kst": "2026-05-22",
        "branches": [],
    }
    out = mod.write_hypothesis_log(stream, fortune_path=tmp_path / "fortune.json", workspace=tmp_path)
    assert out.is_file()
    env = json.loads(out.read_text(encoding="utf-8"))
    assert env["schema"] == "commander_hypothesis_log_v1"
    assert env["hypothesis_stream"]["calendar_kst"] == "2026-05-22"


def test_assemble_includes_hypothesis_stream() -> None:
    import scripts.assemble_personadiary_daily_response_package_v1 as pd

    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "city_default": "Seoul",
        "hypothesis_stream": {
            "synthesis_ko": "초론 요약 테스트",
            "branches": [
                {
                    "branch_id": "x",
                    "trigger_ko": "t",
                    "predicted_bias_ko": "b",
                    "confidence": "mid",
                }
            ],
        },
        "world_pulse_fusion": {"fusion_one_liner_ko": "융합"},
        "telegram_append_lines": [
            "▸ 개인 일운 (명리)",
            "  한 줄",
            "▸ 오늘 초론 스트림 [가설][NON_GATING]",
            "  초론 요약",
            "  1. [mid] trigger → bias",
        ],
        "logos_daily_anchor": {},
    }
    pkg = pd.assemble_package(fortune, fortune_path=Path("x.json"))
    assert "hypothesis_stream" in [s["id"] for s in pkg["sections"]]
    assert "hypothesis_stream" in [b["type"] for b in pkg["ui_blocks"]]
