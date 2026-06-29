"""Smoke tests for PersonaDiary body-rhythm lifestyle builder v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_personadiary_body_rhythm_lifestyle_v1 as br  # noqa: E402
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "personadiary_body_rhythm_lifestyle_v1.schema.json"


def test_build_body_rhythm_required_menus():
    doc = br.build_body_rhythm(calendar_kst="2026-06-07", age_band="40_50")
    assert doc["schema"] == "personadiary_body_rhythm_lifestyle_v1"
    assert doc["hypothesis_tier"] == "B"
    menus = doc["menus"]
    for key in ("meal_fasting", "movement_10m", "style_fit", "breath_1m", "space_tip"):
        assert key in menus
        assert menus[key]["evidence_tier"] in (
            "literature_supported",
            "coaching_heuristic",
            "delight",
        )
    assert "부분 감량" in menus["meal_fasting"]["one_liner_ko"] or "부분감량" in doc["disclaimer_ko"]


def test_infer_age_band():
    assert br.infer_age_band(28) == "20_30"
    assert br.infer_age_band(45) == "40_50"
    assert br.infer_age_band(67) == "60_plus"


def test_merge_into_daily_package_adds_upstream():
    body = br.build_body_rhythm(calendar_kst="2026-06-07")
    pkg = {
        "sections": [{"id": "lifestyle", "title_ko": "오늘의 라이프", "lines": ["기존 라인"]}],
        "ui_blocks": [{"type": "hero", "title_ko": "h", "body_ko": "b"}],
        "concept_ko": "테스트",
    }
    merged = br.merge_into_daily_package(pkg, body)
    assert "body_rhythm" in merged["upstream"]
    lifestyle = next(s for s in merged["sections"] if s["id"] == "lifestyle")
    assert any("몸·리듬" in ln for ln in lifestyle["lines"])
    assert sum(1 for b in merged["ui_blocks"] if b.get("title_ko", "").startswith("몸·리듬")) == 5


def test_schema_file_exists_and_parses():
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["title"] == "personadiary_body_rhythm_lifestyle_v1"
