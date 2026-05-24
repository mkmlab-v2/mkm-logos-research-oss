from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "eval_saving_the_news_phase3_truth_gating_v1",
        ROOT / "scripts/eval_saving_the_news_phase3_truth_gating_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_evaluate_combined_when_phase2_and_integrity_ok() -> None:
    mod = _load()
    doc = mod.evaluate(
        phase2_status={"exit_criteria": {"promote_to_phase3": True}},
        matrix={
            "final_action": {"action": "WATCH"},
            "conflict_resolver": {"conflict": False},
            "headline_anchor": {"headline": "test"},
        },
        news_rt={
            "measurement_status": "COMPLETE",
            "observation_row_count": 160,
            "kpi": {"integrity_score": 1.0},
        },
    )
    assert doc["combined_all_passed"] is True
    assert doc["human_signoff_required"] is True
    assert doc["publish_signoff"]["cms_publish_allowed"] is False


def test_evaluate_reject_on_bad_action() -> None:
    mod = _load()
    doc = mod.evaluate(
        phase2_status={"exit_criteria": {"promote_to_phase3": True}},
        matrix={"final_action": {"action": "BUY"}, "conflict_resolver": {"conflict": False}},
        news_rt={"measurement_status": "COMPLETE", "observation_row_count": 160, "kpi": {"integrity_score": 1.0}},
    )
    assert doc["combined_all_passed"] is False
    assert doc["outcome_class"] == "reject"
