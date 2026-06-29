"""Constitution survey pack scoring."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.lookup_gtm_mai_archetype_v1 import build_mai_public_card
from scripts.score_clinic_constitution_survey_v1 import (
    load_survey_bank,
    score_survey_responses,
)

ROOT = Path(__file__).resolve().parent.parent


def test_bank_loads_items() -> None:
    bank = load_survey_bank(ROOT)
    assert bank["pack_id"] == "mkm_constitution_survey_core_v1"
    assert len(bank["items"]) >= 10


def test_all_heat_responses_skews_soyang_or_uncertain() -> None:
    bank = load_survey_bank(ROOT)
    responses = {
        str(item["item_id"]): 4
        for item in bank["items"]
        if item.get("direction") == "heat"
    }
    # answer all items at max for stable test
    responses = {str(item["item_id"]): 4 for item in bank["items"]}
    out = score_survey_responses(bank, responses)
    proxies = out["observation_proxies"]
    assert all(0 <= proxies[k] <= 1 for k in proxies)
    assert out["ai_hypothesis"]["constitution"] in {
        "taeeum",
        "soyang",
        "taeyang",
        "soeum",
        "uncertain",
    }


def test_park_geumja_intake_bootstrap_scores() -> None:
    from scripts.score_clinic_constitution_survey_v1 import infer_responses_from_intake

    bank = load_survey_bank(ROOT)
    doc = json.loads(
        (ROOT / "reports/park_geumja_intake_fusion_v1.json").read_text(encoding="utf-8")
    )
    responses = infer_responses_from_intake(bank, doc["intake"])
    out = score_survey_responses(bank, responses)
    assert out["survey_meta"]["n_items_answered"] == len(bank["items"])


def test_mai_card_from_proxies() -> None:
    bank = load_survey_bank(ROOT)
    responses = {str(item["item_id"]): 2 for item in bank["items"]}
    out = score_survey_responses(bank, responses)
    card = build_mai_public_card(out["observation_proxies"])
    assert card["schema"] == "gtm_mai_public_card_v1"
    assert card["mai_code"].startswith("MAI-")
