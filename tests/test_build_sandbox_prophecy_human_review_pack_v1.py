from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_human_review_pack_awaiting_human() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_human_review_pack_v1",
        ROOT / "scripts/build_sandbox_prophecy_human_review_pack_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    doc = mod.build_pack(
        bridge={
            "n_total_draft_rows": 2,
            "n_tier_early_watchlist": 2,
            "tier_early_watchlist": [{"target_id": "eth_v1_price_only"}],
        },
        promotion={"candidates": [{"target_id": "eth_v1_price_only", "panel_hit_rate": 0.6}]},
        accumulation={"max_n_calendar_days": 2, "days_until_watchlist_eligible": 1},
        watchlist={"early_candidates": [{"target_id": "eth_v1_price_only"}]},
        mainline={"status": "APPROVED_CANDIDATE"},
    )
    assert doc["status"] == "AWAITING_HUMAN"
    assert doc["runtime_constraints"]["prod_score_mutation"] is False
    assert len(doc["human_review_checklist_ko"]) >= 4
