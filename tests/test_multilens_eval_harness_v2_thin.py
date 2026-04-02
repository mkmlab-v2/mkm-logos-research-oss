"""Thin V2 multilens eval harness: template report structure."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCR = _ROOT / "scripts" / "eval_multilens_harness_v2_thin.py"


def _load():
    spec = importlib.util.spec_from_file_location("eval_multilens_harness_v2_thin", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_report_has_ten_rows_and_slots() -> None:
    r = mod.run_thin_harness(_ROOT)
    assert r["schema"] == "multilens_eval_v2_thin_report_v1"
    assert r.get("dataset_intent") == "repro_bench_grid_v1"
    assert isinstance(r.get("dataset_intent_note"), str) and r["dataset_intent_note"]
    assert r["row_count"] == 10
    first = r["rows"][0]
    assert "lens_outputs" in first
    assert set(first["lens_outputs"].keys()) == {
        "logos_dual_regime",
        "myeongni_b_track",
        "sasang_b_track",
    }


def test_populate_default_samples_fills_matching_dates() -> None:
    r = mod.run_thin_harness(_ROOT, populate_default_samples=True)
    by_date = {row["calendar_date"]: row["lens_outputs"] for row in r["rows"]}
    assert by_date["2022-05-09"]["sasang_b_track"]["regime_hypothesis"] == "phase_transition"
    assert by_date["2022-05-09"]["myeongni_b_track"]["state_id"] == 9
    assert by_date["2023-01-15"]["sasang_b_track"]["regime_hypothesis"] == "neutral"
    assert by_date["2023-01-15"]["myeongni_b_track"]["state_id"] == 3
    assert "populate_meta" in r
    lg = by_date["2022-05-09"]["logos_dual_regime"]
    assert lg is not None
    assert "risk_multiplier_cap" in lg
    assert isinstance(lg["risk_multiplier_cap"], (int, float))
    assert lg.get("inputs_ref") == "dual_regime_curated_overlap_v1"
    assert "summary" in r
    s = r["summary"]
    assert s["total_rows"] == 10
    assert s["fully_populated_rows"] == 10
    assert s["risk_multiplier_cap_stats"]["n"] == 10
    mt = s["mapping_target_sasang_myeongni"]
    assert mt["rows_with_both"] == 10
    assert mt["agreement_count"] == 10
    assert mt["agreement_rate"] == 1.0


def test_populate_covers_all_ten_dates() -> None:
    r = mod.run_thin_harness(_ROOT, populate_default_samples=True)
    for row in r["rows"]:
        lo = row["lens_outputs"]
        assert lo["sasang_b_track"] is not None, row["calendar_date"]
        assert lo["myeongni_b_track"] is not None, row["calendar_date"]
        assert lo["logos_dual_regime"] is not None, row["calendar_date"]
