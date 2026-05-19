"""Holdout7 price-lens CF summary contract."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    path = ROOT / "scripts/build_btrack_holdout_price_lens_cf_holdout7_v1.py"
    spec = importlib.util.spec_from_file_location("hcf", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_build_report_bear_fix_zero_and_gate_pointer():
    mod = _load_mod()
    cf = json.loads(
        (ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf

    holdout = holdout_dates_from_cf(
        ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
    )
    report = mod.build_report(cf=cf, gate=None, oos=None, holdout=holdout)
    assert report["findings"]["price_lens_cf_bear_fix_on_holdout7"] == 0
    assert report["findings"]["price_lens_cf_any_would_fix_wrong_dir"] == 0
    assert len(report["per_day"]) == 7
    assert any("[MKM-HOLDOUT-CF]" in line for line in report["operator_lines"])
    assert any("[MKM-HOLDOUT-GATE]" in line for line in report["operator_lines"])
    assert report["verdict"]["promote_price_lens_blend_to_prod"] is False


def test_panel_script_reads_holdout_gate_artifacts():
    text = (ROOT / "scripts/Check-ProphecyPanel24hAlerts.ps1").read_text(encoding="utf-8")
    assert "btrack_holdout_gate_candidate_v1_latest.json" in text
    assert "btrack_holdout_gate_oos_180d_v1_latest.json" in text
    assert "btrack_holdout_price_lens_cf_holdout7_v1_latest.json" in text
