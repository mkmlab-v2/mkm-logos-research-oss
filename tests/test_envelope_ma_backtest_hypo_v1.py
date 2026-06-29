# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.btrack_envelope_smct_hypo_lib_v1 import (
    classify_smct_stage,
    envelope_signal,
)


def test_classify_smct_severe_on_broken_trend():
    st = classify_smct_stage(
        rsi=50.0,
        vol_z=0.2,
        sma60_slope=0.01,
        sma120_slope=-0.002,
        drawdown_from_60d_high=-0.05,
    )
    assert st == "severe"


def test_classify_smct_light():
    st = classify_smct_stage(
        rsi=70.0,
        vol_z=1.0,
        sma60_slope=0.01,
        sma120_slope=0.005,
        drawdown_from_60d_high=-0.03,
    )
    assert st == "light"


def test_envelope_arm_a_fires_below_band():
    feat = {"close": 94.0, "sma60": 100.0, "sma60_slope": -0.01, "sma120_slope": 0.01}
    assert envelope_signal("arm_a_naked_60d_6", feat, band_pct=0.06) is True


def test_envelope_arm_b_blocks_downtrend():
    feat = {"close": 94.0, "sma60": 100.0, "sma60_slope": -0.01, "sma120_slope": 0.01}
    assert envelope_signal("arm_b_trend_filtered", feat, band_pct=0.06) is False


def test_aggregate_signal_metrics_pooled():
    from scripts.btrack_envelope_smct_hypo_lib_v1 import aggregate_signal_metrics

    pooled = aggregate_signal_metrics(
        [
            {"metrics": {"directional_hits": 2, "n_directional_next_day": 3, "n_entry_signals": 4, "n_eval_days": 10}},
            {"metrics": {"directional_hits": 1, "n_directional_next_day": 1, "n_entry_signals": 1, "n_eval_days": 10}},
        ]
    )
    assert pooled["directional_hit_rate_raw"] == round(3 / 4, 6)
    assert pooled["n_entry_signals"] == 5


def test_envelope_trend_gate_v1_allows_uptrend_dip():
    from scripts.btrack_envelope_smct_hypo_lib_v1 import envelope_trend_gate_v1

    assert envelope_trend_gate_v1(sma120_slope=0.01, drawdown_from_60d_high=-0.08) is True
    assert envelope_trend_gate_v1(sma120_slope=-0.01, drawdown_from_60d_high=-0.08) is False
    assert envelope_trend_gate_v1(sma120_slope=0.01, drawdown_from_60d_high=-0.20) is False


def test_eval_entry_respects_explicit_subset_mode():
    from scripts.btrack_envelope_smct_hypo_lib_v1 import (
        SUBSET_ENVELOPE_TREND_GATE_V1,
        SUBSET_LEGACY_LIGHT_MEDIUM,
        eval_entry_directional_hits,
    )

    features = {
        "2026-01-02": {
            "close": 94.0,
            "sma60": 100.0,
            "sma60_slope": 0.01,
            "sma120_slope": 0.01,
            "smct_subset_allow_envelope": False,
            "envelope_trend_gate_v1": True,
        },
        "2026-01-03": {"close": 96.0},
    }
    full = eval_entry_directional_hits(
        features,
        ["2026-01-02"],
        arm_id="arm_a_naked_60d_6",
        subset_only=False,
    )
    legacy = eval_entry_directional_hits(
        features,
        ["2026-01-02"],
        arm_id="arm_a_naked_60d_6",
        subset_mode=SUBSET_LEGACY_LIGHT_MEDIUM,
    )
    trend = eval_entry_directional_hits(
        features,
        ["2026-01-02"],
        arm_id="arm_a_naked_60d_6",
        subset_mode=SUBSET_ENVELOPE_TREND_GATE_V1,
    )
    assert full["n_entry_signals"] == 1
    assert legacy["n_entry_signals"] == 0
    assert legacy["n_signals_gated_out_by_subset"] == 1
    assert trend["n_entry_signals"] == 1


def test_summarize_severe_knife_signals():
    from scripts.btrack_envelope_smct_hypo_lib_v1 import summarize_severe_knife_signals

    per_signal = [
        {"smct_stage": "severe", "actual_direction": "bear", "hit": False, "signal_date": "2026-01-01"},
        {"smct_stage": "severe", "actual_direction": "bull", "hit": True, "signal_date": "2026-01-02"},
        {"smct_stage": "none", "actual_direction": "bull", "hit": True, "signal_date": "2026-01-03"},
    ]
    out = summarize_severe_knife_signals(per_signal)
    assert out["n_signals_total"] == 3
    assert out["n_severe"] == 2
    assert out["n_severe_bear_next_day"] == 1
    assert out["severe_bear_rate"] == 0.5
    assert out["severe_directional_hit_rate_raw"] == 0.5


def test_build_envelope_benchmark_closure_smoke(tmp_path):
    root = Path(__file__).resolve().parents[1]
    tier1 = {
        "mkm_frozen_kospi_leg": {"directional_hit_rate_raw": 0.572222, "oper_score_generated_at_utc": "2026-06-12T13:13:33Z"},
        "envelope_arms_vs_mkm": [
            {
                "arm_id": "arm_c_120d_up_60d_pullback",
                "scope": "full_180d",
                "envelope": {"raw": {"directional_hit_rate": 0.666667, "n_entry_signals": 3}},
                "delta": {"directional_hit_rate_pp_envelope_minus_mkm": 9.444},
            }
        ],
    }
    tier2 = {
        "envelope_equity_pooled_vs_mkm": [
            {
                "arm_id": "arm_a_naked_60d_6",
                "scope": "pooled_full",
                "envelope_pooled": {"raw": {"directional_hit_rate": 0.628205, "n_entry_signals": 79}},
                "delta_pp_envelope_minus_mkm": 5.598,
            },
            {
                "arm_id": "arm_a_naked_60d_6",
                "scope": "pooled_envelope_trend_gate_v1",
                "envelope_pooled": {"raw": {"n_entry_signals": 0}},
            },
            {
                "arm_id": "arm_c_120d_up_60d_pullback",
                "scope": "pooled_full",
                "delta_pp_envelope_minus_mkm": -8.527,
            },
            {
                "arm_id": "arm_c_120d_up_60d_pullback",
                "scope": "pooled_envelope_trend_gate_v1",
                "envelope_pooled": {"raw": {"directional_hit_rate": 0.514286}},
                "delta_pp_envelope_minus_mkm": -5.794,
            },
        ]
    }
    knife = {
        "eval_window": {"date_from": "2025-09-10", "date_to": "2026-06-11", "n_trading_days": 180},
        "by_arm": {
            "arm_a_naked_60d_6": {
                "pooled_severe_knife": {
                    "n_signals_total": 78,
                    "severe_fraction_of_signals": 1.0,
                    "severe_bear_rate": 0.371795,
                }
            }
        },
    }
    t1 = tmp_path / "t1.json"
    t2 = tmp_path / "t2.json"
    kn = tmp_path / "knife.json"
    out = tmp_path / "closure.json"
    t1.write_text(json.dumps(tier1), encoding="utf-8")
    t2.write_text(json.dumps(tier2), encoding="utf-8")
    kn.write_text(json.dumps(knife), encoding="utf-8")

    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/build_btrack_envelope_benchmark_closure_v1.py"),
            "--tier1-dual",
            str(t1),
            "--tier2-dual",
            str(t2),
            "--knife-json",
            str(kn),
            "--output",
            str(out),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"
    assert doc["decision_tree_outcome"]["branch_id"] == "similar_or_incomparable_within_ci"
