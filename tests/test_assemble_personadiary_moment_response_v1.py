"""PersonaDiary moment response assembler v1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assemble_personadiary_moment_response_v1 as asm  # noqa: E402


def _minimal_package() -> dict:
    return {
        "schema": "personadiary_daily_response_package_v1",
        "calendar_kst": "2026-06-06",
        "city_default": "Seoul",
        "profile_id": "commander",
        "sections": [
            {
                "id": "myeongni",
                "title_ko": "명리",
                "lines": ["일운 테스트 한 줄"],
            },
            {
                "id": "lifestyle",
                "title_ko": "라이프",
                "lines": [
                    "날씨·서울: 14°C",
                    "점심 추천: 닭곰탕",
                    "피하기: 과한 매운 것",
                ],
            },
            {
                "id": "logos_anchor",
                "title_ko": "성경",
                "lines": ["앵커: 시편 23:1 — 여호와는 나의 목자시니"],
            },
        ],
        "disclaimer_ko": "테스트 면책",
    }


def test_meal_response_cards() -> None:
    doc = asm.assemble_moment_response(_minimal_package(), "점심 뭐 먹지?")
    assert doc["schema"] == "personadiary_moment_response_v1"
    assert doc["intent"] == "meal"
    assert doc["preview_only"] is True
    acode = doc.get("acode_persona") or {}
    assert acode.get("public_code", "").startswith("AC-")
    assert doc["regime_field"] == "regime_personadiary_moment_exploration"
    ids = [c["section_id"] for c in doc["cards"]]
    assert "lifestyle" in ids
    assert any("닭곰탕" in c["body_ko"] for c in doc["cards"])
    lifestyle = next(c for c in doc["cards"] if c["section_id"] == "lifestyle")
    assert lifestyle["body_ko"].split("\n")[0].startswith("점심 추천")
    assert "닭곰탕" in doc["summary_ko"] or "AC-" in doc["summary_ko"]


def test_logos_non_gating_badge() -> None:
    doc = asm.assemble_moment_response(_minimal_package(), "기분이 우울해")
    assert doc.get("prophecy_vote") == "none"
    logos = next((c for c in doc["cards"] if c["section_id"] == "logos_anchor"), None)
    if logos:
        assert "[NON_GATING]" in logos.get("badge_ko", "")


def test_world_me_prefers_world_pulse_section() -> None:
    pkg = _minimal_package()
    pkg["sections"].append(
        {
            "id": "world_pulse",
            "title_ko": "찰나",
            "lines": ["세상 헤드라인: 테스트 뉴스 한 줄", "코스피 WATCH"],
        }
    )
    pkg["sections"].append(
        {
            "id": "hypothesis_stream",
            "title_ko": "초론",
            "lines": ["페이싱 우선 [가설]"],
        }
    )
    doc = asm.assemble_moment_response(pkg, "오늘 뉴스 어때?")
    assert doc["intent"] == "world_me"
    ids = [c["section_id"] for c in doc["cards"]]
    assert "world_pulse" in ids


def test_deterministic_replay() -> None:
    pkg = _minimal_package()
    a = asm.assemble_moment_response(pkg, "오늘 점심 추천")
    b = asm.assemble_moment_response(pkg, "오늘 점심 추천")
    assert a["intent"] == b["intent"]
    assert a["cards"] == b["cards"]
