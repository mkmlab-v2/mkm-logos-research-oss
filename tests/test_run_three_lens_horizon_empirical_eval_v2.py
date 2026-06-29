"""Three-lens horizon empirical eval v2 smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_myeongni_grid_ranking() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    matrix = {
        "mid_5d": {"soft_hit_rate": 0.4},
        "mid_10d": {"soft_hit_rate": 0.55},
        "mid_15d": {"soft_hit_rate": 0.5},
        "mid_20d": {"soft_hit_rate": 0.48},
        "macro_21d": {"soft_hit_rate": 0.45},
    }
    ranked = sorted(
        mod.MYEONGNI_GRID.keys(),
        key=lambda h: float((matrix.get(h) or {}).get("soft_hit_rate") or -1.0),
        reverse=True,
    )
    assert ranked[0] == "mid_10d"


def test_sasang_intensity_smoke() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    closes = {f"2026-01-{i:02d}": 100.0 + i * 0.5 for i in range(1, 25)}
    trading_days = sorted(closes)
    sasang_by = {
        d: {
            "machine_readables": {
                "heat_proxy": 0.4 + (i % 5) * 0.05,
                "cold_proxy": 0.6 - (i % 5) * 0.05,
                "volatility_rarefaction_proxy": 0.3 + (i % 3) * 0.1,
            }
        }
        for i, d in enumerate(trading_days)
    }
    out = mod._eval_sasang_intensity(
        trading_days=trading_days,
        closes=closes,
        sasang_by_day=sasang_by,
        intensity_horizon_days=3,
        high_pct=75.0,
    )
    assert out["n_pairs"] >= 10
    assert "spearman_rank_corr" in out
    assert "intensity_rank_pass" in out
    assert "gate_policy" in out


def test_decision_to_direction_calm_neutral() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    assert mod._decision_to_direction("CALM", "low") == "neutral"
    assert mod._decision_to_direction("WATCH", "medium") == "bear"
    assert mod._decision_to_direction("NEUTRAL_BAND") == "neutral"


def test_research_proxy_only_flags_macro_causal() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v1 as v1
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    trading_days = ["2026-01-02", "2026-01-03", "2026-01-06", "2026-01-07", "2026-01-08"]
    labels = {
        d: {h: ("bull" if h == "macro_21d" else "bear") for h in v1.HORIZONS}
        for d in trading_days
    }
    logos_rows = {
        d: {
            "variants": {vid: {"direction": "bull"} for vid in mod.LOGOS_VARIANTS},
        }
        for d in trading_days
    }
    cov = {"research_backfill_rate": 1.0, "operational_causal_rate": 0.0}
    out = mod._eval_logos_variants(
        trading_days=trading_days,
        labels=labels,
        logos_rows_by_date=logos_rows,
        min_n=3,
        min_soft_delta=0.0,
        macro_risk_coverage=cov,
    )
    causal = out["per_variant"]["logos_macro_risk_causal"]
    assert causal["macro_alignment_pass"] is True
    assert causal["research_proxy_only"] is True
    assert causal["macro_alignment_pass_effective"] is False
    assert out["variants_macro_alignment_pass"] >= 1
    assert out["variants_macro_alignment_pass_effective"] < out["variants_macro_alignment_pass"]


def test_run_v2_kospi_smoke() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod

    if not mod.KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    leg = mod.run_v2_leg(
        instrument="kospi",
        csv_path=mod.KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-04-30",
        neutral_bps=5.0,
        myeongni_jsonl=mod.DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=mod.DEFAULT_SASANG_JSONL,
        logos_lens=mod.DEFAULT_LOGOS_LENS,
        myeongni_momentum_window=5,
        min_n=5,
        min_soft_delta=0.03,
        intensity_horizon_days=5,
        write_logos_jsonl=False,
    )
    assert "logos_per_date_eval" in leg
    assert "sasang_intensity_eval" in leg
    assert "myeongni_horizon_grid" in leg
