"""June 2026 KOSPI daily prophecy calendar · eval · evolution smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_krx_election_day_excluded_from_june_calendar() -> None:
    import scripts.kospi_krx_calendar_v1 as krx

    june = krx.krx_trading_days(__import__("datetime").date(2026, 6, 1), __import__("datetime").date(2026, 6, 30))
    assert "2026-06-03" not in june
    assert "2026-06-03" in krx.load_krx_non_trading_days()


def test_build_calendar_schema() -> None:
    import scripts.build_kospi_june2026_daily_prophecy_calendar_v1 as mod

    doc = mod.build_calendar(skip_panel=True, profile="v2_multilens", year_month="2026-06")
    assert doc["schema"] == "kospi_monthly_daily_prophecy_calendar_v2"
    assert doc["multilens_profile"] == "v2_multilens"
    assert doc["n_trading_days"] >= 20
    assert "2026-06-03" not in (doc.get("trading_days") or [])
    assert doc["rows"][0]["hypothesis_tier"] == "B"
    assert doc["rows"][0]["research_only"] is True
    assert "kospi_index_prophecy" in doc["rows"][0]
    assert "integration_maturity" in doc
    assert doc["integration_maturity"]["integration_pct"] > 50


def test_multilens_blend_channels() -> None:
    import scripts.kospi_june2026_multilens_blend_v1 as ml

    static = ml.load_static_lenses()
    direction, score, detail = ml.blend_v2_multilens(
        session_map="bull",
        session_score=0.2,
        momentum_dir="bear",
        static_lenses=static,
        ensemble_row=None,
        weights=ml.default_weights_v2(),
        neutral_band=0.06,
        blend_policy={"directional_winner_min_weight": 0.26, "prefer_directional_over_neutral": True},
    )
    assert direction in ("bull", "bear", "neutral")
    assert "channels" in detail
    assert len(detail["channels"]) >= 5


def test_neutral_plurality_wins_over_bear_minority() -> None:
    import scripts.kospi_june2026_multilens_blend_v1 as ml

    static = ml.load_static_lenses()
    direction, _, detail = ml.blend_v2_multilens(
        session_map="sideways",
        session_score=0.05,
        momentum_dir="bear",
        static_lenses=static,
        ensemble_row={"predicted_direction": "bear", "weighted_score": -0.05},
        weights=ml.default_weights_v2(),
        neutral_band=0.06,
        blend_policy={
            "directional_winner_min_weight": 0.28,
            "directional_margin_ratio": 1.12,
            "prefer_directional_over_neutral": True,
            "require_directional_plurality": True,
        },
    )
    assert detail["votes"]["neutral"] > detail["votes"]["bear"]
    assert direction == "neutral"
    assert detail.get("winner_resolution") == "neutral_plurality"


def test_directional_winner_bear() -> None:
    import scripts.kospi_june2026_multilens_blend_v1 as ml

    static = ml.load_static_lenses()
    direction, _, detail = ml.blend_v2_multilens(
        session_map="bear",
        session_score=-0.2,
        momentum_dir="neutral",
        static_lenses=static,
        ensemble_row=None,
        weights=ml.default_weights_v2(),
        neutral_band=0.06,
        blend_policy={"directional_winner_min_weight": 0.26, "prefer_directional_over_neutral": True},
    )
    assert direction == "bear"
    assert detail.get("winner_resolution") == "directional_bear"


def test_eval_outcome_mapping() -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev

    assert ev._outcome("bull", "bull") == "HIT"
    assert ev._outcome("bear", "bull") == "FAIL"
    assert ev._outcome("bull", "neutral") == "NEUTRAL_DRAW"


def test_eval_paths_for_july_calendar() -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev

    cal_path = ROOT / "reports/kospi_202607_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file():
        pytest.skip("July calendar not built locally")
    report_out, art_out, score_log = ev._resolve_outputs(cal_path, {"year_month": "2026-07"})
    assert report_out.name == "kospi_202607_daily_prophecy_eval_latest.json"
    assert art_out.name == "kospi_202607_daily_prophecy_eval_latest.json"
    assert score_log.name == "kospi_202607_daily_prophecy_score_log.jsonl"


def test_eval_includes_as_of_day_when_ohlcv_present(tmp_path, monkeypatch) -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev

    csv_path = tmp_path / "kospi.csv"
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2026-06-01,1,1,1,100,1\n"
        "2026-06-04,1,1,1,110,1\n"
        "2026-06-05,1,1,1,105,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ev, "KOSPI_CSV", csv_path)

    cal = {
        "year_month": "2026-06",
        "trading_days": ["2026-06-01", "2026-06-04", "2026-06-05"],
        "rows": [
            {"session_date": "2026-06-01", "predicted_direction": "neutral", "kospi_index_prophecy": {}},
            {"session_date": "2026-06-04", "predicted_direction": "bear", "kospi_index_prophecy": {}},
            {"session_date": "2026-06-05", "predicted_direction": "bear", "kospi_index_prophecy": {}},
        ],
    }
    doc = ev.eval_calendar(cal, as_of_kst="2026-06-05")
    assert "2026-06-03" not in doc.get("missing_ohlcv_trading_days", [])
    assert doc["n_scored"] >= 2
    dates = [r["session_date"] for r in doc["rows"]]
    assert "2026-06-05" in dates


def test_evolution_hold_when_few_samples() -> None:
    import scripts.run_kospi_june2026_prophecy_evolution_v1 as evo

    rules = json.loads(
        (ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8")
    )
    doc = evo.run_evolution(
        eval_doc={"n_scored": 1, "metrics": {"soft_hit_rate": 0.2}},
        rules=rules,
        dry_run=True,
    )
    assert doc["evolution_action"] == "hold"
    assert doc["dry_run"] is True


def test_build_calendar_weights_candidate_id() -> None:
    import scripts.build_kospi_june2026_daily_prophecy_calendar_v1 as mod

    active = mod.build_calendar(skip_panel=True, profile="v2_multilens", year_month="2026-06")
    candidate = mod.build_calendar(
        skip_panel=True,
        profile="v2_multilens",
        year_month="2026-06",
        weights_candidate_id="v2_lens3_heavy",
    )
    assert candidate.get("weights_candidate_id") == "v2_lens3_heavy"
    assert float(candidate["blend_weights_applied"].get("session_myeongni", 0)) == 0.3
    active_w = active.get("blend_weights_applied") or {}
    cand_w = candidate.get("blend_weights_applied") or {}
    if float(active_w.get("session_myeongni", 0)) == 0.3:
        assert active_w == cand_w
    else:
        assert active_w != cand_w


def test_weight_candidate_compare_schema() -> None:
    import scripts.run_kospi_june2026_weight_candidate_compare_v1 as cmp

    rules = json.loads(
        (ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8")
    )
    horizon_v2_path = ROOT / "reports/three_lens_horizon_empirical_eval_v2_latest.json"
    horizon_v2 = json.loads(horizon_v2_path.read_text(encoding="utf-8")) if horizon_v2_path.is_file() else None
    doc = cmp.compare_candidates(
        rules=rules,
        year_month="2026-06",
        candidate_id="v2_lens3_heavy",
        horizon_v2_doc=horizon_v2,
    )
    assert doc["schema"] == "kospi_june2026_weight_candidate_compare_v1"
    assert doc["candidate_id"] == "v2_lens3_heavy"
    assert doc["research_only"] is True
    assert "direction_counts" in doc
    assert "promotion_recommendation" in doc
    assert doc["promotion_recommendation"]["ready_for_apply_review"] is False
    if doc.get("weight_apply_status", {}).get("candidate_already_applied"):
        assert doc["candidate_status"] == "applied_active"
        assert doc["promotion_recommendation"]["blockers"] == []
        assert doc["promotion_recommendation"]["candidate_already_applied"] is True
    pol = doc.get("weight_candidate_policy") or {}
    assert pol.get("policy_tier") == "recommended_strict_v1"
    assert int(pol.get("june_forward_min_scored_for_promotion", 0)) == 15
    wf = doc.get("walkforward_prefilter")
    walk_path = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
    if walk_path.is_file() and isinstance(wf, dict):
        assert wf.get("schema") == "kospi_june2026_walkforward_prefilter_v1"
        assert "walkforward_gate_pass" in wf
    if horizon_v2 and horizon_v2.get("schema") == "three_lens_horizon_empirical_eval_v2":
        shadow = doc.get("shadow_horizon_contract")
        assert isinstance(shadow, dict)
        assert shadow.get("shadow_candidate_id") == "myeongni_mid_5d"


def test_evolution_embeds_four_ai_kpi() -> None:
    import scripts.run_kospi_june2026_prophecy_evolution_v1 as evo

    rules = json.loads(
        (ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8")
    )
    four_ai_path = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
    four_ai = json.loads(four_ai_path.read_text(encoding="utf-8")) if four_ai_path.is_file() else None
    doc = evo.run_evolution(
        eval_doc={"n_scored": 3, "metrics": {"soft_hit_rate": 0.5}},
        rules=rules,
        four_ai_doc=four_ai,
        dry_run=True,
    )
    if four_ai:
        kpi = doc.get("four_ai_coordinator_kpi")
        assert isinstance(kpi, dict)
        assert kpi.get("n_trading_days", 0) >= 1


def test_walkforward_prefilter_strict_gate_blockers() -> None:
    import scripts.run_kospi_june2026_weight_candidate_compare_v1 as cmp

    policy = {
        "min_walkforward_selection_top1_hit_rate": 0.52,
        "require_walkforward_candidate_in_top2": True,
        "june_forward_min_scored_for_promotion": 15,
    }
    walk_doc = {
        "schema": "kospi_multilens_walkforward_backtest_v1",
        "summary": {
            "n_folds": 46,
            "selection_top1_hit_rate": 0.4783,
            "recommended_prefilter_variants_top2": ["v2_lens3_heavy", "v2_lens3_heavy_4ai_current"],
            "variant_rank_by_test_mean_soft": [{"variant_id": "v2_lens3_heavy", "mean_soft_hit_rate_test": 0.53}],
        },
    }
    out = cmp._walkforward_prefilter(walk_doc, candidate_id="v2_lens3_heavy", policy=policy)
    assert out is not None
    assert out["candidate_in_top2"] is True
    assert out["selection_top1_pass"] is False
    assert out["walkforward_gate_pass"] is False
    assert "walkforward_selection_top1<0.52" in out["walkforward_blockers"]


def test_walkforward_pragmatic_top2_only_passes() -> None:
    import scripts.run_kospi_june2026_weight_candidate_compare_v1 as cmp

    policy = {
        "walkforward_require_top1_min": False,
        "require_walkforward_candidate_in_top2": True,
        "june_forward_min_scored_for_promotion": 15,
    }
    walk_doc = {
        "schema": "kospi_multilens_walkforward_backtest_v1",
        "summary": {
            "selection_top1_hit_rate": 0.4783,
            "recommended_prefilter_variants_top2": ["v2_lens3_heavy", "v2_lens3_heavy_4ai_current"],
        },
    }
    out = cmp._walkforward_prefilter(walk_doc, candidate_id="v2_lens3_heavy", policy=policy)
    assert out is not None
    assert out["walkforward_gate_pass"] is True
    assert out["walkforward_blockers"] == []


def test_default_as_of_uses_last_krx_session(monkeypatch) -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev
    from datetime import datetime
    from zoneinfo import ZoneInfo

    class FakeDt:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 6, 8, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    monkeypatch.setattr(ev, "datetime", FakeDt)
    assert ev._default_as_of_kst() == "2026-06-05"


def test_vendor_incomplete_split_from_missing_ohlcv(tmp_path, monkeypatch) -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev

    csv_path = tmp_path / "kospi.csv"
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2026-06-03,1,1,1,100,1\n"
        "2026-06-04,1,1,1,110,1\n"
        "2026-06-05,1,1,1,,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ev, "KOSPI_CSV", csv_path)

    cal = {
        "year_month": "2026-06",
        "trading_days": ["2026-06-04", "2026-06-05"],
        "rows": [
            {"session_date": "2026-06-04", "predicted_direction": "bear", "kospi_index_prophecy": {}},
            {"session_date": "2026-06-05", "predicted_direction": "bear", "kospi_index_prophecy": {}},
        ],
    }
    doc = ev.eval_calendar(cal, as_of_kst="2026-06-05")
    assert "2026-06-05" in doc.get("vendor_incomplete_trading_days", [])
    assert "2026-06-05" not in doc.get("missing_ohlcv_trading_days", [])
    assert doc["n_scored"] == 1


def test_neutral_research_bundle_schema() -> None:
    import scripts.build_kospi_june2026_neutral_research_bundle_v1 as bundle

    cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    rules_path = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
    if not cal_path.is_file():
        cal = {
            "year_month": "2026-06",
            "weights_candidate_id": "v2_lens3_heavy",
            "blend_weights_applied": {"session_myeongni": 0.3, "sasang": 0.24, "macro": 0.24},
            "rows": [
                {
                    "session_date": "2026-06-01",
                    "predicted_direction": "neutral",
                    "session_mapping_target": "sideways",
                    "session_direction_score": 0.0,
                    "blend": {
                        "votes": {"bull": 0.24, "bear": 0.0, "neutral": 0.76},
                        "winner_resolution": "neutral_plurality",
                        "blended_score": 0.0,
                        "channels": [
                            {"channel": "session_myeongni", "direction": "neutral", "weight": 0.3},
                            {"channel": "sasang", "direction": "bull", "weight": 0.24},
                        ],
                    },
                }
            ],
        }
        rules = {"blend_policy_v2": {}, "neutral_band": 0.06}
    else:
        cal = json.loads(cal_path.read_text(encoding="utf-8-sig"))
        rules = json.loads(rules_path.read_text(encoding="utf-8-sig"))

    doc = bundle.build_bundle(calendar=cal, rules=rules, eval_doc=None, evolution_path=rules_path)
    assert doc["schema"] == "kospi_june2026_neutral_research_bundle_v1"
    assert doc["auto_apply"] is False
    assert doc["neutral_decomposition"]["n_trading_days"] >= 1
    assert "policy_sweep" in doc
    assert "four_ai_counterfactual" in doc


def test_shadow_candidate_panel_schema() -> None:
    import scripts.run_kospi_june2026_shadow_candidate_panel_v1 as panel

    rules_path = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8-sig"))
    ids = panel._resolve_shadow_candidate_ids(rules)
    assert "v2_lens3_heavy_4ai_current" in ids
    assert "v2_default_4ai_current" in ids
    assert "v2_field_momentum_4ai_legacy_hold" in ids
    assert "v2_lens3_heavy" not in ids

    doc = panel.build_shadow_panel(
        rules=rules,
        year_month="2026-06",
        write_compare_artifacts=False,
        eval_doc={
            "schema": "kospi_june2026_daily_prophecy_eval_v1",
            "year_month": "2026-06",
            "n_scored": 3,
            "metrics": {"soft_hit_rate": 0.5},
        },
    )
    assert doc["schema"] == "kospi_june2026_shadow_candidate_panel_v1"
    assert doc["auto_apply"] is False
    assert doc["applied_active_id"] == "v2_lens3_heavy"
    assert doc["active_forward"]["n_scored"] == 3
    assert len(doc["shadows"]) == 3
    for row in doc["shadows"]:
        assert row["candidate_status"] == "research_shadow"
        assert row["promotion_recommendation"]["ready_for_apply_review"] is False
    scored = doc.get("scored_day_arm_diff") or {}
    assert scored.get("schema") == "kospi_june2026_scored_day_arm_diff_v1"
    assert doc.get("rollup_artifact") == "reports/kospi_june2026_shadow_panel_rollup_latest.json"


def test_shadow_panel_rollup_empty_log(tmp_path) -> None:
    import scripts.build_kospi_june2026_shadow_panel_rollup_v1 as rollup

    log_path = tmp_path / "empty.jsonl"
    log_path.write_text("", encoding="utf-8")
    doc = rollup.build_rollup(log_path=log_path, year_month="2026-06")
    assert doc["schema"] == "kospi_june2026_shadow_panel_rollup_v1"
    assert doc["n_log_entries"] == 0
    assert doc["auto_apply"] is False
    assert doc["leader_by_last_forward_soft"] is None


def test_shadow_panel_rollup_series_and_leader(tmp_path) -> None:
    import scripts.build_kospi_june2026_shadow_panel_rollup_v1 as rollup

    log_path = tmp_path / "panel.jsonl"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_date_kst": "2026-06-04",
                        "logged_at_utc": "2026-06-04T09:00:00Z",
                        "active_n_scored": 2,
                        "active_soft_hit_rate": 0.5,
                        "applied_active_id": "v2_lens3_heavy",
                        "shadows": [
                            {
                                "candidate_id": "v2_default_4ai_current",
                                "soft_hit_rate": 0.6,
                                "soft_delta_vs_active": 0.1,
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "session_date_kst": "2026-06-05",
                        "logged_at_utc": "2026-06-05T09:00:00Z",
                        "active_n_scored": 3,
                        "active_soft_hit_rate": 0.5,
                        "applied_active_id": "v2_lens3_heavy",
                        "shadows": [
                            {
                                "candidate_id": "v2_default_4ai_current",
                                "soft_hit_rate": 0.67,
                                "soft_delta_vs_active": 0.17,
                            }
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    doc = rollup.build_rollup(log_path=log_path, year_month="2026-06")
    assert doc["n_log_entries"] == 2
    assert doc["delta_first_to_last"]["active_n_scored"] == 1
    assert doc["delta_first_to_last"]["active_soft_hit_rate"] == 0.0
    leader = doc["leader_by_last_forward_soft"]
    assert leader["candidate_id"] == "v2_default_4ai_current"
    assert leader["role"] == "research_shadow"


def test_scored_day_arm_diff_from_eval_rows() -> None:
    import scripts.run_kospi_june2026_shadow_candidate_panel_v1 as panel

    eval_doc = {
        "schema": "kospi_june2026_daily_prophecy_eval_v1",
        "rows": [
            {
                "session_date": "2026-06-03",
                "actual_direction": "bull",
                "outcome": "MISS",
            },
            {
                "session_date": "2026-06-04",
                "actual_direction": "neutral",
                "outcome": "NEUTRAL_DRAW",
            },
        ],
    }
    diff = panel._build_scored_day_arm_diff(
        applied_id="v2_lens3_heavy",
        shadow_ids=["v2_default_4ai_current"],
        year_month="2026-06",
        eval_doc=eval_doc,
    )
    assert diff["n_scored_days"] == 2
    assert diff["summary"]["n_days_any_shadow_direction_diff"] >= 0
    assert all("arms" in d for d in diff["days"])
