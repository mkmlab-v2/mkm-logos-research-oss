"""Smoke: min_conf experiment report builder (no subprocess)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.run_btrack_min_conf_experiment_v1 import (
    build_comparison,
    build_grid_report,
    parse_threshold_grid,
    _metrics_slice,
)


def test_build_comparison_delta(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline_eval.json"
    baseline_path.write_text(
        """{
  "metrics": {
    "price_directional_hit_rate": 0.233333,
    "price_hit_rate_on_directional_calls": 0.538462,
    "n_directional_calls": 13,
    "n_neutral_predictions": 17,
    "n_evaluated": 30,
    "price_hits": 7,
    "directional_call_hits": 7
  }
}""",
        encoding="utf-8",
    )
    candidate = {
        "min_direction_confidence": 0.18,
        "paths": {},
        "metrics": {
            "price_directional_hit_rate": 0.30,
            "price_hit_rate_on_directional_calls": 0.50,
            "n_directional_calls": 18,
            "n_neutral_predictions": 12,
            "n_evaluated": 30,
            "price_hits": 9,
            "directional_call_hits": 9,
        },
        "neutral_attribution_summary": {},
    }
    report = build_comparison(
        baseline_path,
        candidate,
        production_threshold=0.25,
    )
    assert report["delta_candidate_minus_baseline"]["n_directional_calls"] == 5
    assert report["candidate"]["min_direction_confidence"] == 0.18
    assert report["alert_policy_preview"]["ALERT_1b_directional_skill"]["informational_only"] is True
    assert report["operator_lines"]


def test_parse_threshold_grid() -> None:
    assert parse_threshold_grid("0.18,0.20,0.22") == [0.18, 0.2, 0.22]


def test_build_grid_report_picks_best(tmp_path: Path) -> None:
    baseline_path = tmp_path / "b.json"
    baseline_path.write_text(
        '{"metrics": {"price_directional_hit_rate": 0.23, '
        '"price_hit_rate_on_directional_calls": 0.54, "n_directional_calls": 13, '
        '"n_neutral_predictions": 17}}',
        encoding="utf-8",
    )
    candidates = [
        {
            "min_direction_confidence": 0.18,
            "metrics": {
                "price_directional_hit_rate": 0.37,
                "price_hit_rate_on_directional_calls": 0.61,
                "n_directional_calls": 18,
                "n_neutral_predictions": 12,
            },
        },
        {
            "min_direction_confidence": 0.22,
            "metrics": {
                "price_directional_hit_rate": 0.30,
                "price_hit_rate_on_directional_calls": 0.55,
                "n_directional_calls": 15,
                "n_neutral_predictions": 15,
            },
        },
    ]
    grid = build_grid_report(baseline_path, candidates)
    assert grid["best_by_all_rows_hit_rate"] == 0.18
    assert len(grid["operator_lines"]) >= 3
