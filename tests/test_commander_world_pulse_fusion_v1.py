"""World pulse fusion — artifact read + telegram section contract."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.commander_world_pulse_fusion_v1 as wp

ROOT = Path(__file__).resolve().parents[1]


def test_build_world_pulse_schema() -> None:
    doc = wp.build_world_pulse(workspace=ROOT)
    assert doc["schema"] == "commander_world_pulse_fusion_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["non_gating"] is True
    assert doc.get("body_lines")
    assert any("코스피" in ln for ln in doc["body_lines"])


def test_fusion_one_liner() -> None:
    world = {"kospi": {"today_action": "WATCH"}, "macro": {"decision_state": "WATCH"}, "headline_ko": "Policy news"}
    line = wp.build_fusion_one_liner("오늘 한 줄: 테스트", world)
    assert "나:" in line
    assert "판:" in line
    assert "[가설]" in line


def test_append_world_pulse_telegram() -> None:
    tg: list[str] = []
    out = wp.append_world_pulse_telegram(tg, myeongni_lines=["오늘 한 줄: 월운 테스트"], workspace=ROOT)
    assert out.get("fusion_one_liner_ko")
    text = "\n".join(tg)
    assert "찰나의 나라" in text
    assert "융합 한 줄" in text
    assert "시장 예언" not in text  # guardrail-friendly boundary wording


def test_assemble_includes_world_pulse_section() -> None:
    import scripts.assemble_personadiary_daily_response_package_v1 as pd

    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "city_default": "Seoul",
        "world_pulse_fusion": {
            "fusion_one_liner_ko": "나: 테스트 · 판: WATCH · [가설]",
        },
        "telegram_append_lines": [
            "▸ 개인 일운 (명리)",
            "  한 줄",
            "▸ 찰나의 나라 (세상×나) [가설]",
            "  융합 한 줄: 나·판",
            "  코스피·장면: WATCH",
        ],
        "logos_daily_anchor": {},
    }
    pkg = pd.assemble_package(fortune, fortune_path=Path("x.json"))
    ids = [s["id"] for s in pkg["sections"]]
    assert "world_pulse" in ids
    types = [b["type"] for b in pkg["ui_blocks"]]
    assert "hero" in types
    assert "world_pulse" in types
