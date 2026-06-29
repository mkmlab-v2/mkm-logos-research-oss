"""Build hyper-personal intake snapshot (§10)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_hyper_personal_news_intake_v1 import build_intake, derive_priors

ROOT = Path(__file__).resolve().parents[1]
COMMANDER = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"


def test_derive_priors_bounded() -> None:
    commander = json.loads(COMMANDER.read_text(encoding="utf-8"))
    priors = derive_priors(commander)
    assert 0 <= priors["sasang_scalar"] <= 1
    assert -0.5 <= priors["myeongni_day_pillar_prior_hypo"] <= 0.5
    assert priors["wellness_hypo_budget"] == 0.25


def test_build_intake_shape() -> None:
    doc = build_intake(commander_path=COMMANDER, news_hp_rt_status="NOT_MEASURED")
    assert doc["schema"] == "hyper_personal_news_intake_v1"
    assert doc["field"]["regime_id"] == "regime_saving_the_news_hyper_personalization"
    assert doc["lenses"]["logos"]["role"] == "NON_GATING"
    assert doc["final"]["decision_label"] in ("WATCH", "HOLD")
    assert doc["final"]["cms_publish_allowed"] is False
