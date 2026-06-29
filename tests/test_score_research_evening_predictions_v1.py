"""R-IBL Phase 2 evening multi-lens scorer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import score_research_evening_predictions_v1 as scorer


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    lines = ["date,open,high,low,close,volume"]
    for d, c in rows:
        lines.append(f"{d},{c},{c},{c},{c},1000")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_score_research_seal_price_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path
    kospi = ws / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = ws / "research" / "market_data" / "btc_daily_external_yf.csv"
    _write_csv(kospi, [("2026-06-01", 2500.0), ("2026-06-02", 2550.0)])
    _write_csv(btc, [("2026-06-01", 90000.0), ("2026-06-02", 91000.0)])

    seal_dir = ws / "reports" / "briefing_log"
    seal_dir.mkdir(parents=True)
    registry = {
        "schema": "research_morning_prediction_registry_v1",
        "calendar_kst": "2026-06-02",
        "seal_id": "testseal1234",
        "predictions": [
            {
                "prediction_id": "pred_2026-06-02_price_btrack_hypothesis",
                "lens": "price_btrack",
                "kind": "kospi_directional",
                "direction_proxy": "bull",
                "score_against": "research/market_data/kospi_daily_external_yf.csv",
            },
            {
                "prediction_id": "pred_2026-06-02_logos_graphrag_q01",
                "lens": "logos",
                "kind": "graphrag_path_hit",
                "evidence_path": "reports/subgraph_replay/subgraph_router_replay_q01.json",
            },
        ],
    }
    replay = ws / "reports" / "subgraph_replay"
    replay.mkdir(parents=True)
    (replay / "subgraph_router_replay_q01.json").write_text(
        json.dumps({"pass": True, "paths_count": 3}), encoding="utf-8"
    )
    seal_path = seal_dir / "2026-06-02_research_seal_v1.json"
    seal_path.write_text(
        json.dumps({"schema": "research_morning_seal_archive_v1", "registry": registry}),
        encoding="utf-8",
    )

    import scripts.multi_asset_market_adapter_v1 as ma

    monkeypatch.setattr(ma, "ROOT", ws)
    monkeypatch.setattr(ma, "KOSPI_CSV", kospi)
    monkeypatch.setattr(ma, "BTC_CSV", btc)
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: None)

    doc = scorer.score_research_evening(seal_path, workspace=ws)
    assert doc["schema"] == "evening_multi_lens_score_v1"
    assert doc["seal_id"] == "testseal1234"
    by_id = {p["prediction_id"]: p for p in doc["prediction_scores"]}
    assert by_id["pred_2026-06-02_price_btrack_hypothesis"]["price_axis"] == "HIT"
    assert by_id["pred_2026-06-02_logos_graphrag_q01"]["outcome"] == "HIT"
    assert doc["stats_by_lens"]["price_btrack"]["HIT"] == 1


def test_resolve_research_seal_path() -> None:
    p = scorer.resolve_research_seal("2026-06-01")
    assert p.name == "2026-06-01_research_seal_v1.json"


def test_graphrag_hit_without_top_level_pass(tmp_path: Path) -> None:
    ws = tmp_path
    replay = ws / "reports" / "subgraph_replay"
    replay.mkdir(parents=True)
    (replay / "subgraph_router_replay_q99.json").write_text(
        json.dumps(
            {
                "schema": "logos_subgraph_graphrag_router_v1",
                "bridges_matched": 2,
                "paths": [{"path_id": "p1"}],
            }
        ),
        encoding="utf-8",
    )
    pred = {
        "prediction_id": "pred_x",
        "lens": "logos",
        "kind": "graphrag_path_hit",
        "evidence_path": "reports/subgraph_replay/subgraph_router_replay_q99.json",
    }
    row = scorer._score_logos_graphrag(pred, ws)
    assert row["outcome"] == "HIT"


def test_resolve_morning_market_seal_from_briefing_archive(tmp_path: Path) -> None:
    ws = tmp_path
    log = ws / "reports" / "briefing_log"
    log.mkdir(parents=True)
    seal_price = 95000.0
    (log / "2026-06-03_morning_briefing_v1.json").write_text(
        json.dumps(
            {
                "schema": "commander_morning_briefing_archive_v1",
                "calendar_kst": "2026-06-03",
                "briefing": {"calendar_kst": "2026-06-03", "market_seal": {"btc_usd": {"price": seal_price}}},
            }
        ),
        encoding="utf-8",
    )
    ms, src = scorer._resolve_morning_market_seal("2026-06-03", workspace=ws, envelope={})
    assert ms is not None
    assert ms["btc_usd"]["price"] == seal_price
    assert "morning_briefing" in src


def test_build_evening_telegram_korean_labels() -> None:
    score = {
        "calendar_kst": "2026-06-10",
        "seal_id": "abc123",
        "multi_asset": {
            "kospi": {"direction": "up", "return_pct": 0.5},
            "btc": {"direction": "down", "return_pct": -1.2},
        },
        "summary": {
            "n_predictions": 2,
            "price_axis_HIT": 1,
            "price_axis_FAIL": 0,
            "price_axis_NEUTRAL_DRAW": 1,
            "price_soft_hit_rate": 0.75,
        },
        "stats_by_lens": {
            "logos": {"n": 1, "soft_hit_rate": 1.0},
            "myeongni": {"n": 1, "soft_hit_rate": 0.5},
        },
        "data_source": {},
    }
    text = scorer.build_evening_telegram(score)
    assert "MKM 저녁 채점" in text
    assert "코스피 상승" in text
    assert "비트코인 하락" in text
    assert "가격축 적중=" in text
    assert "성경" in text
    assert "명리" in text
    assert "HIT=" not in text
    assert "FAIL=" not in text
    assert "Binance shadow" not in text
    assert "research_only" not in text
