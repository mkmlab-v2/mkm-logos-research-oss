"""Tests for dual-path conflict shadow router."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.kospi_dual_path_conflict_shadow_lib_v1 import (
    detect_macro_bear_session_bull_trap,
    detect_momentum_perdate_bull_conflict,
    dual_path_direction,
    should_apply_tier_a_bear_rescue,
)
from scripts.kospi_lens_per_date_static_v1 import load_per_date_lens_bundle, per_date_lenses_for_session
from scripts.kospi_lens_per_date_static_v1 import load_lens_jsonl_by_day, static_lenses_for_eval_date
from scripts.kospi_june2026_multilens_blend_v1 import load_static_lenses


def test_detect_conflict_2026_06_26() -> None:
    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    row = next(r for r in cal["rows"] if r["session_date"] == "2026-06-26")
    my_by, sa_by, _ = load_lens_jsonl_by_day(
        Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
    )
    per_static = static_lenses_for_eval_date(
        "2026-06-26", sasang_by_day=sa_by, myeongni_by_day=my_by, baseline=load_static_lenses()
    )
    ok, reasons = detect_momentum_perdate_bull_conflict(row, per_static, active_direction="bull")
    assert ok is True
    assert "momentum_bear" in reasons
    assert "per_date_bull_consensus" in reasons


def test_dual_path_routes_bear_on_conflict() -> None:
    assert (
        dual_path_direction(
            conflict=True,
            per_date_active_dir="bull",
            static_bear_triple_dir="bear",
        )
        == "bear"
    )
    assert (
        dual_path_direction(
            conflict=False,
            per_date_active_dir="bear",
            static_bear_triple_dir="bull",
        )
        == "bear"
    )


def test_detect_macro_bear_session_bull_trap_2026_06_19() -> None:
    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    row = next(r for r in cal["rows"] if r["session_date"] == "2026-06-19")
    my_by, sa_by, macro_by, _ = load_per_date_lens_bundle(
        Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
    )
    per = per_date_lenses_for_session(
        "2026-06-19",
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        macro_gate_by_day=macro_by,
    )
    ok, reasons = detect_macro_bear_session_bull_trap(row, per, active_direction="bull")
    assert ok is True
    assert "per_date_macro_bear" in reasons


def test_tier_a_guard_skips_weak_foreign_2026_06_09() -> None:
    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    row = next(r for r in cal["rows"] if r["session_date"] == "2026-06-09")
    my_by, sa_by, macro_by, _ = load_per_date_lens_bundle(
        Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
    )
    per = per_date_lenses_for_session(
        "2026-06-09",
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        macro_gate_by_day=macro_by,
    )
    tier_a, _ = detect_momentum_perdate_bull_conflict(row, per, active_direction="bull")
    apply, codes = should_apply_tier_a_bear_rescue(tier_a_conflict=tier_a, prior_foreign_net_buy=-2644.35)
    assert tier_a is True
    assert apply is False
    assert "foreign_flow_weak_guard" in codes


def test_build_shadow_june_exit_0() -> None:
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
            "--year-month",
            "2026-06",
            "--as-of-kst",
            "2026-06-26",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr[-500:]
