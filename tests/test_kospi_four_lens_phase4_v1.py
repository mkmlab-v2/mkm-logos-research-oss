"""Phase-4 KOSPI four-lens GraphRAG: shock fusion walk-forward helpers."""
from __future__ import annotations

from scripts.run_kospi_four_lens_shock_fusion_walkforward_v1 import (
    _needs_conflict_penalty,
    blocked_folds,
    run_shock_fusion_walkforward,
)


def _fixture_eval() -> dict:
    rows = []
    for i, (d, ret, actual, pred) in enumerate(
        [
            ("2026-06-01", 1.0, "bull", "neutral"),
            ("2026-06-02", 0.2, "bull", "bull"),
            ("2026-06-03", -1.0, "bear", "bull"),
            ("2026-06-04", -7.0, "bear", "neutral"),
            ("2026-06-05", 2.0, "bull", "bull"),
            ("2026-06-06", 0.5, "bull", "neutral"),
            ("2026-06-07", -6.5, "bear", "neutral"),
            ("2026-06-08", 8.0, "bull", "bull"),
            ("2026-06-09", -0.5, "bear", "bull"),
            ("2026-06-10", 1.5, "bull", "bull"),
            ("2026-06-11", -5.5, "bear", "neutral"),
            ("2026-06-12", 0.3, "bull", "neutral"),
        ]
    ):
        rows.append(
            {
                "session_date": d,
                "actual_direction": actual,
                "predicted_direction": pred,
                "daily_return_pct": ret,
            }
        )
    return {"rows": rows}


def _fixture_fusion() -> dict:
    return {
        "field": {"direction_sign": "bear", "daily_return_pct": -7.0},
        "lenses": {"logos": {"direction_sign": "bear"}},
        "fusion_resolution": {"conflict_ids": ["field_bear_vs_lens_bull_majority"]},
    }


def test_blocked_folds_splits_dates():
    dates = [f"2026-06-{i:02d}" for i in range(1, 13)]
    folds = blocked_folds(dates, 4)
    assert len(folds) == 3
    train0, test0 = folds[0]
    assert len(train0) == 3
    assert len(test0) == 3
    assert set(train0).isdisjoint(test0)


def test_run_shock_fusion_walkforward_schema_and_arms():
    doc = run_shock_fusion_walkforward(_fixture_eval(), _fixture_fusion(), n_folds=4)
    assert doc["schema"] == "kospi_four_lens_shock_fusion_walkforward_v1"
    assert doc["research_only"] is True
    assert doc["hypothesis_tier"] == "B"
    assert doc["auto_apply"] is False
    assert doc["promotion_ready"] is False
    assert len(doc["folds"]) >= 1
    hold = doc["holdout_pooled"]
    assert "active" in hold
    assert "fusion_shock_only" in hold
    assert "fusion_shock_conflict_penalty" in hold
    assert hold["fusion_shock_only"]["n_scored"] >= 1


def test_conflict_penalty_trigger_on_weak_disagreement():
    fusion = _fixture_fusion()
    assert _needs_conflict_penalty(fusion=fusion, active_pred="bull", fused_pred="bear") is True
    assert _needs_conflict_penalty(fusion=fusion, active_pred="neutral", fused_pred="bear") is False


def test_band_hit_widens_on_scale():
    from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import _band_hit

    row = {"prior_close": 100.0, "actual_close": 101.5}
    cal_row = {
        "kospi_index_prophecy": {
            "predicted_return_band_pct": [-1.0, 1.0],
        }
    }
    assert _band_hit(row, cal_row, band_scale=1.0) is False
    assert _band_hit(row, cal_row, band_scale=2.0) is True


def test_conflict_band_coverage_wf_schema():
    from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import run_conflict_band_coverage_wf

    eval_doc = _fixture_eval()
    calendar = {
        "rows": [
            {
                "session_date": r["session_date"],
                "kospi_index_prophecy": {
                    "predicted_return_band_pct": [-1.0, 1.0],
                },
            }
            for r in eval_doc["rows"]
        ]
    }
    doc = run_conflict_band_coverage_wf(eval_doc, calendar, _fixture_fusion(), n_folds=4)
    assert doc["schema"] == "kospi_four_lens_conflict_band_coverage_wf_v1"
    assert doc["metric_primary"] == "band_hit_rate"
    assert "band_conflict_shock_widen" in doc["holdout_pooled"]
    assert "band_conflict_vol_widen" in doc["holdout_pooled"]
    assert "delta_conflict_vol_widen_minus_active_band_holdout" in doc["comparison"]


def test_promotion_ready_requires_delta_and_n():
    eval_doc = _fixture_eval()
    fusion = _fixture_fusion()
    doc = run_shock_fusion_walkforward(
        eval_doc,
        fusion,
        n_folds=2,
        min_holdout_n=100,
        min_delta_pp=0.03,
    )
    assert doc["promotion_ready"] is False
