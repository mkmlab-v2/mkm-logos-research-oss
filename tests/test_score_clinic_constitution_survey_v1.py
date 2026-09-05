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


def test_all_max_responses_proxies_in_unit_interval() -> None:
    """Smoke only: every item=4 → proxies in [0,1] and constitution enum. Not a heat-skew test."""
    bank = load_survey_bank(ROOT)
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


def test_soeum_lower_solid_upper_weak_not_taeeum_body_collision() -> None:
    """v1.2 regression: 상체약·하체상대실 + 한증·소화약 → soeum > taeeum (tb01/zb02 교차오염 금지)."""
    bank = load_survey_bank(ROOT)
    assert bank.get("version") == "1.2.0"
    # 중립 2점 후, 소음 전형만 올림 / 태음 전체체격·복부돌출은 낮춤
    responses = {str(item["item_id"]): 2 for item in bank["items"]}
    responses.update(
        {
            "ch02": 4,  # 수족냉
            "dg02": 4,  # 소화더딤
            "ac02": 4,  # 피로
            "tb01": 1,  # 전체 체격 큼·배 나옴 — 소음형 거부
            "tb02": 4,  # 마름 + 하체 상대실
            "zb01": 1,  # 상체·목덜미
            "zb02": 1,  # 배 나옴·전체 굵음 — 소음형 거부
            "zb03": 1,  # 중초 왕성
            "zb04": 4,  # 하체 실·상체·소화 약
            "sj03": 4,  # 소음 성정
        }
    )
    out = score_survey_responses(bank, responses)
    hints = out["survey_meta"]["hint_scores"]
    assert hints["soeum"] > hints["taeeum"]
    assert out["ai_hypothesis"]["constitution"] == "soeum"
