"""Smoke: weekly refresh script exists and references key runners."""
from __future__ import annotations

from pathlib import Path


def test_run_trackb_weekly_refresh_ps1_present():
    root = Path(__file__).resolve().parents[1]
    ps1 = root / "scripts" / "Run-TrackBWeeklyRefresh.ps1"
    assert ps1.is_file()
    text = ps1.read_text(encoding="utf-8")
    assert "run_trackb_weekly_gate_recheck.py" in text
    assert "build_trackb_semantic_eval_by_domain.py" in text
    assert "build_trackb_quaternion_top_combo_ranking.py" in text
    assert "build_trackb_top_combo_fixed_set.py" in text
    assert "run_trackb_top_combo_fixed_set_replay.py" in text
    assert "run_trackb_top_combo_stress_grid.py" in text
    assert "IncludeExtendedStressGrid" in text
    assert "stress_grid_extended_latest.json" in text
    assert "Start-Process" in text
    for name in ("AGENTS.md", "CLAUDE.md"):
        doc = (root / name).read_text(encoding="utf-8")
        assert "Run-TrackBWeeklyRefresh.ps1" in doc, name
