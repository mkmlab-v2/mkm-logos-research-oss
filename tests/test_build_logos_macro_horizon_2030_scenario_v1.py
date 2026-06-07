from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_macro_horizon_2030_scenario_v1.py"


def _write_fixture_tree(art: Path) -> None:
    art.mkdir(parents=True, exist_ok=True)
    (art / "logos_chronology_dynamic_map_v1_latest.json").write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-06-07T00:00:00Z",
                "inferred_regime_tags": ["caution", "risk"],
                "era_ranking": [
                    {"era_id": "modern_observational_field", "label_ko": "현대", "score": 0.77},
                    {"era_id": "judges_risk_cycle", "label_ko": "사사", "score": 0.47},
                ],
                "primary_match": {
                    "era_id": "modern_observational_field",
                    "label_ko": "현대",
                    "confidence_band": "high",
                },
            }
        ),
        encoding="utf-8",
    )
    (art / "logos_chronology_v1_latest.json").write_text(
        json.dumps(
            {
                "modern_bridges": [
                    {
                        "era_id": "judges_risk_cycle",
                        "bridge_kind": "regime_fingerprint",
                        "regime_id": "lehman",
                        "resonance_weight": 0.9,
                    },
                    {
                        "era_id": "modern_observational_field",
                        "bridge_kind": "chronology_window",
                        "window_id": "rate_hike_cycle",
                        "resonance_weight": 0.85,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (art / "logos_chronology_text_blind_v2_holdout_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "logos_chronology_text_blind_v2_holdout_v1",
                "policy": {"primary_oos_partition": "train_holdout"},
                "by_partition": {
                    "train_holdout": {
                        "text_blind_v1_ms_baseline": {"n": 20, "hit_at_1_strict": 0.1},
                        "text_blind_v2_btrack_poc": {"n": 20, "hit_at_1_strict": 0.9},
                        "delta_v2_minus_v1": 0.8,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (art / "prophecy_2050_two_track_v1_latest.json").write_text(
        json.dumps(
            {
                "track_a_trading_theory": {
                    "operational_bands": [
                        {"period": "2026-2030", "thesis": "High-volatility expansion with frequent regime flips."}
                    ]
                },
                "track_b_historical_omen": {
                    "era_signs": [
                        {
                            "period": "2026-2030",
                            "sign_cluster": "Acceleration and meaning-friction",
                            "interpretation": "Tech speed vs trust lag.",
                        },
                        {
                            "period": "2031-2040",
                            "sign_cluster": "System reconfiguration and narrative conflict",
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (art / "trackc_macro_risk_morning_briefing_latest.json").write_text(
        json.dumps(
            {
                "market_snapshot": {
                    "asset_scope": "BTC-USD",
                    "decision_state": "WATCH",
                    "risk_warning_level": "elevated",
                    "primary_regime_id": "post_covid_normalization",
                    "recommended_operator_posture": "watch_tighten",
                },
                "top_risk_signals": [{"name": "market_liquidity_stress", "score": 0.58}],
            }
        ),
        encoding="utf-8",
    )
    (art / "macro_risk_forward_weekly_report_latest.json").write_text(
        json.dumps({"rows_total": 3, "latest_row": {"decision_state": "WATCH"}, "decision_state_counts": {"WATCH": 2}}),
        encoding="utf-8",
    )
    (art / "general_prophecy_latest.json").write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "question_id": "gp_2026_h2_kostat_cpi_yoy_below_2_any_month",
                        "question_text": "CPI below 2?",
                        "forecasts": [{"probability_0_1": 0.42, "source_kind": "hybrid"}],
                        "resolution": {"status": "pending"},
                    },
                    {
                        "question_id": "gp_2026_h2_boj_policy_rate_above_1pct",
                        "question_text": "BoJ >1%?",
                        "forecasts": [{"probability_0_1": 0.48, "source_kind": "hybrid"}],
                        "resolution": {"status": "pending"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def _run_builder(art: Path, rep: Path, *, strict: bool = False) -> subprocess.CompletedProcess[str]:
    out_json = art / "logos_macro_horizon_2030_scenario_v1_latest.json"
    out_md = rep / "logos_macro_horizon_2030_scenario_v1_latest.md"
    cmd = [
        sys.executable,
        str(BUILDER),
        "--dynamic-map-json",
        str(art / "logos_chronology_dynamic_map_v1_latest.json"),
        "--chronology-json",
        str(art / "logos_chronology_v1_latest.json"),
        "--holdout-json",
        str(art / "logos_chronology_text_blind_v2_holdout_v1_latest.json"),
        "--two-track-json",
        str(art / "prophecy_2050_two_track_v1_latest.json"),
        "--macro-brief-json",
        str(art / "trackc_macro_risk_morning_briefing_latest.json"),
        "--forward-weekly-json",
        str(art / "macro_risk_forward_weekly_report_latest.json"),
        "--general-prophecy-json",
        str(art / "general_prophecy_latest.json"),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)


def test_build_logos_macro_horizon_2030_scenario_v1(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    rep = tmp_path / "reports"
    _write_fixture_tree(art)

    proc = _run_builder(art, rep, strict=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    doc = json.loads((art / "logos_macro_horizon_2030_scenario_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_macro_horizon_2030_scenario_v1"
    assert doc["version"] == "1.2.1"
    assert doc["scenario_kind"] == "narrative_template"
    assert doc["phases"][0]["track_a_thesis"] == "High-volatility expansion with frequent regime flips."
    assert doc["phases"][0]["track_a_phase_note"]
    assert doc["phases"][1]["track_b_forward_lean"] == "System reconfiguration and narrative conflict"
    assert doc["phases"][0]["track_b_sign"] == "Acceleration and meaning-friction"
    assert doc["scenario_probability_weights"]["global"]["base"] + doc["scenario_probability_weights"]["global"]["stress"] == 1.0
    assert "post_covid_normalization" in doc["conflict_resolver"]["summary_ko"]
    assert doc["chronology_evidence"]["holdout_internal_only"]["v2_btrack_hit_at_1_strict"] == 0.9
    assert "japan" in doc["tri_axis_scenarios"]
    assert "eu" in doc["tri_axis_scenarios"]
    assert doc["macro_forward_anchor"]["top_risk_signals"][0]["name"] == "market_liquidity_stress"
    assert doc["inputs"]["dynamic_map"]["sha256"] is not None


def test_build_logos_macro_horizon_2030_lens_wiring(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    rep = tmp_path / "reports"
    _write_fixture_tree(art)
    (art / "myeongni_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "lens_id": "myeongni",
                "scores": {"direction_score": 0.08, "confidence": 0.69},
                "myeongri_stream_outputs": {"state_id": 15},
                "ts_utc": "2026-06-07T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (art / "market_sasang_lens_latest.json").write_text(
        json.dumps(
            {
                "lens_id": "market_sasang",
                "state_vector_sasang_softmax": {"taeyang": 0.31, "soyang": 0.28, "taeeum": 0.2, "soeum": 0.21},
                "uncertainty": {"entropy_norm_4way": 0.99},
                "veto": {"force_hold": True, "reason_codes": ["HIGH_ENTROPY_SOFTMAX"]},
                "fusion_bridge": {"direction_hint": "bull"},
                "ts_utc": "2026-06-07T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    out_json = art / "logos_macro_horizon_2030_scenario_v1_latest.json"
    out_md = rep / "logos_macro_horizon_2030_scenario_v1_latest.md"
    cmd = [
        sys.executable,
        str(BUILDER),
        "--dynamic-map-json",
        str(art / "logos_chronology_dynamic_map_v1_latest.json"),
        "--chronology-json",
        str(art / "logos_chronology_v1_latest.json"),
        "--holdout-json",
        str(art / "logos_chronology_text_blind_v2_holdout_v1_latest.json"),
        "--two-track-json",
        str(art / "prophecy_2050_two_track_v1_latest.json"),
        "--macro-brief-json",
        str(art / "trackc_macro_risk_morning_briefing_latest.json"),
        "--forward-weekly-json",
        str(art / "macro_risk_forward_weekly_report_latest.json"),
        "--general-prophecy-json",
        str(art / "general_prophecy_latest.json"),
        "--myeongni-lens-json",
        str(art / "myeongni_independent_lens_latest.json"),
        "--sasang-lens-json",
        str(art / "market_sasang_lens_latest.json"),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    triad = doc["lens_triad_stub"]
    assert triad["myeongni"]["status"] == "read_only_snapshot"
    assert triad["sasang"]["status"] == "read_only_snapshot"
    assert triad["sasang"]["dominant_constitution"] == "taeyang"
    assert "명리 dir=" in (doc["conflict_resolver"].get("lens_supplement_ko") or "")


def test_build_logos_macro_horizon_2030_strict_fails_missing(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    rep = tmp_path / "reports"
    art.mkdir()
    rep.mkdir()
    proc = _run_builder(art, rep, strict=True)
    assert proc.returncode == 1
