from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bridge_draft_tiers() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_track_a_candidate_bridge_draft_v1",
        ROOT / "scripts/build_sandbox_track_a_candidate_bridge_draft_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    panel = {
        "targets": [
            {
                "target_id": "eth_v1_price_only",
                "asset": "eth",
                "lens_profile": "v1_price_only",
                "hit_rate": 0.6,
                "n_evaluated": 30,
                "ok": True,
            },
            {
                "target_id": "btc_v2_confidence_fusion",
                "asset": "btc",
                "lens_profile": "v2_confidence_fusion",
                "hit_rate": 0.0,
                "n_evaluated": 30,
                "ok": True,
            },
        ]
    }
    holdout = {"holdout_pass_target_ids": ["eth_v1_price_only"]}
    rollup = {
        "early_watchlist": [
            {"target_id": "eth_v1_price_only", "streak_days": 2, "mean_hit_last_7d": 0.6}
        ]
    }
    promotion = {
        "candidates": [{"target_id": "eth_v1_price_only", "panel_hit_rate": 0.6}]
    }
    doc = mod.build_bridge_draft(
        panel=panel,
        holdout=holdout,
        promotion=promotion,
        rollup=rollup,
        mainline_candidate=None,
    )
    assert doc["runtime_constraints"]["overwrites_prophecy_track_a_candidate_v1"] is False
    assert doc["n_tier_holdout_pass"] == 1
    assert doc["n_tier_early_watchlist"] == 0
    assert doc["tier_holdout_pass"][0]["bridge_readiness"] == "ready_for_human_review"
