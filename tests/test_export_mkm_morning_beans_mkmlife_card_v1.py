"""mkmlife Morning Beans card export smoke."""

from __future__ import annotations

from scripts.export_mkm_morning_beans_mkmlife_card_v1 import build_card


def test_build_mkmlife_morning_beans_card() -> None:
    feed = {
        "schema": "mkm_morning_beans_feed_v1",
        "generated_at_utc": "2026-06-09T01:00:00Z",
        "feed_date_local": "2026-06-09",
        "field": {
            "regime_id": "post_covid_normalization",
            "regime_label_ko": "포스트 코로나 정상화",
        },
        "feed_policy": {"max_cards": 10, "anti_doomscroll": True, "session_ttl_minutes": 12},
        "pipeline_summary": {
            "final_action": "WATCH",
            "conflict_note_ko": "격벽 유지",
        },
        "track_c_positioning_v1": {
            "headline_ko": "아침 10장",
            "subline_ko": "멀티렌즈 분리",
        },
        "subject_ref": {"profile_path": "docs/final/artifacts/commander_profile_v1.example.json"},
        "cards": [
            {
                "card_id": "card_01",
                "lane": "field_regime",
                "epistemic_label": "FACT",
                "lens_slot": None,
                "title_ko": "Field",
                "body_ko": "관측만.",
                "deep_link": {"kind": "artifact", "path_or_route": "a.json", "label_ko": "a"},
            }
        ],
        "final": {
            "decision_label": "WATCH",
            "card_count": 1,
            "disclaimer_ko": "test",
        },
        "audit": {"guardrail_script_exit": 0, "model_route": "local_stub_no_llm"},
    }
    card = build_card(feed)
    assert card["schema"] == "mkm_morning_beans_mkmlife_card_v1"
    assert card["lane"] == "research_only"
    assert card["ready_for_external_send"] is False
    assert card["regime_id"] == "post_covid_normalization"
    assert len(card["cards_display"]) == 1
    assert card["cards_display"][0]["epistemic_label"] == "FACT"
