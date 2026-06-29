from __future__ import annotations

from scripts.prophecy_micro_oscillator_lib_v1 import (
    apply_micro_tiebreak,
    combo_score_is_ambiguous,
    micro_oscillator_sign,
    micro_trigger_allows_apply,
)


def test_micro_mom_ret1_bull_prefers_lagged() -> None:
    assert micro_oscillator_sign({"ret_1_lagged": 0.02, "ret_1": -0.5}, "mom_ret1", dz=0.0) == 1


def test_micro_revert_ret1_bear_on_positive_ret() -> None:
    assert micro_oscillator_sign({"ret_1": 0.02}, "revert_ret1", dz=0.0) == -1


def test_apply_only_on_neutral() -> None:
    row = {"instrument": "kospi", "eval_date": "2026-01-02"}
    kf = {"2026-01-02": {"ret_1": 0.03, "ret_3": 0.01, "vol_3": 0.01, "vol_10": 0.005}}
    pred, applied = apply_micro_tiebreak(
        "bull",
        row,
        kf,
        {},
        mode="mom_ret1",
        only_neutral=True,
    )
    assert pred == "bull"
    assert applied is False

    pred2, applied2 = apply_micro_tiebreak(
        "neutral",
        row,
        kf,
        {},
        mode="mom_ret1",
        only_neutral=True,
    )
    assert pred2 == "bull"
    assert applied2 is True


def test_combo_score_ambiguous_inside_band() -> None:
    assert combo_score_is_ambiguous(0.0, up_thr=0.5, down_thr=-0.5) is True
    assert combo_score_is_ambiguous(0.6, up_thr=0.5, down_thr=-0.5, margin=0.15) is True
    assert combo_score_is_ambiguous(2.0, up_thr=0.5, down_thr=-0.5) is False


def test_ambiguous_trigger_applies_on_weak_bull() -> None:
    row = {"instrument": "kospi", "eval_date": "2026-01-02"}
    kf = {"2026-01-02": {"ret_1_lagged": -0.02, "ret_3": -0.01, "vol_3": 0.01, "vol_10": 0.005}}
    assert micro_trigger_allows_apply(
        "ambiguous",
        base_pred="bull",
        combo_score=0.55,
        up_thr=0.5,
        down_thr=-0.5,
        ambiguous_margin=0.1,
    )
    pred, applied = apply_micro_tiebreak(
        "bull",
        row,
        kf,
        {},
        mode="revert_ret1",
        trigger="ambiguous",
        combo_score=0.55,
        up_thr=0.5,
        down_thr=-0.5,
        ambiguous_margin=0.1,
    )
    assert applied is True
    assert pred == "bull"  # revert of negative lagged ret1 -> bull
