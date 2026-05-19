"""Human review pack builder — decision logic."""
from __future__ import annotations

from scripts.build_btrack_v1_price_only_human_review_pack_v1 import (
    PROFILE,
    _decision_block,
    _find_candidate,
)


def test_find_candidate_by_profile() -> None:
    cands = [
        {"candidate_id": "ensemble_v1_price_only_30", "window": "30", "profile": PROFILE, "price_directional_hit_rate": 0.43},
    ]
    found = _find_candidate(cands, profile=PROFILE, window="30")
    assert found is not None
    assert found["price_directional_hit_rate"] == 0.43


def test_decision_reject_when_30d_fails() -> None:
    prod = {"price_directional_hit_rate": 0.366667}
    c30 = {"price_directional_hit_rate": 0.433333, "alert_1_pass": False}
    c180 = {"price_directional_hit_rate": 0.511111, "alert_1_pass": True}
    d = _decision_block(prod_30=prod, cand_30=c30, cand_180=c180)
    assert d["apply_to_prod_score_json"] is False
    assert d["track_a_promotion"] is False
    assert d["auto_promote"] is False
    assert d["human_decision"] == "HOLD_REVIEW_180_ONLY"


def test_decision_reject_both_fail() -> None:
    d = _decision_block(
        prod_30={"price_directional_hit_rate": 0.36},
        cand_30={"price_directional_hit_rate": 0.40},
        cand_180={"price_directional_hit_rate": 0.45},
    )
    assert d["human_decision"] == "REJECT_APPLY"
