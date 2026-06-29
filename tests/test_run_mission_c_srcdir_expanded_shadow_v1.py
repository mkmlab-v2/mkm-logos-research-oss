"""Tests for Mission C srcdir+expanded shadow runner."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shadow_paths_reports_only() -> None:
    path = ROOT / "scripts/run_mission_c_srcdir_expanded_shadow_v1.py"
    spec = importlib.util.spec_from_file_location("run_mission_c_srcdir_expanded_shadow_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    assert "docs/final/artifacts/btrack_prophecy_score_latest.json" not in str(mod.DEFAULT_SCORE_OUT)
    assert mod.DEFAULT_SCORE_OUT.parent.name == "reports"
    assert mod.DEFAULT_STREAK.name == "prophecy_promotion_strict_streak_mission_c_shadow_v1.json"
