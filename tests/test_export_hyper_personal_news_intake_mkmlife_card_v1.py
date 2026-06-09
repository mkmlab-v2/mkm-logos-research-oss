"""mkmlife §10 intake card export smoke."""

from __future__ import annotations

import json

from scripts.export_hyper_personal_news_intake_mkmlife_card_v1 import build_card
from scripts.mkm_consumer_facade_v1 import facade_hyper_personal_card


def test_build_mkmlife_hp_card_has_dual_compression() -> None:
    intake = {
        "schema": "hyper_personal_news_intake_v1",
        "generated_at_utc": "2026-06-05T00:00:00Z",
        "field": {
            "regime_id": "regime_saving_the_news_hyper_personalization",
            "priors": {
                "sasang_scalar": 0.7,
                "myeongni_day_pillar_prior_hypo": 0.06,
                "wellness_hypo_budget": 0.25,
            },
        },
        "lenses": {
            "sasang": {"summary_ko": "s"},
            "myeongni": {"summary_ko": "m"},
            "logos": {"summary_ko": "l"},
        },
        "final": {
            "decision_label": "WATCH",
            "cms_publish_allowed": False,
            "one_line_ko": "shadow",
            "disclaimer_ko": "test",
        },
    }
    hp = {
        "measurement_status": "COMPLETE",
        "kpi": {"token_saving_ratio_hp_weighted": 0.46},
        "delta_vs_news_rt_baseline": {"token_saving_ratio_delta_hp_minus_baseline": 0.07},
    }
    raw = {"kpi": {"token_saving_ratio": 0.38}}
    card = facade_hyper_personal_card(build_card(intake, hp, raw))
    assert card["schema"] == "hyper_personal_news_intake_mkmlife_card_v1"
    assert card["lane"] == "research_only"
    assert card["ready_for_external_send"] is False
    assert card["dual_compression"]["raw_token_saving"] == 0.38
    assert card["dual_compression"]["hp_token_saving"] == 0.46
    assert len(card["priors_display"]) == 3
    assert card["priors_display"][0]["label_ko"] == "A-Code 큐레이션 강도"
    assert "Logos" not in json.dumps(card["forbidden"], ensure_ascii=False)
