"""PersonaDiary A-Code profile derive + meal menu (Python mirror)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personadiary_acode_profile_v1 as acode  # noqa: E402

SCHEMA = ROOT / "docs/final/schemas/personadiary_acode_persona_v1.schema.json"


def _sample_package() -> dict:
    return {
        "schema": "personadiary_daily_response_package_v1",
        "profile_id": "commander",
        "calendar_kst": "2026-06-24",
        "sections": [
            {
                "id": "lifestyle",
                "lines": ["날씨·서울: 22°C", "점심 추천: 닭곰탕"],
            },
            {
                "id": "world_pulse",
                "lines": ["1. 코스피 변동 헤드라인"],
            },
            {
                "id": "myeongni",
                "lines": ["오늘 한 줄: 균형을 지키며 정리"],
            },
            {
                "id": "mkm_4ai",
                "lines": ["마음 코칭: 호흡을 가볍게"],
            },
        ],
    }


def test_derive_acode_public_code() -> None:
    profile = acode.derive_personadiary_acode_profile(_sample_package())
    assert profile["schema"] == "personadiary_acode_persona_v1"
    assert profile["public_code"].startswith("AC-")
    assert profile["preview_only"] is True


def test_meal_menu_recommendation_includes_acode_and_menu() -> None:
    summary = acode.build_moment_meal_menu_recommendation(_sample_package())
    assert "닭곰탕" in summary or "곰탕" in summary
    assert "AC-" in summary
    assert "역" not in summary


def test_acode_schema_file_valid_json() -> None:
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert doc.get("$schema")
    assert doc["properties"]["public_code"]["pattern"].startswith("^AC-")
