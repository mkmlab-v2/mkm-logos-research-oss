"""Tests for holdout gate 180d OOS eval (wrong_dir cohort path)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_mod():
    path = ROOT / "scripts/build_btrack_holdout_gate_oos_180d_eval_v1.py"
    spec = importlib.util.spec_from_file_location("oos180", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_wrong_dir_cohort_holdout7_all_neutralized():
    mod = _load_mod()
    manifest = json.loads(
        (ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json").read_text(encoding="utf-8")
    )
    layer = mod._candidate_layer(manifest)
    per = json.loads(
        (ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    dump = json.loads(
        (ROOT / "reports/btrack_wrong_dir_holdout_features_180d_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    from scripts.btrack_wrong_dir_holdout_core_v1 import (
        holdout_dates_from_cf,
        wrong_dir_cohort_with_auxiliary,
    )

    holdout = holdout_dates_from_cf(ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json")
    hwd = wrong_dir_cohort_with_auxiliary(per, dump, holdout, layer, holdout_only=True)
    assert hwd["n_wrong_dir_days"] == 7
    assert hwd["neutralized"] == 7
    assert hwd["bear_fix"] == 0
