from __future__ import annotations

import scripts.apply_btc_weight_sweep_winner_v1 as mod


def test_pick_winner_prefers_higher_confidence_among_candidates() -> None:
    sweep = {
        "profiles": [
            {"profile": "btc_70", "ok": True, "weights": {"price": 0.7}, "result": {"confidence": 0.5, "guard_blocked": False}},
            {"profile": "btc_80", "ok": True, "weights": {"price": 0.8}, "result": {"confidence": 0.6, "guard_blocked": False}},
        ]
    }
    name, weights, _ = mod.pick_winner(sweep, candidates=["btc_70", "btc_80"])
    assert name == "btc_80"
    assert weights["price"] == 0.8


def test_pick_winner_tie_breaks_by_candidate_order() -> None:
    sweep = {
        "profiles": [
            {"profile": "btc_70", "ok": True, "weights": {"price": 0.7}, "result": {"confidence": 0.5, "guard_blocked": False}},
            {"profile": "btc_80", "ok": True, "weights": {"price": 0.8}, "result": {"confidence": 0.5, "guard_blocked": False}},
        ]
    }
    name, _, _ = mod.pick_winner(sweep, candidates=["btc_70", "btc_80"])
    assert name == "btc_70"


def test_pick_winner_skips_guard_blocked() -> None:
    sweep = {
        "profiles": [
            {"profile": "btc_70", "ok": True, "weights": {"price": 0.7}, "result": {"confidence": 0.9, "guard_blocked": True}},
            {"profile": "btc_80", "ok": True, "weights": {"price": 0.8}, "result": {"confidence": 0.1, "guard_blocked": False}},
        ]
    }
    name, weights, _ = mod.pick_winner(sweep, candidates=["btc_70", "btc_80"])
    assert name == "btc_80"
    assert weights["price"] == 0.8
