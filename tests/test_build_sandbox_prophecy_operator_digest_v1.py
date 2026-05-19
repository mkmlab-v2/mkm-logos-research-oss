from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operator_digest_line() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_operator_digest_v1",
        ROOT / "scripts/build_sandbox_prophecy_operator_digest_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    doc = mod.build_digest(
        {
            "n_targets": 27,
            "max_calendar_days": 2,
            "days_until_watchlist_eligible": 1,
            "n_early_watchlist": 5,
            "n_holdout_pass": 0,
            "leaderboard_top3": [{"target_id": "btc_phase3_composite_flow", "hit_rate": 0.633}],
        },
        {"status": "AWAITING_HUMAN"},
    )
    assert "[SANDBOX]" in doc["digest_line_ko"]
    assert "until_wl=1" in doc["digest_line_ko"]
