"""Tests for btrack_typea_micro_live_guard_v1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BT = ROOT / "projects" / "bitcoin-trading"
if str(BT) not in sys.path:
    sys.path.insert(0, str(BT))

from src.futures_engine.btrack_typea_micro_live_guard_v1 import (  # noqa: E402
    MicroLiveGuard,
    MicroLivePolicyLimits,
    cap_qty_by_policy,
    load_micro_live_policy,
    _utc_date,
)


class _FakeBinance:
    def __init__(self, *, total: float = 1000.0, fills: list | None = None) -> None:
        self.total = total
        self.fills = fills or []

    def get_balance(self) -> dict:
        return {"total": self.total, "USDT": self.total}

    def get_recent_fills(self, symbol: str = "BTCUSDT", limit: int = 50) -> list:
        return self.fills


def test_load_policy_from_workspace() -> None:
    p = load_micro_live_policy(workspace_root=ROOT)
    assert p is not None
    assert p.max_trades_per_day >= 1
    assert p.max_daily_loss_pct > 0


def test_guard_blocks_max_trades(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    guard = MicroLiveGuard(project_root=tmp_path, workspace_root=ROOT)
    policy = MicroLivePolicyLimits(
        max_trades_per_day=2,
        max_daily_loss_pct=2.0,
        max_drawdown_pct=3.0,
        max_consecutive_losses=4,
        max_position_size=0.06,
        size_usd=35.0,
    )
    guard._state.update(
        utc_date=_utc_date(),
        entries_today=2,
        day_start_equity=1000.0,
        peak_equity=1000.0,
        paused=False,
    )
    # monkeypatch policy load via overlay path - check_before_entry loads policy from workspace
    ok, reason = guard.check_before_entry(True, _FakeBinance(), "BTCUSDT", fallback_equity=1000.0)
    # If workspace policy max_trades is 4, entries_today=2 should pass; force paused via entries>=policy
    guard._state["entries_today"] = 999
    ok2, reason2 = guard.check_before_entry(True, _FakeBinance(), "BTCUSDT", fallback_equity=1000.0)
    assert ok2 is False
    assert "max_trades_per_day" in reason2


def test_guard_blocks_daily_loss(tmp_path: Path) -> None:
    guard = MicroLiveGuard(project_root=tmp_path, workspace_root=ROOT)
    guard._state.update(
        utc_date=_utc_date(),
        entries_today=0,
        day_start_equity=1000.0,
        peak_equity=1000.0,
        paused=False,
    )
    ok, reason = guard.check_before_entry(
        True,
        _FakeBinance(total=970.0),
        "BTCUSDT",
        fallback_equity=1000.0,
    )
    # 3% loss vs default policy 2% daily cap
    if load_micro_live_policy(workspace_root=ROOT) is not None:
        assert ok is False
        assert "daily_loss_pct" in reason


def test_cap_qty_by_policy() -> None:
    policy = MicroLivePolicyLimits(
        max_trades_per_day=4,
        max_daily_loss_pct=2.0,
        max_drawdown_pct=3.0,
        max_consecutive_losses=4,
        max_position_size=0.06,
        size_usd=35.0,
    )
    qty = cap_qty_by_policy(0.01, mark_price=70000.0, equity=1000.0, policy=policy, overlay_size_usd=35.0)
    cap = min(0.01, 35.0 / 70000.0, (1000.0 * 0.06) / 70000.0)
    assert qty == max(0.001, cap)
