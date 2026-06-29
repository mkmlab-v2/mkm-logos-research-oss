"""Build MKM Morning Beans feed v1 smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_mkm_morning_beans_feed_v1 import (
    _pick_calendar_events,
    build_feed,
    resolve_field,
)

ROOT = Path(__file__).resolve().parents[1]
COMMANDER = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"
CALENDAR = ROOT / "docs/final/artifacts/mkm_morning_beans_calendar_v1_latest.json"
MACRO = ROOT / "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json"


def test_resolve_field_from_macro() -> None:
    macro = json.loads(MACRO.read_text(encoding="utf-8"))
    field = resolve_field(macro)
    assert field["regime_id"] == "post_covid_normalization"
    assert field["regime_source"] == "regime_map"
    assert field["operator_posture_hint"] in ("WATCH", "HOLD", "REDUCE")


def test_pick_calendar_events_excludes_ops_blocked() -> None:
    cal = {
        "events_local": [
            {"title": "ok", "start_local": "2026-06-09T10:00:00+09:00", "rail": "family_anchor"},
            {
                "title": "blocked",
                "start_local": "2026-06-09T11:00:00+09:00",
                "rail": "ops_blocked_from_personal_cards",
            },
        ]
    }
    picked = _pick_calendar_events(cal, feed_date_local="2026-06-09")
    assert len(picked) == 1
    assert picked[0]["title"] == "ok"


def test_build_feed_shape_and_guardrails() -> None:
    doc = build_feed(
        commander_path=COMMANDER,
        macro_path=MACRO,
        calendar_path=CALENDAR,
        feed_date_local="2026-06-09",
        max_cards=10,
    )
    assert doc["schema"] == "mkm_morning_beans_feed_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["feed_policy"]["anti_doomscroll"] is True
    assert doc["governance"]["track_a_auto_merge"] is False
    assert doc["final"]["cms_publish_allowed"] is False
    assert doc["final"]["card_count"] >= 7
    assert doc["audit"]["guardrail_script_exit"] == 0

    titles = [c["title_ko"] for c in doc["cards"]]
    assert any("강민" in t or "이강민" in t for t in titles)
    assert any("딸" in t for t in titles)
    assert any("일정" in t for t in titles)
    assert not any("MS 340" in c["body_ko"] for c in doc["cards"])

    calendar_src = [s for s in doc["input_sources"] if s.get("source_id") == "calendar_local"]
    assert calendar_src
    assert calendar_src[0]["consent"] == "explicit_local"

    logos = [c for c in doc["cards"] if c.get("lens_slot") == "logos"]
    assert logos
    assert logos[0]["epistemic_label"] == "NON_GATING"

    for card in doc["cards"]:
        assert card["guardrail_precheck"]["ops_stage_tokens_absent"] is True
        assert card["guardrail_precheck"]["market_debt_bleed_absent"] is True
