from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ops_dashboard_merges_slices() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_ops_dashboard_v1",
        ROOT / "scripts/build_sandbox_prophecy_ops_dashboard_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    doc = mod.build_dashboard(
        health={
            "ok": True,
            "checks": {"rollup_progress": {"max_n_calendar_days": 2, "watchlist_ready": False}},
        },
        watchlist={"candidates": [], "early_candidates": [{"target_id": "eth_v1_price_only"}]},
        bridge={"n_tier_early_watchlist": 1, "recommended_next_human_action": "wait"},
        brief={"leaderboard_top5": [{"target_id": "eth_v1_price_only", "hit_rate": 0.6}]},
        holdout={"n_holdout_pass": 0},
        chain={"ok": True, "n_targets": 27},
        accumulation={"max_n_calendar_days": 2, "days_until_watchlist_eligible": 1},
    )
    assert doc["schema"] == "sandbox_prophecy_ops_dashboard_v1"
    assert doc["n_early_watchlist"] == 1
    assert doc["max_calendar_days"] == 2
    assert doc["days_until_watchlist_eligible"] == 1
