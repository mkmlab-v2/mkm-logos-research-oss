"""MAI GTM lookup."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.lookup_gtm_mai_archetype_v1 import (
    build_mai_public_card,
    lookup_mai_code,
    survey_bucket_from_proxies,
)

ROOT = Path(__file__).resolve().parent.parent


def test_survey_bucket_stable() -> None:
    b = survey_bucket_from_proxies(
        {
            "cold_heat_lean": 0.8,
            "digestion_lean": 0.2,
            "activity_lean": 0.6,
            "moisture_lean": 0.5,
        }
    )
    assert b.startswith("H")
    assert len(b) == 8


def test_lookup_returns_mai_code() -> None:
    draft = json.loads(
        (ROOT / "docs/final/artifacts/gtm_personality_wrapper_draft_v1.json").read_text(
            encoding="utf-8"
        )
    )
    code, method = lookup_mai_code(draft, survey_bucket="H2D1A2M1", myeongri_bucket="E*")
    assert code.startswith("MAI-")
    assert method in ("sample_mapping", "hash_fallback")


def test_public_card_has_no_sasang() -> None:
    card = build_mai_public_card(
        {
            "cold_heat_lean": 0.5,
            "digestion_lean": 0.5,
            "activity_lean": 0.5,
            "moisture_lean": 0.5,
        }
    )
    assert card["mai_code"].startswith("MAI-")
    assert card.get("one_liner_ko")
    assert "survey_bucket_internal" in card
    assert "sasang" not in json.dumps(card, ensure_ascii=False).lower()
