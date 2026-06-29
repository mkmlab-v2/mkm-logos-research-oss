"""Contract tests for mkm_morning_beans_feed_v1 ([HYPO], research_only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_morning_beans_feed_v1.schema.json"
FIXTURE_PATH = ROOT / "docs/final/artifacts/fixtures/mkm_morning_beans_feed_v1.example.json"


@pytest.mark.skipif(not SCHEMA_PATH.is_file(), reason="schema missing")
def test_mkm_morning_beans_feed_example_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    jsonschema.validate(doc, schema)


def test_mkm_morning_beans_feed_shape_and_governance() -> None:
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "mkm_morning_beans_feed_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["feed_policy"]["max_cards"] <= 14
    assert doc["feed_policy"]["anti_doomscroll"] is True
    assert doc["field"]["regime_source"] == "regime_map"
    assert doc["governance"]["track_a_auto_merge"] is False
    assert doc["governance"]["live_trading_trigger"] is False
    assert doc["final"]["cms_publish_allowed"] is False

    logos_cards = [c for c in doc["cards"] if c.get("lens_slot") == "logos"]
    assert logos_cards
    assert logos_cards[0]["epistemic_label"] == "NON_GATING"

    for card in doc["cards"]:
        assert card["guardrail_precheck"]["ops_stage_tokens_absent"] is True
        assert card["guardrail_precheck"]["market_debt_bleed_absent"] is True

    positioning = doc["track_c_positioning_v1"]
    assert "아침" in positioning["headline_ko"]
    assert "멀티렌즈" in positioning["subline_ko"]


def test_mkm_morning_beans_schema_title() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    assert schema["title"] == "mkm_morning_beans_feed_v1"
