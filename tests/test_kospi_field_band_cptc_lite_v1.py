"""CPTC-lite + FinStressTS + HD auto chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_cptc_change_point_detect():
    from scripts.run_kospi_field_band_cptc_lite_v1 import _is_change_point

    assert _is_change_point(shock_day=True, prev_shock=False, vol_jump=None, vol_jump_threshold=1.75, conflict=False, prev_conflict=False)
    assert not _is_change_point(shock_day=True, prev_shock=True, vol_jump=None, vol_jump_threshold=1.75, conflict=False, prev_conflict=False)
    assert _is_change_point(shock_day=False, prev_shock=False, vol_jump=2.0, vol_jump_threshold=1.75, conflict=False, prev_conflict=False)


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_cptc_lite_runs():
    from scripts.run_kospi_field_band_cptc_lite_v1 import run_cptc_lite
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    ev = _read(ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json")
    cal = _read(ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json")
    fusion = _read(ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json")
    if not all((ev, cal, fusion)):
        pytest.skip("inputs missing")
    doc = run_cptc_lite(ev, cal, fusion)
    assert doc["direction_unchanged"] is True
    assert int((doc.get("summary") or {}).get("holdout_pooled", {}).get("n_scored") or 0) >= 30


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_finstress_diagnostic_runs():
    from scripts.run_kospi_finstress_ts_diagnostic_v1 import run_finstress_diagnostic
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    ev = _read(ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json")
    fusion = _read(ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json")
    if not ev or not fusion:
        pytest.skip("inputs missing")
    doc = run_finstress_diagnostic(ev, fusion)
    assert doc["diagnostic_only"] is True
    assert doc["promotion_candidate"] is False
    assert doc.get("recommendation")


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_hd_auto_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_hd_auto_chain_v1.py", "--skip-extended-oos", "--skip-panel-build"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    completion = json.loads((ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert completion["quality_ok"] is True
    stack = json.loads((ROOT / "reports/kospi_field_band_stack_compare_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert stack["stack"]["holdout_band_base"] is not None
