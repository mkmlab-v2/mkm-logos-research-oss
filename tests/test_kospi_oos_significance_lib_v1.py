"""KOSPI OOS Wilson / Clopper-Pearson significance appendix."""

from __future__ import annotations

from scripts.kospi_oos_significance_lib_v1 import (
    clopper_pearson_ci,
    metrics_from_eval_rows,
    significance_block,
    wilson_ci,
)


def test_wilson_known_n11_k6():
    lo, hi = wilson_ci(6, 11)
    assert lo < 0.5 < hi
    assert 0.25 < lo < 0.35
    assert 0.75 < hi < 0.85


def test_directional_june_metrics():
    rows = [{"outcome": "HIT"}] * 6 + [{"outcome": "FAIL"}] * 5 + [{"outcome": "NEUTRAL_DRAW"}] * 8
    m = metrics_from_eval_rows(rows)
    assert m["n_scored"] == 19
    assert m["n_directional_bets"] == 11
    assert m["directional_hit_rate"] == 0.5455
    assert m["soft_successes"] == 10.0


def test_significance_rejects_edge_at_n11():
    block = significance_block(label="directional", successes=6.0, n=11)
    assert block["null_inside_wilson_ci"] is True
    assert block["reject_h0_p_equals_null_two_sided_005"] is False


def test_clopper_contains_wilson_center():
    k, n = 6, 11
    w = wilson_ci(k, n)
    c = clopper_pearson_ci(k, n)
    assert c[0] <= w[0] + 0.05
    assert c[1] >= w[1] - 0.05
    assert c[0] < 0.5 < c[1]
