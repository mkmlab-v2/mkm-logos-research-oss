"""Conformal param sweep + premium field band attach."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="multi-month panel missing",
)
def test_conformal_sweep_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_conformal_param_sweep_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((ROOT / "reports/kospi_field_band_conformal_param_sweep_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "kospi_field_band_conformal_param_sweep_v1"
    assert len(doc.get("grid_rows_rwc") or []) >= 1


def test_render_field_band_stack_md():
    from scripts.build_premium_btrack_multilens_report_v1 import render_field_band_stack_md

    md = render_field_band_stack_md(
        {
            "stack": {
                "holdout_band_base": 0.48,
                "holdout_band_rwc": 0.61,
                "holdout_band_stack_union": 0.65,
                "best_band_layer": "stack_union",
            }
        }
    )
    assert "stack_union" in md
    assert "[HYPO]" in md


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_stack_compare_v1_latest.json").is_file(),
    reason="stack compare missing",
)
def test_premium_best_effort_includes_field_band_section():
    cp = subprocess.run(
        [
            PY,
            "scripts/build_premium_btrack_multilens_report_v1.py",
            "--mode",
            "best-effort",
            "--no-validate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    md = (ROOT / "reports/premium_btrack_multilens_report_v1.md").read_text(encoding="utf-8")
    assert "Field band conformal stack" in md
