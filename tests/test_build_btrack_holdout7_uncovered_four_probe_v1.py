"""Uncovered four holdout7 probe."""
from __future__ import annotations

from scripts.build_btrack_holdout7_uncovered_four_probe_v1 import (
    PROBE_LAYERS,
    _prepare_rows,
    _probe_holdout7,
    match_probe_when,
)


def test_union_rule_covers_seven_wrong_days() -> None:
    holdout = [
        "2026-04-02",
        "2026-04-08",
        "2026-04-14",
        "2026-04-24",
        "2026-04-27",
        "2026-05-07",
        "2026-05-11",
    ]
    by_date = {}
    for ed in holdout:
        ovn = -0.0001 if ed in ("2026-04-02", "2026-04-14", "2026-04-24") else 0.0001
        prp = 0.31 if ed == "2026-04-02" else 0.85
        by_date[ed] = {
            "eval_date": ed,
            "instrument": "btc",
            "predicted_direction": "bull",
            "preliminary_direction": "bull",
            "actual_direction": "bear",
            "is_holdout_7": True,
            "is_wrong_direction": True,
            "overnight_return": ovn,
            "prior_range_position": prp,
        }
    layer = next(l for l in PROBE_LAYERS if l["slug"] == "holdout_union_ovn_neg_or_pr_high")
    res = _probe_holdout7(layer, by_date, holdout)
    assert res["n_holdout7_wrong_neutralized"] == 7
    assert res["n_uncovered_four_hit"] == 4


def test_match_overnight_positive() -> None:
    row = {
        "is_holdout_7": True,
        "preliminary_direction": "bull",
        "overnight_return": 0.001,
        "prior_range_position": 0.5,
    }
    layer = next(l for l in PROBE_LAYERS if l["slug"] == "holdout_ovn_pos_bull")
    assert match_probe_when(row, layer["apply_when"]) is True
