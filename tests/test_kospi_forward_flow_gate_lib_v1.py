"""Tests for kospi_forward_flow_gate_lib_v1."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.kospi_forward_flow_gate_lib_v1 import (
    evaluate_conditional_unlock,
    resolve_prior_foreign_for_gate,
)


def test_stale_forward_skips_foreign_gate():
    flow = {"2026-06-26": -30000.0}
    ctx = resolve_prior_foreign_for_gate(flow, "2028-08-01", max_lag_calendar_days=14)
    assert ctx.gate_mode == "skipped_stale_forward"
    assert ctx.apply_foreign_flow_gate is False
    allow, blocks = evaluate_conditional_unlock(
        prior_foreign=ctx.value,
        shock_pred=False,
        apply_foreign_flow_gate=ctx.apply_foreign_flow_gate,
    )
    assert allow is True
    assert blocks == []


def test_live_flow_applies_foreign_gate():
    flow = {"2026-06-25": -30000.0, "2026-06-26": -30000.0}
    ctx = resolve_prior_foreign_for_gate(flow, "2026-06-27", max_lag_calendar_days=14)
    assert ctx.gate_mode == "live"
    allow, blocks = evaluate_conditional_unlock(
        prior_foreign=ctx.value,
        shock_pred=False,
        apply_foreign_flow_gate=ctx.apply_foreign_flow_gate,
    )
    assert allow is False
    assert "prior_foreign_net_buy_lt_-25000" in blocks


def test_recent_july_session_live_with_june26_prior():
    flow = {"2026-06-26": 50000.0}
    ctx = resolve_prior_foreign_for_gate(flow, "2026-07-01", max_lag_calendar_days=14)
    assert ctx.gate_mode == "live"
    assert ctx.lag_calendar_days == 5
