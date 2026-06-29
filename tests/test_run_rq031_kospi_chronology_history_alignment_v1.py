# -*- coding: utf-8
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.run_rq031_kospi_chronology_history_alignment_v1 import (  # noqa: E402
    _daily_returns,
    _max_drawdown,
    _macro_landmarks,
    _pillar_a_regime_alignment,
    _window_stats,
    build_report,
)


def test_macro_landmarks_filters_tier() -> None:
    gold = {
        "events": [
            {"tier": "macro_landmark", "as_of_date": "2008-09-15", "event_id": "a"},
            {"tier": "narrative", "as_of_date": "2000-01-01", "event_id": "b"},
        ]
    }
    assert len(_macro_landmarks(gold)) == 1


def test_window_stats_and_drawdown() -> None:
    closes = {
        "2020-02-03": 100.0,
        "2020-02-04": 95.0,
        "2020-02-05": 90.0,
        "2020-02-06": 92.0,
        "2020-02-07": 91.0,
    }
    rets = _daily_returns(closes)
    stats = _window_stats(closes, rets, "2020-02-03", "2020-02-07")
    assert stats is not None
    assert stats["n_trading_days"] == 5
    assert stats["max_drawdown"] == _max_drawdown(closes, sorted(closes))


def test_build_report_smoke(tmp_path: Path) -> None:
    kospi = tmp_path / "kospi.csv"
    kospi.write_text(
        "date,open,high,low,close,volume\n"
        "1997-07-01,100,101,99,100,1\n"
        "1998-01-02,100,102,98,98,1\n"
        "2008-09-15,200,201,190,191,1\n"
        "2009-03-09,150,151,149,150,1\n"
        "2020-03-16,250,251,200,205,1\n"
        "2022-06-01,300,301,299,300,1\n",
        encoding="utf-8",
    )
    regime_map = _ROOT / "data/regimes/regime_map.json"
    quad = _ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
    gold = _ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not regime_map.is_file() or not quad.is_file() or not gold.is_file():
        return
    report = build_report(
        kospi_csv=kospi,
        regime_map=regime_map,
        quad_json=quad,
        gold_json=gold,
        era_blind_json=_ROOT / "reports/logos_chronology_era_blind_eval_v1_latest.json",
        brier_json=_ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
        chronology_json=_ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json",
    )
    assert report["schema"] == "rq031_kospi_chronology_history_alignment_v1"
    assert report["research_only"] is True
    assert report["auto_promote_ready"] is False
    assert "kospi_daily_directional_hit_rate" in report["not_measured"]
    assert report["pillar_a_regime_tag_alignment"]["n_macro_landmarks"] >= 1


def test_pillar_a_strict_match_logic() -> None:
    regime_map = _ROOT / "data/regimes/regime_map.json"
    quad = _ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
    gold_path = _ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not regime_map.is_file() or not quad.is_file() or not gold_path.is_file():
        return
    from scripts.run_rq031_kospi_chronology_history_alignment_v1 import (  # noqa: E402
        _load_json,
        _quad_year_vectors,
    )

    gold = _load_json(gold_path)
    assert gold
    year_vecs = _quad_year_vectors(quad)
    pillar = _pillar_a_regime_alignment(
        gold=gold,
        year_vecs=year_vecs,
        regime_map=regime_map,
        kospi_csv=_ROOT / "research/market_data/kospi_daily_external_yf.csv",
    )
    assert pillar["n_macro_landmarks"] >= 10
    cov = pillar.get("combined_primary_coverage_rate")
    if cov is not None:
        assert 0.0 <= cov <= 1.0
