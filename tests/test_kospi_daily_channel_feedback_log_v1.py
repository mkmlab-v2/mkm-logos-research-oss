"""Tests for daily channel feedback log."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_kospi_daily_channel_feedback_log_v1 import build_feedback_row


def test_feedback_row_fail_rescue_flag():
    rules = {"neutral_band": 0.06, "blend_policy_v2": {}, "forward_flow_gate_policy_v1": {"max_lag_calendar_days": 14}}
    cal_row = {
        "session_date": "2026-06-26",
        "predicted_direction": "bull",
        "blend": {
            "channels": [
                {"channel": "field_regime", "direction": "bear", "weight": 0.0},
            ],
            "votes": {"bull": 0.78, "bear": 0.0},
            "winner": "bull",
            "blended_score": 0.5,
        },
    }
    eval_row = {
        "session_date": "2026-06-26",
        "predicted_direction": "bull",
        "actual_direction": "bear",
        "outcome": "FAIL",
        "daily_return_pct": -5.8,
    }
    row = build_feedback_row(
        session_date="2026-06-26",
        year_month="2026-06",
        cal_row=cal_row,
        eval_row=eval_row,
        rules=rules,
        flow={"2026-06-25": 50000.0},
        eval_stub={"rows": [eval_row]},
    )
    assert row["active_outcome"] == "FAIL"
    assert row["briefing_merge_forbidden"] is True
    assert isinstance(row["suppressed_bear_channels"], list)
