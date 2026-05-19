"""Smoke: weekly Phase3 entry script exists and delegates to daily chain."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_weekly_phase3_script_exists() -> None:
    p = ROOT / "scripts/run_prophecy_sandbox_weekly_phase3_v1.py"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "run_prophecy_sandbox_daily_chain_v1.py" in text
    assert "--refresh-phase3-binance" in text
