"""RQ-024 BTC lens causal feature v0 smoke tests."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_causal_feature_map_smoke():
    from scripts.btrack_causal_ohlc_features_v1 import build_causal_feature_map, load_btc_ohlc_by_date

    csv = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not csv.is_file():
        return
    ohlc = load_btc_ohlc_by_date(csv)
    feat = build_causal_feature_map(ohlc)
    assert feat
    sample = next(iter(feat.values()))
    assert "overnight_return" in sample
    assert "prior_range_position" in sample
    assert "vol_regime_high" in sample
    assert "volume_ratio_5d" in sample
    assert "prior_intraday_range" in sample


def test_rq024_v2_overlay_smoke():
    from scripts.rq024_btc_lens_feature_v0_lib import (
        acc_with_causal_overlay_v2,
        best_causal_weights_v2_on_train,
        causal_feature_map,
    )

    csv = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not csv.is_file():
        return
    causal = causal_feature_map(csv)
    rows = [
        {
            "eval_date": d,
            "instrument": "btc",
            "actual_direction": "bull",
            "macro_score": 0.1,
            "source_direction": "bull",
        }
        for d in sorted(causal.keys())[-40:]
    ]
    params = (0.01, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    w, _ = best_causal_weights_v2_on_train(
        rows[:20],
        params,
        {},
        {},
        {},
        {},
        causal,
        include_source_direction_signal=True,
        train_objective="margin_vs_bull",
    )
    assert len(w) == 7
    acc, hits = acc_with_causal_overlay_v2(
        rows[20:],
        params,
        {},
        {},
        {},
        {},
        causal,
        include_source_direction_signal=True,
        causal_weights=w,
    )
    assert 0.0 <= acc <= 1.0
    assert hits >= 0


def test_rq024_multisplit_script_import():
    from scripts.run_rq024_btc_lens_feature_v0_multisplit_v1 import SCHEMA

    assert SCHEMA == "rq024_btc_lens_feature_v0_multisplit_v1"


def test_rq024_v1_overlay_smoke():
    from scripts.rq024_btc_lens_feature_v0_lib import (
        acc_with_causal_overlay_v1,
        best_causal_weights_v1_on_train,
        causal_feature_map,
    )

    csv = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not csv.is_file():
        return
    causal = causal_feature_map(csv)
    rows = [
        {
            "eval_date": d,
            "instrument": "btc",
            "actual_direction": "bull",
            "macro_score": 0.1,
            "source_direction": "bull",
        }
        for d in sorted(causal.keys())[-40:]
    ]
    params = (0.01, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    w, _ = best_causal_weights_v1_on_train(
        rows[:20],
        params,
        {},
        {},
        {},
        {},
        causal,
        include_source_direction_signal=True,
        train_objective="margin_vs_bull",
    )
    assert len(w) == 5
    acc, hits = acc_with_causal_overlay_v1(
        rows[20:],
        params,
        {},
        {},
        {},
        {},
        causal,
        include_source_direction_signal=True,
        causal_weights=w,
    )
    assert 0.0 <= acc <= 1.0
    assert hits >= 0


def test_rq024_closure_readiness_import():
    from scripts.build_rq024_research_closure_readiness_v1 import SCHEMA

    assert SCHEMA == "rq024_research_closure_readiness_v1"


def test_rq024_nf5_replication_import():
    from scripts.run_rq024_btc_lens_v1_nf5_wf_replication_v1 import SCHEMA

    assert SCHEMA == "rq024_btc_lens_v1_nf5_wf_replication_v1"
