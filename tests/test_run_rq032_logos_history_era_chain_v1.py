# -*- coding: utf-8
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.run_rq032_logos_history_era_chain_v1 import (  # noqa: E402
    _macro_landmarks,
    _pillar_a_era_blind,
    _pillar_b_quad_regime_only,
    _summarize_era_eval,
    build_report,
)


def test_macro_landmarks_filters_tier() -> None:
    gold = {
        "events": [
            {"tier": "macro_landmark", "as_of_date": "2008-09-15", "event_id": "a"},
            {"tier": "biblical_narrative", "as_of_date": "1000-01-01", "event_id": "b"},
        ]
    }
    assert len(_macro_landmarks(gold)) == 1


def test_summarize_era_eval_missing() -> None:
    out = _summarize_era_eval(None, label="x")
    assert out["status"] == "missing"


def test_pillar_a_dual_eval() -> None:
    gold_doc = {
        "summary": {
            "tag_mode": "gold_tags",
            "n_non_synthetic": 47,
            "hit_at_1_strict": 0.702128,
            "locked_eval_hit_at_1_strict": 0.454545,
        },
        "status": "ok",
    }
    blind_doc = {
        "summary": {
            "tag_mode": "text_blind",
            "n_non_synthetic": 47,
            "hit_at_1_strict": 0.06383,
            "locked_eval_hit_at_1_strict": 0.090909,
        },
        "status": "warning",
    }
    pillar = _pillar_a_era_blind(gold_tags_eval=gold_doc, text_blind_eval=blind_doc)
    assert pillar["kospi_removed"] is True
    assert pillar["ms_public_headline_metric"]["value"] == 0.090909
    assert pillar["gold_tags_eval"]["hit_at_1_strict"] == 0.702128


def test_build_report_smoke() -> None:
    regime_map = _ROOT / "data/regimes/regime_map.json"
    quad = _ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
    gold = _ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not regime_map.is_file() or not quad.is_file() or not gold.is_file():
        return
    report = build_report(
        regime_map=regime_map,
        quad_json=quad,
        gold_json=gold,
        chronology_json=_ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json",
        era_gold_tags_json=_ROOT / "reports/logos_chronology_era_blind_eval_v1_latest.json",
        era_text_blind_json=_ROOT
        / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_tier_v2_v1_latest.json",
        brier_json=_ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
    )
    assert report["schema"] == "rq032_logos_history_era_chain_v1"
    assert report["kospi_removed"] is True
    assert report["auto_promote_ready"] is False
    assert "kospi_daily_directional_hit_rate" in report["not_measured"]
    assert report["pillar_b_quad_regime_only"]["ohlcv_year_proxy_used"] is False
    assert report["pillar_a_era_blind_eval"]["gold_tags_eval"]["hit_at_1_strict"] is not None


def test_pillar_b_quad_only_no_ohlcv() -> None:
    regime_map = _ROOT / "data/regimes/regime_map.json"
    quad = _ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
    gold_path = _ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not regime_map.is_file() or not quad.is_file() or not gold_path.is_file():
        return
    from scripts.run_rq032_logos_history_era_chain_v1 import _load_json, _quad_year_vectors  # noqa: E402

    gold = _load_json(gold_path)
    assert gold
    year_vecs = _quad_year_vectors(quad)
    pillar = _pillar_b_quad_regime_only(gold=gold, year_vecs=year_vecs, regime_map=regime_map)
    assert pillar["kospi_removed"] is True
    assert pillar["n_macro_landmarks"] >= 10
    assert pillar.get("quad_coverage_rate") is not None
