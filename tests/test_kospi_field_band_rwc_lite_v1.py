"""RWC-lite conformal band margin PoC."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_weighted_quantile_monotone():
    from scripts.run_kospi_field_band_rwc_lite_v1 import _weighted_quantile

    vals = [0.0, 1.0, 2.0, 5.0]
    w = [1.0, 1.0, 1.0, 1.0]
    q90 = _weighted_quantile(vals, w, 0.9)
    assert q90 >= 2.0


def test_outside_distance_zero_when_inside():
    from scripts.run_kospi_field_band_rwc_lite_v1 import _outside_distance_pct

    row = {"prior_close": 1000.0, "actual_close": 1010.0}
    cal = {"kospi_index_prophecy": {"predicted_return_band_pct": [-2.0, 2.0]}}
    assert _outside_distance_pct(row, cal, band_scale=1.0) == 0.0


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_rwc_lite_holdout_improves_or_runs():
    from scripts.run_kospi_field_band_rwc_lite_v1 import run_rwc_lite
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    ev = _read(ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json")
    cal = _read(ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json")
    fusion = _read(ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json")
    if not all((ev, cal, fusion)):
        pytest.skip("inputs missing")
    doc = run_rwc_lite(ev, cal, fusion, field_tier2=_read(ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"))
    hold = doc["summary"]["holdout_pooled"]
    assert hold["n_scored"] >= 30
    assert doc["direction_unchanged"] is True
    delta = doc["summary"]["delta_rwc_minus_base_holdout"]
    assert delta is not None


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_rwc_lite_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_rwc_lite_chain_v1.py", "--skip-extended-oos"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    completion = json.loads((ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert completion["quality_ok"] is True
