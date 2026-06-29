"""Smoke tests for [MAX_HYPO] unbound sandbox harness."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
    SCHEMA,
    assert_output_path_isolated,
    build_report,
    load_recipe,
    max_hypo_lens_weights,
)


def test_load_recipe_schema():
    path = Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json")
    assert path.is_file()
    recipe = load_recipe(path)
    w = max_hypo_lens_weights(recipe)
    assert abs(sum(w.values()) - 1.0) < 0.01
    assert w.get("momentum_overlay", 0) >= 0.2


def test_track_wall_rejects_operational_score_path():
    try:
        assert_output_path_isolated(
            Path("docs/final/artifacts/btrack_prophecy_score_latest.json")
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_sandbox_output_allowed():
    assert_output_path_isolated(
        Path("experiments/max_hypo_unbound/results/max_theory_unbound_simulation_v1_latest.json")
    )


def test_build_report_schema():
    doc = build_report(
        recipe_path=Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"),
        steps=[{"step": "fills_cache", "present": False}],
        dry_run=True,
    )
    assert doc["schema"] == SCHEMA
    assert doc["research_only"] is True
    assert doc["track_wall"]["track_a_auto_bridge"] is False


def test_latest_json_if_present():
    path = Path("experiments/max_hypo_unbound/results/max_theory_unbound_simulation_v1_latest.json")
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == SCHEMA
    assert doc.get("source_track") == "B"


def test_shock_overlay_ablation_sidecar_on_fixture(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_shock_overlay_ablation_sidecar

    score = tmp_path / "score.json"
    score.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "eval_date": "2026-06-08",
                        "predicted_direction": "bear",
                        "actual_direction": "bear",
                    },
                    {
                        "eval_date": "2026-06-09",
                        "predicted_direction": "bull",
                        "actual_direction": "bull",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "ablation.json"
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not kospi.is_file():
        return
    summary = run_shock_overlay_ablation_sidecar(
        recipe=recipe,
        score_json=score,
        kospi_csv=kospi,
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "shock_overlay_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_shock_overlay_ablation_v1"
    assert doc.get("threshold_sweep")


def test_bull_abstain_overlay_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_bull_abstain_overlay_ablation_sidecar

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "bull_ablation.json"
    summary = run_bull_abstain_overlay_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "bull_abstain_overlay_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_bull_abstain_overlay_ablation_v1"
    assert len(doc.get("overlay_results") or []) >= 2
    spot_68 = next(
        (
            s
            for item in doc.get("overlay_results") or []
            for s in item.get("spotlight") or []
            if s.get("date") == "2026-06-08"
        ),
        None,
    )
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        bear_row = next(
            x for x in doc["overlay_results"] if x.get("overlay") == "prior_day_shock_bull_to_bear_v0"
        )
        spot_bear = next(s for s in bear_row["spotlight"] if s.get("date") == "2026-06-08")
        # -6% recommended may miss 6/8 when prior_completed is ~-5.54%; looser sweep should fire.
        modified_any = spot_bear.get("overlay_modified") or any(
            s.get("overlay_rows_modified", 0) > 0 for s in bear_row.get("threshold_sweep") or []
        )
        assert modified_any
        best = bear_row.get("best_delta_in_sweep") or {}
        if best.get("prior_return_threshold", 0) >= -0.048:
            assert spot_bear.get("after_overlay_predicted") in ("bear", "neutral")


def test_shock_rebound_guard_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_shock_rebound_guard_ablation_sidecar

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "rebound_guard.json"
    summary = run_shock_rebound_guard_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "shock_rebound_guard_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_shock_rebound_guard_ablation_v1"
    rec = doc.get("recommended_rebound_guard") or {}
    spot_68 = next((s for s in rec.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    spot_69 = next((s for s in rec.get("spotlight") or [] if s.get("date") == "2026-06-09"), None)
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        assert spot_68.get("after_overlay_predicted") == "bear"
        assert spot_68.get("after_overlay_hit") is True
    if spot_69 and spot_69.get("baseline_predicted") == "bull":
        assert spot_69.get("after_overlay_predicted") == "bull"
        assert spot_69.get("after_overlay_hit") is True


def test_intraday_oracle_overlay_fixes_6_8_not_6_9(tmp_path: Path) -> None:
    from scripts.run_prophecy_restoration_spike import (
        _apply_overlay,
        _eval_directional_hit,
        _intraday_open_to_low_drawdown_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
    )

    csv_path = tmp_path / "kospi.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-06-05,100,101,99,100,1000",
                "2026-06-06,100,101,94,94,1000",
                "2026-06-08,94,96,86.4,86.4,1000",
                "2026-06-09,86,92,88,92,1000",
            ]
        ),
        encoding="utf-8",
    )
    intraday_map = _intraday_open_to_low_drawdown_by_eval_date(csv_path)
    prior_map = _prior_completed_daily_return_by_eval_date(csv_path)
    rows = [
        {"eval_date": "2026-06-08", "predicted_direction": "bull", "actual_direction": "bear"},
        {"eval_date": "2026-06-09", "predicted_direction": "bull", "actual_direction": "bull"},
    ]
    overlaid, n_mod = _apply_overlay(
        rows,
        overlay="intraday_open_to_low_oracle_bull_to_bear_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=0.05,
        intraday_drawdown_by_date=intraday_map,
    )
    assert n_mod == 1
    by_date = {r["eval_date"]: r for r in overlaid}
    assert by_date["2026-06-08"]["predicted_direction"] == "bear"
    assert by_date["2026-06-09"]["predicted_direction"] == "bull"
    base_rate, _, _ = _eval_directional_hit(rows)
    ov_rate, _, _ = _eval_directional_hit(overlaid)
    assert base_rate == 0.5
    assert ov_rate == 1.0


def test_intraday_shock_proxy_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_intraday_shock_proxy_ablation_sidecar

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "intraday_proxy.json"
    summary = run_intraday_shock_proxy_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "intraday_shock_proxy_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_intraday_shock_proxy_ablation_v1"
    assert doc.get("track_wall") == "no_track_a_live_auto_merge"
    rec_oracle = doc.get("recommended_intraday_oracle") or {}
    spot_68 = next((s for s in rec_oracle.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    spot_69 = next((s for s in rec_oracle.get("spotlight") or [] if s.get("date") == "2026-06-09"), None)
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        assert spot_68.get("after_overlay_predicted") == "bear"
        assert spot_68.get("after_overlay_hit") is True
    if spot_69 and spot_69.get("baseline_predicted") == "bull":
        assert spot_69.get("after_overlay_predicted") == "bull"
        assert spot_69.get("after_overlay_hit") is True


def test_causal_open_limit_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_causal_open_limit_ablation_sidecar

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "causal_open_limit.json"
    summary = run_causal_open_limit_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "causal_open_limit_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_causal_open_limit_ablation_v1"
    tiers = {t["tier_id"]: t for t in doc.get("causal_tier_ladder") or []}
    t1 = tiers.get("T1_overnight_only") or {}
    t3 = tiers.get("T3_composite_recommended") or {}
    spot_68_t1 = next((s for s in t1.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    spot_68_t3 = next((s for s in t3.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    if spot_68_t1 and spot_68_t1.get("baseline_predicted") == "bull":
        assert spot_68_t1.get("overlay_modified") is False
    if spot_68_t3 and spot_68_t3.get("baseline_predicted") == "bull":
        assert spot_68_t3.get("after_overlay_predicted") == "bear"
        assert spot_68_t3.get("after_overlay_hit") is True
    limits = {x["date"]: x for x in doc.get("spotlight_causal_limits") or []}
    lim_68 = limits.get("2026-06-08") or {}
    assert lim_68.get("overnight_only_fires_at_tier_threshold") is False
    assert lim_68.get("prior_mild_fires_at_tier_threshold") is True
    wf = doc.get("composite_blocked_walkforward") or {}
    assert wf.get("n_folds_effective", 0) >= 1


def test_causal_vol_range_proxy_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import run_causal_vol_range_proxy_ablation_sidecar

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "vol_range_proxy.json"
    summary = run_causal_vol_range_proxy_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "causal_vol_range_proxy_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_causal_vol_range_proxy_ablation_v1"
    tiers = {t["tier_id"]: t for t in doc.get("causal_proxy_tiers") or []}
    t5 = tiers.get("T5_prior_range_low_open") or {}
    spot_68 = next((s for s in t5.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    spot_69 = next((s for s in t5.get("spotlight") or [] if s.get("date") == "2026-06-09"), None)
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        assert spot_68.get("after_overlay_predicted") == "bear"
        assert spot_68.get("after_overlay_hit") is True
    if spot_69 and spot_69.get("baseline_predicted") == "bull":
        assert spot_69.get("after_overlay_predicted") == "bull"
        assert spot_69.get("after_overlay_hit") is True
    wf = doc.get("conservative_vs_aggressive_walkforward") or {}
    assert wf.get("n_folds_effective", 0) >= 1


def test_causal_proxy_ensemble_holdout_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_causal_proxy_ensemble_holdout_ablation_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "ensemble_holdout.json"
    summary = run_causal_proxy_ensemble_holdout_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        dry_run=False,
    )
    assert summary["step"] == "causal_proxy_ensemble_holdout_ablation"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_causal_proxy_ensemble_holdout_ablation_v1"
    tiers = {t["tier_id"]: t for t in doc.get("full_window_tiers") or []}
    t7 = tiers.get("T7_range_or_composite_ensemble") or {}
    spot_68 = next((s for s in t7.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    spot_69 = next((s for s in t7.get("spotlight") or [] if s.get("date") == "2026-06-09"), None)
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        assert spot_68.get("after_overlay_predicted") == "bear"
        assert spot_68.get("after_overlay_hit") is True
    if spot_69 and spot_69.get("baseline_predicted") == "bull":
        assert spot_69.get("after_overlay_predicted") == "bull"
        assert spot_69.get("after_overlay_hit") is True
    holdout = doc.get("holdout_split") or {}
    assert holdout.get("n_holdout_dates", 0) >= 1
    assert (doc.get("range_threshold_blocked_walkforward") or {}).get("n_folds_effective", 0) >= 1
    t8 = tiers.get("T8_triple_causal_proxy_ensemble") or {}
    assert t8.get("delta_hit_rate") is not None
    audit = doc.get("holdout_fold_day_audit") or {}
    assert len(audit.get("folds") or []) >= 1
    assert summary.get("triple_ensemble_delta") is not None


def test_range_rebound_guard_refinement_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_range_rebound_guard_refinement_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "range_rebound.json"
    md = tmp_path / "summary.md"
    summary = run_range_rebound_guard_refinement_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "range_rebound_guard_refinement"
    assert out.is_file()
    assert md.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_range_rebound_guard_refinement_v1"
    assert len(doc.get("grid") or []) >= 1
    assert doc.get("recommended")


def test_t9_ensemble_holdout_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_t9_ensemble_holdout_ablation_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "t9_ens.json"
    md = tmp_path / "t9_ens.md"
    summary = run_t9_ensemble_holdout_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "t9_ensemble_holdout_ablation"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_t9_ensemble_holdout_ablation_v1"
    t10 = doc.get("recommended_t10") or {}
    assert t10.get("delta_hit_rate") is not None
    assert summary.get("spotlight_safe") is True
    cmp_ = doc.get("t10_vs_t7") or {}
    assert cmp_.get("regressions_fixed_vs_t7", 0) >= 3
    assert cmp_.get("regressions_remaining_vs_t7") == 0
    spot_68 = next((s for s in t10.get("spotlight") or [] if s.get("date") == "2026-06-08"), None)
    if spot_68 and spot_68.get("baseline_predicted") == "bull":
        assert spot_68.get("after_overlay_predicted") == "bear"


def test_ensemble_soft_range_uplift_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_ensemble_soft_range_uplift_ablation_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "soft_uplift.json"
    md = tmp_path / "soft_uplift.md"
    summary = run_ensemble_soft_range_uplift_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "ensemble_soft_range_uplift_ablation"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_ensemble_soft_range_uplift_ablation_v1"
    rec = doc.get("recommended") or {}
    assert rec.get("spotlight_safe") is True
    assert rec.get("regressions_remaining_vs_t7") == 0
    assert (rec.get("full_window_delta_hit_rate") or 0) >= (doc.get("baseline_t10") or {}).get(
        "delta_hit_rate", 0
    )


def test_composite_overnight_mild_gate_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_composite_overnight_mild_gate_ablation_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "ovn_gate.json"
    md = tmp_path / "ovn_gate.md"
    summary = run_composite_overnight_mild_gate_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "composite_overnight_mild_gate_ablation"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_composite_overnight_mild_gate_ablation_v1"
    assert summary.get("spotlight_safe") is True


def test_t10_shadow_eval_forbidden_path():
    from scripts.sandbox.run_max_hypo_t10_shadow_eval_v1 import assert_output_path_isolated

    try:
        assert_output_path_isolated(
            Path("docs/final/artifacts/prophecy_hit_rate_eval_latest.json")
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_t10_shadow_eval_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_hypo_t10_shadow_eval_v1 import run_shadow_eval

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    manifest = Path("experiments/max_hypo_unbound/results/max_hypo_recommended_tier_manifest_v1.json")
    recipe = Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json")
    if not all(p.is_file() for p in (panel, kospi, manifest, recipe)):
        return
    out = tmp_path / "t10_shadow.json"
    doc = run_shadow_eval(
        recipe_path=recipe,
        manifest_path=manifest,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
    )
    assert doc["schema"] == "max_hypo_t10_shadow_eval_v1"
    assert doc.get("overlay")
    assert doc.get("n_evaluated", 0) > 200


def test_recommended_tier_manifest_sidecar(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_recommended_tier_manifest_sidecar,
    )

    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "manifest.json"
    md = tmp_path / "manifest.md"
    summary = run_recommended_tier_manifest_sidecar(
        recipe=recipe,
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "recommended_tier_manifest"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_recommended_tier_manifest_v1"
    assert doc.get("recommended", {}).get("tier_id")
    assert out.is_file() and md.is_file()


def test_prior_mild_range_conjunction_ablation_sidecar_on_panel(tmp_path: Path):
    from scripts.sandbox.run_max_theory_unbound_simulation_v1 import (
        run_prior_mild_range_conjunction_ablation_sidecar,
    )

    panel = Path("reports/btrack_session_myeongni_panel_252d_v1.csv")
    kospi = Path("research/market_data/kospi_daily_external_yf.csv")
    if not panel.is_file() or not kospi.is_file():
        return
    recipe = load_recipe(Path("experiments/max_hypo_unbound/max_hypo_recipe_v1.json"))
    out = tmp_path / "conj.json"
    md = tmp_path / "conj.md"
    summary = run_prior_mild_range_conjunction_ablation_sidecar(
        recipe=recipe,
        panel_csv=panel,
        kospi_csv=kospi,
        date_from="2025-05-26",
        date_to="2026-06-09",
        spotlight_dates=["2026-06-08", "2026-06-09"],
        out_path=out,
        md_path=md,
        dry_run=False,
    )
    assert summary["step"] == "prior_mild_range_conjunction_ablation"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "max_hypo_prior_mild_range_conjunction_ablation_v1"
    rec = doc.get("recommended") or {}
    assert rec.get("spotlight_safe") is True
    assert rec.get("regressions_fixed", 0) >= 3
    assert rec.get("regressions_remaining_vs_t5") == 0
