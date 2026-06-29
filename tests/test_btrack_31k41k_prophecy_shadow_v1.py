"""B-track 31k/41k prophecy shadow feature + eval smoke tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_compute_features_from_fixtures(tmp_path: Path) -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    mapping = {"assignments": [{"verse_id": "Gen.1.1"}] * 16}
    logos = {
        "scores": {"direction_score": -0.2, "confidence": 0.25},
        "evidence_refs": [{"verse_id": "a"}],
        "logos_stream_outputs": {"verses_with_simple_4d": 3, "batch_rows_total": 3},
    }
    hypo = {
        "prediction": {"direction": "bear"},
        "runtime_meta": {
            "lens_values": {
                "price": {"score": -0.5},
                "macro": {"score": 0.1},
            }
        },
    }
    corpus = {
        "counting_layers": [
            {
                "id": "mkm_operational_baseline",
                "representative_values": {"normalized_lexicon_rows": 41658},
            }
        ]
    }
    mp = tmp_path / "map.json"
    lp = tmp_path / "logos.json"
    hp = tmp_path / "hypo.json"
    cp = tmp_path / "corpus.json"
    mp.write_text(json.dumps(mapping), encoding="utf-8")
    lp.write_text(json.dumps(logos), encoding="utf-8")
    hp.write_text(json.dumps(hypo), encoding="utf-8")
    cp.write_text(json.dumps(corpus), encoding="utf-8")

    features = mod.compute_all_features(
        logos_mapping_path=mp,
        logos_lens_path=lp,
        hypothesis_path=hp,
        corpus_baseline_path=cp,
    )
    assert features["logos_anchor_density_31k_v1"]["n_anchor_assignments"] == 16
    assert 0 < features["lexicon_coverage_41k_v1"]["value"] < 1
    assert features["anchor_conflict_ratio_v1"]["n_disagreeing"] == 1


def test_shadow_overlay_v2_not_global_on_all_rows() -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    rows = [
        {
            "instrument": "btc",
            "eval_date": "2026-05-01",
            "predicted_direction": "bull",
            "actual_direction": "bear",
            "daily_return": -0.02,
            "neutral_bps": 5.0,
        },
        {
            "instrument": "btc",
            "eval_date": "2026-05-02",
            "predicted_direction": "bull",
            "actual_direction": "bear",
            "daily_return": -0.02,
            "neutral_bps": 5.0,
        },
    ]
    logos = {"scores": {"direction_score": 0.5, "confidence": 0.9}}
    features = {
        "anchor_conflict_ratio_v1": {"value": 0.0},
        "logos_anchor_density_31k_v1": {"value": 0.001},
    }
    hypo = {"prediction": {"direction": "bear"}}
    v1 = mod.apply_shadow_overlay(rows, logos_lens=logos, features=features)
    v2 = mod.apply_shadow_overlay_v2(rows, logos_lens=logos, features=features, hypothesis=hypo)
    assert sum(1 for r in v1 if r.get("shadow_overlay_applied")) == len(rows)
    assert sum(1 for r in v2 if r.get("shadow_overlay_applied")) == 0


def test_v2c_skips_ensemble_when_move_matches_baseline() -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    row = {
        "instrument": "btc",
        "eval_date": "2026-04-30",
        "predicted_direction": "bull",
        "actual_direction": "bull",
        "daily_return": 0.007,
        "neutral_bps": 5.0,
    }
    v2 = mod.overlay_decision_detail(
        row,
        ensemble_dir="bear",
        logos_dir="bear",
        logos_conf=0.9,
        conflict_val=0.0,
        density_val=0.001,
        routing_policy="v2",
    )
    v2c = mod.overlay_decision_detail(
        row,
        ensemble_dir="bear",
        logos_dir="bear",
        logos_conf=0.9,
        conflict_val=0.0,
        density_val=0.001,
        routing_policy="v2c",
    )
    assert v2["routing_path"] == "align_ensemble_direction"
    assert v2["overlay_applied"] is True
    assert v2c["routing_path"] == "ensemble_skipped_move_matches_baseline"
    assert v2c["overlay_applied"] is False


def test_overlay_decision_detail_routing_path() -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    row = {
        "instrument": "btc",
        "eval_date": "2026-05-01",
        "predicted_direction": "bull",
        "actual_direction": "bear",
        "daily_return": -0.02,
        "neutral_bps": 5.0,
    }
    detail = mod.overlay_decision_detail(
        row,
        ensemble_dir="bear",
        logos_dir="bear",
        logos_conf=0.9,
        conflict_val=0.0,
        density_val=0.001,
    )
    assert detail["routing_path"] == "align_daily_move_sign"
    assert detail["overlay_applied"] is True


def test_rotating_sample_ids_differ_by_eval_date() -> None:
    ts = _load("btrack_31k41k_daily_anchor_timeseries_v1", "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")
    catalog = [f"V.{i}" for i in range(5000)]
    a = set(ts.rotating_sample_verse_ids("2026-05-01", 0, catalog, 64))
    b = set(ts.rotating_sample_verse_ids("2026-05-02", 1, catalog, 64))
    assert a != b
    assert len(a) == 64


def test_timeseries_panel_density_varies_by_move_sign() -> None:
    ts = _load("btrack_31k41k_daily_anchor_timeseries_v1", "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")
    verse_by_id = {
        "Gen.1.1": {"vector_4d": {"S": 0.9, "L": 0.5, "K": 0.2, "M": 0.1}, "gematria_normalized": 0.9},
        "Gen.1.2": {"vector_4d": {"S": 0.85, "L": 0.5, "K": 0.2, "M": 0.15}, "gematria_normalized": 0.88},
        "Gen.1.3": {"vector_4d": {"S": 0.1, "L": 0.5, "K": 0.2, "M": 0.9}, "gematria_normalized": 0.1},
    }
    bull_row = {
        "eval_date": "2026-05-01",
        "predicted_direction": "bull",
        "daily_return": 0.02,
        "neutral_bps": 5.0,
    }
    bear_row = dict(bull_row)
    bear_row["eval_date"] = "2026-05-02"
    bear_row["daily_return"] = -0.02
    r_bull = ts.compute_timeseries_row(
        bull_row,
        verse_by_id=verse_by_id,
        assignment_ids=["Gen.1.1", "Gen.1.2", "Gen.1.3"],
        canon_denominator=31102,
        lexicon_rows=41658,
    )
    r_bear = ts.compute_timeseries_row(
        bear_row,
        verse_by_id=verse_by_id,
        assignment_ids=["Gen.1.1", "Gen.1.2", "Gen.1.3"],
        canon_denominator=31102,
        lexicon_rows=41658,
    )
    assert r_bull["timeseries_ready"] is True
    assert r_bull["logos_anchor_density_31k_v1"]["value"] != r_bear["logos_anchor_density_31k_v1"]["value"]


def test_per_row_strict_ignores_global_density_boost() -> None:
    ts = _load("btrack_31k41k_daily_anchor_timeseries_v1", "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")
    panel_row = {
        "logos_anchor_density_31k_v1": {"value": 0.0},
        "lexicon_coverage_41k_v1": {"value": 0.5},
        "anchor_conflict_ratio_v1": {"value": 0.0},
    }
    global_features = {
        "logos_anchor_density_31k_v1": {"value": 0.01},
        "lexicon_coverage_41k_v1": {"value": 0.5},
        "anchor_conflict_ratio_v1": {"value": 0.0},
    }
    strict = ts.panel_row_to_overlay_features(
        panel_row, global_features, merge_policy="per_row_strict"
    )
    merged = ts.panel_row_to_overlay_features(
        panel_row, global_features, merge_policy="max_per_row_global"
    )
    assert strict["logos_anchor_density_31k_v1"]["value"] == 0.0
    assert merged["logos_anchor_density_31k_v1"]["value"] == 0.01


def test_v2b_merges_panel_density_with_global_conflict(tmp_path: Path) -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    ts = _load("btrack_31k41k_daily_anchor_timeseries_v1", "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")
    rows = [
        {
            "instrument": "btc",
            "eval_date": "2026-05-01",
            "predicted_direction": "bull",
            "actual_direction": "bear",
            "daily_return": -0.02,
            "neutral_bps": 5.0,
        }
    ]
    panel_row = {
        "eval_date": "2026-05-01",
        "feature_mode": "timeseries_v1",
        "logos_anchor_density_31k_v1": {"value": 0.0001},
        "lexicon_coverage_41k_v1": {"value": 0.0001},
        "anchor_conflict_ratio_v1": {"value": 0.0},
    }
    panel_by_date = {"2026-05-01": panel_row}
    logos = {"scores": {"direction_score": -0.5, "confidence": 0.9}}
    global_features = {
        "anchor_conflict_ratio_v1": {"value": 0.0},
        "logos_anchor_density_31k_v1": {"value": 0.001},
        "lexicon_coverage_41k_v1": {"value": 0.0001},
    }
    hypo = {"prediction": {"direction": "bear"}}
    out = mod.apply_shadow_overlay_v2b(
        rows,
        logos_lens=logos,
        features=global_features,
        hypothesis=hypo,
        panel_by_date=panel_by_date,
        panel_to_features=lambda pr: ts.panel_row_to_overlay_features(pr, global_features),
    )
    assert out[0]["shadow_overlay_applied"] is True


def test_fold_stability_blocked_folds(tmp_path: Path) -> None:
    wf = _load("prophecy_per_date_combo_wf", "scripts/run_prophecy_per_date_combo_walkforward_v1.py")
    dates = [f"2026-05-{d:02d}" for d in range(1, 11)]
    specs = wf._blocked_walkforward_folds(dates, 5)
    assert len(specs) == 4
    assert all(train and test for train, test in specs)


def test_gate_two_tier_decisions() -> None:
    gate_mod = _load(
        "check_btrack_31k41k_prophecy_shadow_gate_v1",
        "scripts/check_btrack_31k41k_prophecy_shadow_gate_v1.py",
    )
    d, ok, tier = gate_mod.resolve_gate_outcome(
        technical_passed=True,
        gate_mode="routine",
        human_signoff_ok=False,
        signoff_present=False,
    )
    assert d == gate_mod.DECISION_CANDIDATE
    assert ok is True
    assert tier == "technical_only"

    d2, ok2, _ = gate_mod.resolve_gate_outcome(
        technical_passed=True,
        gate_mode="allowlist_review",
        human_signoff_ok=False,
        signoff_present=False,
    )
    assert d2 == gate_mod.DECISION_PENDING_SIGNOFF
    assert ok2 is False

    d3, ok3, tier3 = gate_mod.resolve_gate_outcome(
        technical_passed=True,
        gate_mode="allowlist_review",
        human_signoff_ok=True,
        signoff_present=True,
    )
    assert d3 == gate_mod.DECISION_HUMAN_APPROVED
    assert ok3 is True
    assert tier3 == "allowlist_human_approved"


def test_contrast_audit_row_from_ab_multi() -> None:
    multi_path = ROOT / "docs/final/artifacts/btrack_31k41k_shadow_v2b_ab_multi_v1_latest.json"
    if not multi_path.is_file():
        return
    append_mod = _load(
        "append_btrack_31k41k_prophecy_shadow_log_v1",
        "scripts/append_btrack_31k41k_prophecy_shadow_log_v1.py",
    )
    multi_doc = json.loads(multi_path.read_text(encoding="utf-8-sig"))
    row = append_mod._contrast_audit_row(multi_doc)
    assert row is not None
    assert row["schema"] == "btrack_31k41k_prophecy_shadow_log_contrast_audit_v1"
    assert row["strict_reduces_overlay_vs_max"] is True
    assert row["overlay_v2b_strict"] == 0
    assert row["overlay_v2b_max_merge"] == 9


def test_shadow_overlay_changes_hit_rate(tmp_path: Path) -> None:
    mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    rows = [
        {"instrument": "btc", "predicted_direction": "bull", "actual_direction": "bear"},
        {"instrument": "btc", "predicted_direction": "bull", "actual_direction": "bear"},
    ]
    logos = {"scores": {"direction_score": -0.5, "confidence": 0.9}}
    features = {
        "anchor_conflict_ratio_v1": {"value": 0.0},
        "logos_anchor_density_31k_v1": {"value": 0.001},
    }
    overlaid = mod.apply_shadow_overlay(rows, logos_lens=logos, features=features)
    rate, hits, n = mod.hit_rate_for_predictions(overlaid, "shadow_predicted_direction")
    assert n == 2
    assert hits == 2
    assert rate == 1.0
