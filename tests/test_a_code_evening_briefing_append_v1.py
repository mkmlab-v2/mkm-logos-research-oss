"""RQ-028 evening briefing append helper tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/a_code_evening_briefing_append_v1.py"
OBS = ROOT / "reports/a_code_governor_knob_evening_observation_v1_latest.json"


def _load_helper():
    spec = importlib.util.spec_from_file_location("a_code_append", HELPER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_governor_telegram_append_line_from_latest() -> None:
    if not OBS.is_file():
        pytest.skip("evening observation missing")
    mod = _load_helper()
    line = mod.governor_telegram_append_line()
    assert line
    assert "[HYPO" in line


def test_missing_obs_returns_none(tmp_path: Path) -> None:
    mod = _load_helper()
    assert mod.governor_telegram_append_line(tmp_path / "missing.json") is None


def test_gate_summary_line_from_latest() -> None:
    gate = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"
    if not gate.is_file():
        pytest.skip("promotion gate missing")
    mod = _load_helper()
    line = mod.governor_gate_summary_line()
    assert line
    assert "관측 지속" in line or "연구 유지" in line
    assert "A-code 게이트" in line


def test_koreanize_evening_ops_line() -> None:
    mod = _load_helper()
    raw = "▸ A-code gate [HYPO·non-gating]: WATCH_CONTINUE · holdout_consistency=1"
    out = mod.koreanize_evening_ops_line(raw)
    assert "관측 지속" in out
    assert "홀드아웃 일치=" in out
    assert "HYPO" not in out
