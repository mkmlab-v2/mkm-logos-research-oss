from __future__ import annotations

from datetime import date
from pathlib import Path

import scripts.kospi_premarket_dynamic_query_lib_v1 as dyn


def test_resolve_includes_base_and_rotational(tmp_path: Path, monkeypatch) -> None:
    cfg = {
        "schema": "kospi_premarket_news_ingest_v1",
        "news_queries": ["코스피", "뉴욕증시"],
        "rotational_boost_queries": ["AI 반도체", "유럽 증시", "유가"],
        "rotational_pick_count": 2,
        "max_distinct_news_queries": 10,
        "context_risk_off_boost": [],
        "context_kospi_shock_boost": [],
        "exa_queries": ["macro test"],
    }
    overnight = tmp_path / "overnight.json"
    overnight.write_text('{"composite_tilt": "mixed_overnight"}', encoding="utf-8")
    plan = dyn.resolve_premarket_news_queries(
        cfg,
        as_of=date(2026, 6, 29),
        overnight_path=overnight,
        kospi_csv=tmp_path / "missing.csv",
    )
    qs = plan["news_queries_resolved"]
    assert "코스피" in qs
    assert len(qs) >= 4
    assert len(plan["exa_queries_resolved"]) >= 1


def test_risk_off_and_kospi_shock_boost(tmp_path: Path) -> None:
    cfg = {
        "schema": "kospi_premarket_news_ingest_v1",
        "news_queries": ["코스피"],
        "rotational_boost_queries": [],
        "rotational_pick_count": 0,
        "max_distinct_news_queries": 12,
        "context_risk_off_boost": ["기술주 매도"],
        "context_kospi_shock_boost": ["코스피 급락"],
        "context_kospi_shock_threshold_pct": -2.0,
        "exa_queries": ["base exa"],
        "exa_risk_off_boost": ["ai derating"],
        "max_exa_queries": 4,
    }
    overnight = tmp_path / "overnight.json"
    overnight.write_text('{"composite_tilt": "risk_off_overnight"}', encoding="utf-8")
    kospi = tmp_path / "kospi.csv"
    kospi.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2026-06-25,1,1,1,100,1\n"
        "2026-06-26,1,1,1,95,1\n",
        encoding="utf-8",
    )
    plan = dyn.resolve_premarket_news_queries(
        cfg,
        as_of=date(2026, 6, 29),
        overnight_path=overnight,
        kospi_csv=kospi,
    )
    assert "기술주 매도" in plan["news_queries_resolved"]
    assert "코스피 급락" in plan["news_queries_resolved"]
    assert "ai derating" in plan["exa_queries_resolved"]
