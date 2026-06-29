"""A-Code derive blends local survey responses (preview_only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personadiary_acode_profile_v1 as acode  # noqa: E402

LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryAcodeProfileV1.ts"


def _pkg() -> dict:
    return {
        "schema": "personadiary_daily_response_package_v1",
        "profile_id": "commander",
        "calendar_kst": "2026-06-24",
        "sections": [
            {"id": "lifestyle", "lines": ["날씨·서울: 22°C"]},
            {"id": "world_pulse", "lines": ["헤드라인 한 줄"]},
            {"id": "myeongni", "lines": ["흐름 한 줄"]},
            {"id": "mkm_4ai", "lines": ["마음 코칭"]},
        ],
    }


def test_ts_exports_survey_boost() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "surveyBoostForAcodeAxis" in text
    assert "surveyResponsesForAcodeDerive" in str(
        (ROOT / "projects/no1kmedi/src/lib/personadiaryConsumerProfileV1.ts").read_text(
            encoding="utf-8"
        )
    )


def _pkg_neutral() -> dict:
    """Package without axis keyword hits — survey boost should steer derive."""
    return {
        "schema": "personadiary_daily_response_package_v1",
        "profile_id": "commander",
        "calendar_kst": "2026-06-24",
        "sections": [
            {"id": "lifestyle", "lines": ["오늘 일정"]},
            {"id": "world_pulse", "lines": ["뉴스 요약"]},
            {"id": "myeongni", "lines": ["메모"]},
            {"id": "mkm_4ai", "lines": ["노트"]},
        ],
    }


def test_survey_boost_changes_phase_or_axis() -> None:
    base = acode.derive_personadiary_acode_profile(_pkg_neutral())
    fatigued = acode.derive_personadiary_acode_profile(
        _pkg_neutral(),
        {"ac02": 4, "dg02": 4, "ch02": 4, "ch01": 0, "dg01": 0},
    )
    active = acode.derive_personadiary_acode_profile(
        _pkg_neutral(),
        {"ac01": 4, "ac02": 0, "dg01": 4, "ch01": 0, "dg02": 0},
    )
    assert base["public_code"].startswith("AC-")
    assert fatigued["public_code"].startswith("AC-")
    assert active["public_code"].startswith("AC-")
    assert fatigued["public_code"] != active["public_code"]


def test_survey_pack_json_loads() -> None:
    pack = json.loads(
        (ROOT / "projects/no1kmedi/public/data/clinic_constitution_survey_pack_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack.get("pack_id") == "mkm_constitution_survey_core_v1"
