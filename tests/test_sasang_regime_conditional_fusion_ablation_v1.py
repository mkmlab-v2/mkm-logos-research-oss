"""Smoke tests for sasang regime conditional fusion ablation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    daily_fusion_posture,
    apply_geumhwa_min_days_gate,
)


def test_daily_fusion_posture_split_holds_through_veto() -> None:
    posture, in_mkt = daily_fusion_posture(
        veto=True, supplier_tight=True, in_market=True, policy="regime_mkm_split_tactical"
    )
    assert posture == "HOLD_THROUGH_VETO"
    assert in_mkt is True


def test_daily_fusion_posture_literal_exits_on_veto() -> None:
    posture, in_mkt = daily_fusion_posture(
        veto=True, supplier_tight=True, in_market=True, policy="literal_veto_hold"
    )
    assert posture == "HOLD_CASH_OR_EXIT"
    assert in_mkt is False


def test_geumhwa_gate_requires_streak() -> None:
    dates = [f"2026-01-{i:02d}" for i in range(2, 8)]
    raw = {d: True for d in dates[:3]} | {d: False for d in dates[3:]}
    gated = apply_geumhwa_min_days_gate(raw, dates, min_consecutive=5)
    assert gated[dates[2]] is False
    raw2 = {d: True for d in dates}
    gated2 = apply_geumhwa_min_days_gate(raw2, dates, min_consecutive=5)
    assert gated2[dates[4]] is True
    assert gated2[dates[3]] is False
