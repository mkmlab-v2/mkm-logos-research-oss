from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_accumulation_status_days_until_watchlist() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_accumulation_status_v1",
        ROOT / "scripts/build_sandbox_prophecy_accumulation_status_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    rollup = {
        "targets": [
            {
                "target_id": "eth_v1_price_only",
                "n_calendar_days": 2,
                "consecutive_days_at_or_above_threshold": 2,
                "last_hit_rate": 0.6,
            }
        ]
    }
    watchlist = {
        "candidates": [],
        "early_candidates": [{"target_id": "eth_v1_price_only", "streak_days": 2}],
    }
    doc = mod.build_status(rollup, watchlist)
    assert doc["max_n_calendar_days"] == 2
    assert doc["days_until_watchlist_eligible"] == 1
    assert doc["watchlist_gate_open"] is False
    assert "내일 UTC" in (doc.get("next_milestone_ko") or "")
