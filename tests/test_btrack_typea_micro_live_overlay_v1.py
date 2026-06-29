"""Tests for btrack_typea_micro_live_overlay_v1."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BT = ROOT / "projects" / "bitcoin-trading"
if str(BT) not in sys.path:
    sys.path.insert(0, str(BT))

from src.futures_engine.btrack_typea_micro_live_overlay_v1 import (  # noqa: E402
    BtrackMicroLiveOverlay,
    load_btrack_micro_live_overlay,
    order_qty_from_overlay,
    resolve_workspace_root,
)


def test_overlay_allows_aligned_sides() -> None:
    ov = BtrackMicroLiveOverlay(
        active=True,
        mode="filter",
        side_hint="SELL",
        eval_date="2026-05-29",
        size_usd=35.0,
        max_position_size=0.06,
        status="READY_FOR_ENGINE_SUBMIT",
        source_path="/tmp/x.json",
    )
    ok, reason = ov.allows_aroon_target("SHORT")
    assert ok is True
    assert reason == "aligned_bear"
    bad, reason2 = ov.allows_aroon_target("LONG")
    assert bad is False
    assert "conflict" in reason2


def test_order_qty_cap() -> None:
    ov = BtrackMicroLiveOverlay(
        active=True,
        mode="filter",
        side_hint="SELL",
        eval_date="2026-05-29",
        size_usd=35.0,
        max_position_size=0.06,
        status="READY",
        source_path=None,
    )
    qty = order_qty_from_overlay(ov, default_qty=0.01, mark_price=70000.0)
    assert qty <= 0.01
    assert qty >= 0.001


def test_load_overlay_from_workspace() -> None:
    ws = resolve_workspace_root(Path(__file__))
    ov = load_btrack_micro_live_overlay(workspace_root=ws, force_refresh=True)
    assert isinstance(ov.active, bool)
    assert ov.mode == "filter"
