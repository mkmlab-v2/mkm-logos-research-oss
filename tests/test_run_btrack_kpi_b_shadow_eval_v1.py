"""Tests for KPI-B shadow eval runner."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operator_lines_shape() -> None:
    path = ROOT / "scripts/run_btrack_kpi_b_shadow_eval_v1.py"
    spec = importlib.util.spec_from_file_location("run_btrack_kpi_b_shadow_eval_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    assert mod.DEFAULT_EVAL_OUT.name == "prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"
    assert mod.DEFAULT_SCORE_OUT.name == "btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
