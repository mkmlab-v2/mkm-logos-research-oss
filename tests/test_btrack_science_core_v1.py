"""Science Core lane v1 smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_price_lens_causal_no_lookahead() -> None:
    from scripts.btrack_science_core_v1 import build_daily_returns, price_lens_causal_at_index

    closes = {
        "2026-01-02": 100.0,
        "2026-01-03": 102.0,
        "2026-01-06": 101.0,
        "2026-01-07": 103.0,
    }
    days = sorted(closes)
    rets = build_daily_returns(closes, days)
    score_a, _, _ = price_lens_causal_at_index(rets, days, 2, lookback=2)
    score_b, _, _ = price_lens_causal_at_index(rets, days, 3, lookback=2)
    assert score_a != score_b or days[2] != days[3]


def test_compose_science_excludes_humanist() -> None:
    from scripts.btrack_science_core_v1 import compose_science_core

    row = compose_science_core(
        price_score=0.2,
        price_conf=0.5,
        price_meta={"mode": "test"},
        macro_score=-0.1,
        macro_conf=0.4,
        macro_meta={"mode": "test"},
        news_score=0.0,
        news_conf=0.3,
        news_meta={"mode": "test"},
        session_date="2026-01-15",
    )
    assert row["excludes_humanist_lenses"] is True
    assert row["lane_id"] == "science_core_v1"
    assert row["direction"] in {"bull", "bear", "neutral"}
    assert "price" in row["components"]


def test_build_science_jsonl_smoke(tmp_path: Path) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    rows = build_rows(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-02-28",
        lookback=5,
        apply_overnight=False,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
    )
    assert len(rows) >= 5
    assert rows[0]["schema"] == "btrack_science_core_per_date_v1"
    out = tmp_path / "science.jsonl"
    write_jsonl(rows, out)
    assert out.is_file()


def test_horizon_eval_smoke(tmp_path: Path) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl
    from scripts.run_science_core_horizon_empirical_eval_v1 import run_eval
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    science_jsonl = tmp_path / "science_kospi.jsonl"
    rows = build_rows(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-02-28",
        lookback=5,
        apply_overnight=False,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
    )
    write_jsonl(rows, science_jsonl)

    doc = run_eval(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        science_jsonl=science_jsonl,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        myeongni_jsonl=ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202606.jsonl",
        sasang_jsonl=ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202606.jsonl",
        logos_lens=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        myeongni_momentum_window=5,
    )
    assert doc["schema"] == "science_core_horizon_empirical_eval_v1"
    assert "science_core" in doc["rate_matrix"]
def test_holdout_combo_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl
    from scripts.run_science_core_holdout_combo_v1 import run_holdout_bundle
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV
    import scripts.run_science_core_holdout_combo_v1 as holdout_mod

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    kospi_jsonl = tmp_path / "science_kospi.jsonl"
    btc_jsonl = tmp_path / "science_btc.jsonl"
    for instrument, csv, out, overnight in (
        ("kospi", KOSPI_CSV, kospi_jsonl, True),
        ("btc", holdout_mod.v1.BTC_CSV, btc_jsonl, False),
    ):
        if not csv.is_file():
            pytest.skip(f"{instrument} CSV missing")
        write_jsonl(
            build_rows(
                instrument=instrument,
                csv_path=csv,
                date_from="2026-02-01",
                date_to="2026-02-28",
                lookback=5,
                apply_overnight=overnight,
                exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
            ),
            out,
        )
    monkeypatch.setattr(holdout_mod, "DEFAULT_SCIENCE_JSONL_KOSPI", kospi_jsonl)
    monkeypatch.setattr(holdout_mod, "DEFAULT_SCIENCE_JSONL_BTC", btc_jsonl)

    doc = run_holdout_bundle(
        train_from="2026-02-01",
        train_to="2026-02-20",
        holdout_from="2026-02-21",
        holdout_to="2026-02-28",
        neutral_bps=5.0,
        myeongni_jsonl=ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202606.jsonl",
        sasang_jsonl=ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202606.jsonl",
        logos_lens=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        rebuild_science=False,
    )
    assert doc["schema"] == "science_core_holdout_combo_v1"
    assert "always_attach_recommended" in doc["summary"]
    assert "kospi" in doc and "btc" in doc


def test_walkforward_smoke(tmp_path: Path) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl
    from scripts.run_science_core_walkforward_v1 import run_walkforward
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    science_jsonl = tmp_path / "science_kospi.jsonl"
    write_jsonl(
        build_rows(
            instrument="kospi",
            csv_path=KOSPI_CSV,
            date_from="2026-02-01",
            date_to="2026-02-28",
            lookback=5,
            apply_overnight=False,
            exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
        ),
        science_jsonl,
    )

    doc = run_walkforward(
        kospi_csv=KOSPI_CSV,
        science_jsonl=science_jsonl,
        train_days=10,
        test_days=5,
        step_days=5,
        max_window_days=28,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        myeongni_jsonl=ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202606.jsonl",
        sasang_jsonl=ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202606.jsonl",
        logos_lens=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        myeongni_momentum_window=5,
    )
    assert doc["schema"] == "science_core_walkforward_v1"
    assert "n_folds" in doc["summary"]


def test_shock_discordant_report_smoke() -> None:
    from scripts.build_science_core_shock_discordant_day_report_v1 import build_report
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    science_jsonl = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    if not science_jsonl.is_file():
        pytest.skip("science jsonl missing")
    doc = build_report(
        csv_path=KOSPI_CSV,
        science_jsonl=science_jsonl,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        shock_move_bps=50.0,
        myeongni_jsonl=ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202606.jsonl",
        sasang_jsonl=ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202606.jsonl",
        logos_lens=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        myeongni_momentum_window=5,
    )
    assert doc["schema"] == "science_core_shock_discordant_day_v1"
    assert "macro_only_diversity_audit" in doc
    assert isinstance(doc.get("daily_rows"), list)


def test_composite_attach_gate() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _composite_attach

    holdout = {"always_attach_recommended": True, "recommended_combo_lens_id": "science_plus_sasang"}
    wf = {"selection_top1_hit_rate": 0.0, "mean_test_uplift_vs_science_alone": 0.0}
    blocked = _composite_attach(holdout, wf)
    assert blocked["composite_attach_recommended"] is False
    assert blocked["walkforward_blockers"]

    wf_ok = {"selection_top1_hit_rate": 0.25, "mean_test_uplift_vs_science_alone": 0.03}
    ok = _composite_attach(holdout, wf_ok, humanist_stub={"any_stub": False, "paths": {}})
    assert ok["composite_attach_recommended"] is True

    stub_blocked = _composite_attach(holdout, wf_ok, humanist_stub={"any_stub": True, "paths": {}})
    assert stub_blocked["composite_attach_recommended"] is False
    assert stub_blocked["stub_blockers"]

    sidecar_underlying = _composite_attach(
        holdout,
        wf_ok,
        humanist_stub={"any_stub": False, "underlying_stub_caution": True, "paths": {}},
    )
    assert sidecar_underlying["composite_attach_recommended"] is False
    assert "humanist_sidecar_underlying_calendar_stub" in sidecar_underlying["stub_blockers"]

    macro_bias = _composite_attach(
        holdout,
        wf_ok,
        humanist_stub={"any_stub": False, "paths": {}},
        macro_bias={"bias_flags": ["macro21_hit_above_shuffle_margin", "low_macro_score_entropy"]},
        holdout_slice_ab={"delta_science_plus_sasang_soft": 0.31},
    )
    assert "macro_only_in_sample_bias_suspect" in macro_bias["macro_blockers"]
    assert macro_bias["recommended_lane"] == "science_plus_sasang"

    stub_slice = _composite_attach(
        holdout,
        wf_ok,
        humanist_stub={"any_stub": True, "paths": {}},
        holdout_slice_ab={"delta_science_plus_sasang_soft": 0.31},
    )
    assert "holdout_slice_stub_depresses_science_plus_sasang" in stub_slice["stub_blockers"]


def test_science_jsonl_needs_rebuild(tmp_path: Path) -> None:
    from scripts.run_science_core_governance_bundle_v1 import _science_jsonl_needs_rebuild

    missing = tmp_path / "missing.jsonl"
    assert _science_jsonl_needs_rebuild(missing, "2026-01-01", "2026-06-08") is True

    sparse = tmp_path / "sparse.jsonl"
    sparse.write_text(
        "\n".join(
            json.dumps({"session_date": f"2026-02-{d:02d}"}) for d in range(1, 6)
        )
        + "\n",
        encoding="utf-8",
    )
    assert _science_jsonl_needs_rebuild(sparse, "2026-01-01", "2026-06-08") is True

    ok = tmp_path / "ok.jsonl"
    ok.write_text(
        "\n".join(
            json.dumps({"session_date": f"2026-02-{d:02d}"}) for d in range(1, 32)
        )
        + "\n",
        encoding="utf-8",
    )
    assert _science_jsonl_needs_rebuild(ok, "2026-02-01", "2026-02-28") is False


def test_recompose_science_from_components() -> None:
    from scripts.btrack_science_core_v1 import recompose_science_from_components

    row = {
        "components": {
            "price": {"direction_score": 0.5},
            "macro": {"direction_score": -0.2},
            "news": {"direction_score": 0.1},
        }
    }
    score, direction = recompose_science_from_components(row, {"price": 0.65, "macro": 0.2, "news": 0.15})
    assert direction in {"bull", "bear", "neutral"}
    assert score != 0.0
    score0, _ = recompose_science_from_components(
        row, {"price": 0.765, "macro": 0.235, "news": 0.0}
    )
    assert score0 != score


def test_news_coverage_audit_smoke(tmp_path: Path) -> None:
    from scripts.run_science_core_news_coverage_audit_v1 import run_audit

    science = tmp_path / "science.jsonl"
    exa = tmp_path / "exa.jsonl"
    exa.write_text(
        json.dumps(
            {
                "published_utc": "2026-05-01T12:00:00Z",
                "as_of_utc": "2026-05-01T12:00:00Z",
                "canonical_text": "Markets rally on macro relief and risk-on flows",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    science.write_text(
        json.dumps(
            {
                "session_date": "2026-05-10",
                "components": {"news": {"mode": "global_news_snapshot"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    doc = run_audit(
        science_jsonl=science,
        exa_jsonl=exa,
        date_from="2026-05-01",
        date_to="2026-05-31",
    )
    assert doc["schema"] == "science_core_news_coverage_audit_v1"
    assert doc["simulated_news_modes"].get("causal_exa_news_window", 0) >= 1


def test_governance_extended_audit_helpers(tmp_path: Path) -> None:
    from scripts.run_science_core_governance_bundle_v1 import (
        _audit_news_coverage_from_science_jsonl,
        _slim_humanist_ab,
        _slim_macro_bias_audit,
        _slim_slice_eval,
    )

    science = tmp_path / "science.jsonl"
    science.write_text(
        json.dumps(
            {
                "session_date": "2026-05-01",
                "components": {"news": {"mode": "causal_exa_news_window"}},
            }
        )
        + "\n"
        + json.dumps(
            {
                "session_date": "2026-05-02",
                "components": {"news": {"mode": "global_news_snapshot"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    news = _audit_news_coverage_from_science_jsonl(science)
    assert news["causal_exa_days"] == 1
    assert news["causal_exa_share"] == 0.5

    slim = _slim_slice_eval(
        {
            "slices": {
                "by_coverage": {
                    "holdout_2026_h1": {
                        "n_days": 10,
                        "best_lens_id": "science_plus_sasang",
                        "lenses": {
                            "science_plus_sasang": {"soft_hit_rate": 0.7},
                            "science_core": {"soft_hit_rate": 0.3},
                        },
                    }
                }
            }
        }
    )
    assert slim["science_plus_sasang_soft_hit_short_1d"] == 0.7

    macro = _slim_macro_bias_audit(
        {
            "n_eval_days": 100,
            "bias_flags": ["low_macro_score_entropy"],
            "observed_hit_rates": {"macro_vs_short_1d": 0.55},
            "verdict_ko": "test",
        }
    )
    assert macro["bias_flags"] == ["low_macro_score_entropy"]

    ab = _slim_humanist_ab(
        {
            "windows": {"holdout": "2026-05"},
            "arms": {"calendar_stub": {"uplift_pp": 0.25}},
            "delta_market_sasang_minus_stub": {"holdout_uplift_pp": 0.33},
        }
    )
    assert ab["calendar_stub"]["uplift_pp"] == 0.25


def test_export_humanist_from_sidecar_smoke() -> None:
    from scripts.build_btrack_humanist_jsonl_from_sidecar_v1 import export_humanist_jsonl_from_sidecar

    sidecar = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
    if not sidecar.is_file():
        pytest.skip("sidecar missing")
    doc = export_humanist_jsonl_from_sidecar(sidecar_path=sidecar, instrument="kospi")
    assert doc["n_eval_dates"] >= 1
    if doc["myeongni_rows"]:
        assert doc["myeongni_rows"][0].get("stub") is False
        assert doc["myeongni_rows"][0].get("underlying_may_be_calendar_stub") is True


def test_market_sasang_per_date_row_smoke() -> None:
    from scripts.build_btrack_market_sasang_per_date_jsonl_v1 import build_market_sasang_per_date_rows
    from scripts.market_psych_sasang_axis_v2 import load_manifest, map_row_to_sasang

    manifest = load_manifest(ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json")
    row = {
        "timestamp_utc": "2026-05-15T00:00:00Z",
        "fear_score": "0.6",
        "greed_score": "0.2",
        "ret_5d": "-0.02",
        "ret_20d": "0.01",
        "vol_ratio": "1.1",
        "rsi_14_norm": "0.45",
        "panic_ratio": "0.5",
        "fomo_index": "0.3",
        "volatility_score": "0.4",
        "range_pct": "0.02",
        "momentum_20_60": "0.1",
        "drawdown_20d": "-0.05",
        "trend_strength": "0.7",
        "dispersion_score": "0.5",
    }
    m = map_row_to_sasang(row, manifest=manifest, prev_stress=None)
    assert m.get("mapping_target") in {"bull", "bear", "neutral", "sideways"}
    assert (m.get("machine_readables") or {}).get("heat_proxy") is not None

    csv = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
    if not csv.is_file():
        pytest.skip("market psych csv missing")
    rows, meta = build_market_sasang_per_date_rows(
        csv_path=csv,
        manifest_path=ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json",
        policy_path=ROOT / "data/market_sasang/market_sasang_lens_policy_v1.json",
        date_from="2026-05-01",
        date_to="2026-06-08",
    )
    assert meta["n_rows"] >= 1
    assert rows[0].get("stub") is False
    assert rows[0].get("source_provenance") == "market_psych_v2_per_date_v1"


def test_myeongni_per_date_row_smoke() -> None:
    from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import build_myeongni_session_jsonl_rows
    from scripts.btrack_multilens_per_date_core_v1 import score_myeongni_at_date

    rows, _, meta = build_myeongni_session_jsonl_rows(
        date_from="2026-05-01",
        date_to="2026-05-05",
        calendar_mode="krx_weekdays",
    )
    assert meta["n_days"] >= 1
    row = rows[0]
    assert row.get("stub") is False
    assert row.get("source_provenance") == "manseryeok_session_per_date_v1"
    assert isinstance(row.get("state_id"), int)
    scored = score_myeongni_at_date(rows[:1], eval_date=row["eval_date"], matched_day=row["eval_date"])
    assert scored["data_quality"] == "manseryeok_session_per_date_v1"


def test_humanist_stub_audit_manseryeok_non_stub(tmp_path: Path) -> None:
    from scripts.run_science_core_governance_bundle_v1 import _humanist_inputs_are_calendar_stub

    my_path = tmp_path / "my.jsonl"
    my_path.write_text(
        json.dumps(
            {
                "stub": False,
                "source_provenance": "manseryeok_session_per_date_v1",
                "mapping_target": "bull",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    sa_path = tmp_path / "sa.jsonl"
    sa_path.write_text(
        json.dumps(
            {
                "stub": False,
                "source_provenance": "market_psych_v2_per_date_v1",
                "mapping_target": "bear",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    audit = _humanist_inputs_are_calendar_stub(my_path, sa_path)
    assert audit["any_stub"] is False
    assert audit["manseryeok_session_per_date"] is True
    assert audit["underlying_stub_caution"] is False


def test_repo_rel_handles_relative_logos_path() -> None:
    from scripts.run_science_core_horizon_empirical_eval_v1 import _repo_rel

    rel = Path("reports/btrack_logos_per_date_v1.jsonl")
    out = _repo_rel(rel)
    assert out == "reports/btrack_logos_per_date_v1.jsonl"


def test_logos_per_date_row_smoke() -> None:
    from scripts.btrack_logos_per_date_core_v1 import (
        build_logos_per_date_rows,
        logos_block_at_date,
        index_logos_per_date_rows,
    )
    import scripts.run_three_lens_horizon_empirical_eval_v1 as v1

    csv = v1.KOSPI_CSV
    if not csv.is_file():
        pytest.skip("KOSPI CSV missing")
    closes = v1._load_closes(csv)
    days = sorted(closes.keys())
    rows, meta = build_logos_per_date_rows(
        trading_days=days,
        closes=closes,
        date_from="2026-05-01",
        date_to="2026-06-08",
        neutral_bps=5.0,
    )
    assert meta["n_rows"] >= 1
    assert rows[0].get("stub") is False
    assert rows[0].get("non_gating") is True
    assert rows[0].get("source_provenance") == "macro_gate_causal_asof_v1"
    by_day = index_logos_per_date_rows(rows)
    block = logos_block_at_date(by_day, "2026-06-01")
    assert block.get("input_mode") == "per_date_macro_gate"
    assert block.get("non_gating") is True


def test_triple_sasang_myeongni_direction_weights() -> None:
    from scripts.btrack_science_core_v1 import triple_sasang_myeongni_direction

    assert triple_sasang_myeongni_direction(1.0, 1.0, -1.0) == "bull"
    assert triple_sasang_myeongni_direction(-1.0, -1.0, 1.0) == "bear"


def test_btc_holdout_auxiliary_gate_observe_only() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _btc_holdout_auxiliary_gate

    doc = _btc_holdout_auxiliary_gate(
        {
            "n_eval_dates": 18,
            "rate_matrix": {
                "science_core": {"short_1d": {"soft_hit_rate": 0.4}},
                "science_plus_sasang": {"short_1d": {"soft_hit_rate": 0.55}},
            },
        },
        {"kospi_holdout_uplift_soft": 0.58},
    )
    assert doc["gates_primary_attach"] is False
    assert doc["auxiliary_recommendation"] == "observe_only"
    assert doc["uplift_directional_parity_with_kospi"] == "aligned"


def test_pnl_economic_significance_blocks_live_claim() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _slim_pnl_economic_significance

    doc = _slim_pnl_economic_significance(
        {
            "pnl_backtest_holdout": {
                "fee_bps": 5.0,
                "strategies": {
                    "science_core": {"total_return": -0.02, "n_active_days": 10},
                    "science_plus_sasang": {"total_return": 0.01, "n_active_days": 12},
                    "science_plus_myeongni": {"total_return": -0.01, "n_active_days": 8},
                },
            }
        }
    )
    assert doc["economic_edge_claim_allowed"] is False
    assert "holdout_science_core_pnl_non_positive" in doc["pnl_blockers"]
    assert doc["holdout_delta_total_return_vs_science"]["science_plus_sasang"] == 0.03


def test_slim_shock_only_attach_policy_rejects_switch() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _slim_shock_only_attach_policy

    slim = _slim_shock_only_attach_policy(
        {
            "policy_verdict": {
                "attach_on_shock_only_recommended": False,
                "recommended_hypothesis": "keep_always_science_plus_sasang",
                "shock_only_vs_always_sasang_soft_pp": -0.0185,
            },
            "soft_hit": {
                "policies": {
                    "shock_only_attach": {"n_scored": 27, "soft_hit_rate": 0.7963},
                    "always_science_plus_sasang": {"soft_hit_rate": 0.8148},
                }
            },
            "pnl_sim": {
                "policies": {
                    "shock_only_attach": {"total_return": 0.203773},
                    "always_science_plus_sasang": {"total_return": 0.516834},
                }
            },
        }
    )
    assert slim is not None
    assert slim["attach_on_shock_only_recommended"] is False
    assert slim["recommended_hypothesis"] == "keep_always_science_plus_sasang"
    assert slim["active_lane_unchanged"] == "science_plus_sasang"
    assert slim["economic_edge_claim_allowed"] is False


def test_humanist_combo_holdout_compare_ranking() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _humanist_combo_holdout_compare

    doc = _humanist_combo_holdout_compare(
        {
            "n_eval_dates": 20,
            "rate_matrix": {
                "science_core": {"short_1d": {"soft_hit_rate": 0.5}},
                "science_plus_sasang": {"short_1d": {"soft_hit_rate": 0.7}},
                "science_plus_myeongni": {"short_1d": {"soft_hit_rate": 0.55}},
            },
        }
    )
    assert doc["short_1d_ranking"][0]["lens_id"] == "science_plus_sasang"
    assert doc["sasang_vs_myeongni_delta_short_1d"] == 0.15


def test_governance_instrument_parity_summary_shape() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _slim_instrument_parity

    parity = _slim_instrument_parity(
        {"kospi_holdout_uplift_soft": 0.58, "always_attach_recommended": True},
        {
            "long_window_lane_compare": {
                "kospi": {"eras": {"bundle_window_market_sasang": {"science_plus_sasang_soft": 0.72}}},
                "btc": {"eras": {"bundle_window_market_sasang": {"science_plus_sasang_soft": 0.53}}},
            }
        },
    )
    assert parity["kospi"]["holdout_uplift_soft"] == 0.58
    assert parity["btc"]["bundle_market_sasang_combo_soft"] == 0.53


def test_readiness_strict_requires_instrument_parity() -> None:
    from scripts.check_science_core_lane_readiness_v1 import _validate_governance

    doc = {
        "promotion_gate": {"track_a_ready": False, "live_trading_ready": False},
        "composite_attach": {
            "composite_attach_recommended": True,
            "stub_blockers": [],
            "macro_blockers": [],
        },
        "extended_audits": {
            "macro_gate_bias_bundle_window": {},
            "holdout_slice_ab": {},
            "news_coverage": {},
            "era_split_news_policy": {},
            "long_window_lane_compare": {
                "kospi": {"eras": {}},
                "btc": {"eras": {}},
            },
        },
    }
    issues = _validate_governance(doc)
    assert "instrument_parity_summary missing" in issues

    doc["instrument_parity_summary"] = {"kospi": {}, "btc": {}}
    doc["humanist_combo_holdout"] = {"short_1d_ranking": []}
    doc["btc_holdout_auxiliary"] = {"gates_primary_attach": False}
    doc["pnl_economic_significance"] = {"economic_edge_claim_allowed": False}
    issues2 = _validate_governance(doc)
    assert "instrument_parity_summary missing" not in issues2
    assert "pnl_economic_significance missing" not in issues2


def test_era_split_news_policy_sparse_pre_exa() -> None:
    from scripts.run_science_core_governance_bundle_v1 import _era_split_news_policy

    policy = _era_split_news_policy(ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl")
    if not (ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl").is_file():
        pytest.skip("kospi science jsonl missing")
    assert policy["sparse_pre_exa_exa_expected"] is True
    assert policy["exa_era_start"] == "2020-01-01"


def test_long_window_lane_compare_btc_smoke() -> None:
    from scripts.run_science_core_long_window_lane_compare_v1 import run_compare, slim_eras_from_compare_doc
    import scripts.run_three_lens_horizon_empirical_eval_v1 as v1

    btc_jsonl = ROOT / "reports/btrack_science_core_per_date_btc_v1.jsonl"
    if not btc_jsonl.is_file():
        pytest.skip("btc science jsonl missing")
    if v1.BTC_CSV.is_file():
        closes = v1._load_closes(v1.BTC_CSV)
        if closes and min(closes.keys()) > "2019-12-31":
            pytest.skip("BTC CSV does not overlap pre_exa era (2014-2019)")
    doc = run_compare(
        instrument="btc",
        science_jsonl=btc_jsonl,
        date_to="2026-06-08",
        bundle_from="2026-01-01",
        bundle_to="2026-06-08",
        neutral_bps=5.0,
    )
    slim = slim_eras_from_compare_doc(doc)
    assert doc["instrument"] == "btc"
    assert slim["pre_exa_era"]["n_days"] >= 100


def test_long_window_lane_compare_news_off_augment(tmp_path: Path) -> None:
    from scripts.run_science_core_long_window_lane_compare_v1 import (
        NEWS_OFF_WEIGHTS,
        _augment_news_off_outcomes,
        _slim_block,
    )

    science_by = {
        "2026-05-01": {
            "session_date": "2026-05-01",
            "components": {
                "price": {"direction_score": 0.4},
                "macro": {"direction_score": -0.2},
                "news": {"direction_score": 0.9},
            },
        }
    }
    sa_by = {
        "2026-05-01": {
            "session_date": "2026-05-01",
            "direction_score": 0.3,
        }
    }
    rows = [
        {
            "session_date": "2026-05-01",
            "actual_short_1d": "up",
            "outcomes_short_1d": {
                "science_core": {"soft_hit": True},
                "science_plus_sasang": {"soft_hit": True},
            },
        }
    ]
    _augment_news_off_outcomes(rows, science_by=science_by, sa_by=sa_by)
    assert "science_plus_sasang_news_off" in rows[0]["outcomes_short_1d"]
    assert NEWS_OFF_WEIGHTS["news"] == 0.0
    block = _slim_block(rows)
    assert block["n_days"] == 1
    assert "science_plus_sasang_news_off" in block["lenses"]


def test_prophecy_combo_science_variants_smoke() -> None:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _build_variants, _extract_science_maps

    base = _build_variants(include_science=False)
    sci = _build_variants(include_science=True)
    assert len(sci) == len(base) + 4
    science_jsonl = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    if not science_jsonl.is_file():
        pytest.skip("science jsonl missing")
    signs, scores = _extract_science_maps(science_jsonl)
    assert signs
    assert scores


def test_extend_calendar_stub_smoke(tmp_path: Path) -> None:
    from scripts.extend_btrack_calendar_stub_jsonl_v1 import extend_stub, _sasang_row

    src = tmp_path / "src.jsonl"
    src.write_text(
        '{"ts_utc": "2026-04-29T12:00:00+00:00", "mapping_target": "bear"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    meta = extend_stub(source=src, out_path=out, through_date="2026-05-02", row_builder=_sasang_row)
    assert meta["appended"] == 3
    assert out.is_file()


def test_sidecar_logos_session_date_index_smoke(tmp_path: Path) -> None:
    from scripts.build_btrack_prophecy_score_insight_sidecar_stub_v1 import (
        _jsonl_last_row_by_calendar_day,
        _row_asof_calendar_day,
    )

    logos_path = tmp_path / "logos.jsonl"
    logos_path.write_text(
        json.dumps(
            {
                "session_date": "2026-06-01",
                "direction": "down",
                "non_gating": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    by_day = _jsonl_last_row_by_calendar_day(logos_path)
    assert "2026-06-01" in by_day
    matched, row = _row_asof_calendar_day(by_day, "2026-06-05")
    assert matched == "2026-06-01"
    assert row.get("direction") == "down"


def test_sidecar_logos_per_date_alignment_smoke() -> None:
    from scripts.build_btrack_prophecy_score_insight_sidecar_stub_v1 import _per_date_features

    rows = [{"eval_date": "2026-06-01", "instrument": "kospi", "predicted_direction": "up"}]
    lens_snap = {
        "logos": {"direction": "flat", "non_gating": True},
        "myeongni": {"direction": "up"},
        "sasang": {"direction": "down"},
    }
    logos_by_day = {
        "2026-06-01": {
            "session_date": "2026-06-01",
            "direction": "down",
            "direction_score": -0.2,
            "derivation_mode": "macro_gate_causal_asof",
            "non_gating": True,
            "source_provenance": "macro_gate_causal_asof_v1",
        }
    }
    out = _per_date_features(rows, lens_snap, None, None, None, logos_by_day)
    assert len(out) == 1
    assert out[0]["lens_snapshot_attribution"] == "per_date_mirrored_v1"
    dated = out[0]["dated_source_snapshots_asof_eval_date"]
    assert dated["logos_per_date_jsonl"]["matched_calendar_day"] == "2026-06-01"
    assert dated["logos_per_date_jsonl"]["snapshot"]["direction"] == "down"
    logos_snap_out = out[0]["lens_scores_snapshot"]["logos"]
    assert logos_snap_out.get("per_date_overlay") is True
    assert logos_snap_out.get("direction") == "down"


def test_long_walkforward_smoke() -> None:
    from scripts.run_science_core_long_walkforward_v1 import run_long_walkforward
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    profiles = (
        {
            "profile_id": "pytest_tiny",
            "date_from": "2026-02-01",
            "date_to": "2026-02-28",
            "train_days": 10,
            "test_days": 5,
            "step_days": 5,
        },
    )
    doc = run_long_walkforward(
        profiles=profiles,
        neutral_bps=5.0,
        rebuild_per_date=False,
        rebuild_science=False,
    )
    assert doc["schema"] == "science_core_long_walkforward_v1"
    assert doc["research_only"] is True
    assert len(doc["profiles"]) == 1
    arms = doc["profiles"][0]["arms"]
    assert "calendar_stub" in arms and "full_per_date" in arms


def test_lane_readiness_checker_scripts_ok(tmp_path: Path) -> None:
    from scripts.check_science_core_lane_readiness_v1 import build_report

    out = tmp_path / "readiness.json"
    doc = build_report(strict_governance=False, governance_path=tmp_path / "missing.json")
    assert doc["readiness_ok"] is True
    assert doc["scripts"]["missing"] == []
    assert doc["lane_id"] == "science_core_v1"


def test_daily_chain_wires_science_core_combo_tail() -> None:
    chain = ROOT / "scripts/run_btrack_daily_hypothesis_chain.ps1"
    text = chain.read_text(encoding="utf-8")
    assert "-IncludeScienceCoreLane" in text
    assert "run_prophecy_lens_combo_backtest_v1.py" in text
    assert "--include-science-core" in text
    assert "prophecy_lens_combo_backtest_science_core_v1_latest.json" in text
    assert "check_science_core_lane_readiness_v1.py" in text


def test_long_history_slice_eval_smoke(tmp_path: Path) -> None:
    from scripts.build_btrack_science_core_per_date_v1 import build_rows, write_jsonl
    from scripts.run_science_core_long_history_slice_eval_v1 import run_slice_eval
    from scripts.btrack_multilens_per_date_core_v1 import (
        DEFAULT_LOGOS_LENS,
        DEFAULT_MYEONGNI_JSONL,
        DEFAULT_SASANG_JSONL,
    )
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    science_jsonl = tmp_path / "science_kospi_smoke.jsonl"
    rows = build_rows(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-02-28",
        lookback=5,
        apply_overnight=True,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
    )
    write_jsonl(rows, science_jsonl)
    doc = run_slice_eval(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        science_jsonl=science_jsonl,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=DEFAULT_SASANG_JSONL,
        logos_lens=DEFAULT_LOGOS_LENS,
    )
    assert doc["schema"] == "science_core_long_history_slice_eval_v1"
    assert doc["research_only"] is True
    assert "by_year" in doc["slices"]
    assert "by_coverage" in doc["slices"]
    assert doc["n_eval_days"] >= 10


def test_macro_gate_bias_audit_smoke() -> None:
    from scripts.run_science_core_macro_gate_bias_audit_v1 import run_audit
    from scripts.run_science_core_horizon_empirical_eval_v1 import DEFAULT_SCIENCE_JSONL_KOSPI
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file() or not DEFAULT_SCIENCE_JSONL_KOSPI.is_file():
        pytest.skip("KOSPI science inputs missing")
    doc = run_audit(
        csv_path=KOSPI_CSV,
        science_jsonl=DEFAULT_SCIENCE_JSONL_KOSPI,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        shuffle_trials=20,
        seed=1,
    )
    assert doc["schema"] == "science_core_macro_gate_bias_audit_v1"
    assert doc["research_only"] is True
    assert doc["n_eval_days"] >= 10


def test_lane_readiness_governance_contract(tmp_path: Path) -> None:
    from scripts.check_science_core_lane_readiness_v1 import build_report

    gov = tmp_path / "gov.json"
    gov.write_text(
        json.dumps(
            {
                "lane_id": "science_core_v1",
                "composite_attach": {
                    "composite_attach_recommended": True,
                    "recommended_lane": "science_plus_sasang",
                    "stub_blockers": [],
                    "macro_blockers": [],
                },
                "extended_audits": {
                    "macro_gate_bias_bundle_window": {"bias_flags": []},
                    "macro_gate_bias_full_window": {"bias_flags": []},
                    "macro_gate_bias_long_history": {
                        "bias_flags": ["macro21_hit_above_shuffle_margin"],
                    },
                    "holdout_slice_ab": {"delta_science_plus_sasang_soft": 0.31},
                    "news_coverage": {"causal_exa_share": 0.01, "sparse_causal_coverage": True},
                    "era_split_news_policy": {"pre_exa": {}, "exa_era": {}},
                    "long_window_lane_compare": {
                        "kospi": {"eras": {"bundle_window_market_sasang": {}}},
                        "btc": {"eras": {"bundle_window_market_sasang": {}}},
                    },
                },
                "instrument_parity_summary": {
                    "kospi": {"holdout_uplift_soft": 0.31},
                    "btc": {"bundle_market_sasang_combo_soft": 0.53},
                },
                "humanist_combo_holdout": {"short_1d_ranking": []},
                "btc_holdout_auxiliary": {"gates_primary_attach": False},
                "pnl_economic_significance": {"economic_edge_claim_allowed": False},
                "promotion_gate": {
                    "track_a_ready": False,
                    "live_trading_ready": False,
                },
            }
        ),
        encoding="utf-8",
    )
    doc = build_report(strict_governance=True, governance_path=gov)
    assert doc["readiness_ok"] is True
    assert doc["governance"]["valid"] is True
    assert doc["composite_summary"]["recommended_lane"] == "science_plus_sasang"


def test_slim_triple_blend_and_pnl_bootstrap_helpers() -> None:
    from scripts.run_science_core_governance_bundle_v1 import (
        _slim_pnl_bootstrap,
        _slim_triple_blend_sweep,
    )

    triple = _slim_triple_blend_sweep(
        {
            "best_holdout_triple": {
                "profile_id": "baseline_50_25_25",
                "holdout_triple_soft": 0.66,
            },
            "holdout_sasang_combo_reference_soft": 0.86,
            "any_triple_beats_sasang_combo_on_holdout": False,
            "ranked_holdout_by_triple_soft": [{"profile_id": "a"}, {"profile_id": "b"}],
        }
    )
    assert triple["best_holdout_profile"] == "baseline_50_25_25"
    assert triple["any_triple_beats_sasang_combo_on_holdout"] is False
    assert len(triple["ranked_holdout_top3"]) == 2

    pnl = _slim_pnl_bootstrap(
        {
            "window": {"from": "2026-05-01", "to": "2026-06-08"},
            "bootstrap_trials": 2000,
            "strategies": {"science_plus_sasang": {"total_return": 0.629, "ci_95": [0.1, 0.9]}},
            "sasang_combo_ci_excludes_zero": True,
            "economic_edge_claim_allowed": False,
            "delta_vs_science": {"science_plus_sasang": {"delta_total_return_vs_science": 0.77}},
        }
    )
    assert pnl["economic_edge_claim_allowed"] is False
    assert pnl["science_plus_sasang_total_return"] == 0.629


def test_prophecy_combo_attach_gate_skip(tmp_path: Path) -> None:
    from scripts.run_science_core_prophecy_combo_attach_v1 import main as attach_main

    gov = tmp_path / "gov.json"
    gov.write_text(
        json.dumps(
            {
                "composite_attach": {
                    "composite_attach_recommended": False,
                    "recommended_lane": "science_plus_sasang",
                },
                "promotion_gate": {"track_a_ready": False, "live_trading_ready": False},
                "research_only": True,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "combo.json"
    rc = attach_main(
        [
            "--governance-json",
            str(gov),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["combo_backtest_ran"] is False
    assert doc["research_only"] is True


def test_triple_blend_sweep_smoke() -> None:
    from scripts.run_science_core_triple_blend_weight_sweep_v1 import run_sweep

    science = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    sasang = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
    if not science.is_file() or not sasang.is_file():
        pytest.skip("per-date jsonl missing")
    doc = run_sweep(
        science_jsonl=science,
        sasang_jsonl=sasang,
        myeongni_jsonl=ROOT / "reports/btrack_myeongni_per_date_v1.jsonl",
        date_from="2026-05-01",
        date_to="2026-06-08",
        train_to="2026-05-15",
        holdout_from="2026-05-16",
        holdout_to="2026-06-08",
        neutral_bps=5.0,
    )
    assert doc["schema"] == "science_core_triple_blend_weight_sweep_v1"
    assert doc["research_only"] is True
    assert doc.get("best_holdout_triple") is not None


def test_pnl_bootstrap_smoke() -> None:
    from scripts.run_science_core_pnl_bootstrap_v1 import run_bootstrap

    science = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
    sasang = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
    if not science.is_file() or not sasang.is_file():
        pytest.skip("per-date jsonl missing")
    doc = run_bootstrap(
        science_jsonl=science,
        sasang_jsonl=sasang,
        myeongni_jsonl=ROOT / "reports/btrack_myeongni_per_date_v1.jsonl",
        holdout_from="2026-05-01",
        holdout_to="2026-06-08",
        fee_bps=5.0,
        neutral_bps=5.0,
        trials=200,
        seed=42,
    )
    assert doc["schema"] == "science_core_pnl_bootstrap_v1"
    assert doc["economic_edge_claim_allowed"] is False
    assert "science_plus_sasang" in doc["strategies"]
