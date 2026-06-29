from __future__ import annotations

import json
from pathlib import Path

import scripts.build_global_market_overnight_signals_v1 as overnight_mod
import scripts.fetch_naver_openapi_signals_v1 as naver_mod


def test_merge_news_feed_items_dedupes_by_title_and_link() -> None:
    batches = [
        (
            "코스피",
            [
                {"title": "KOSPI rises", "link": "https://a.example/1"},
                {"title": "KOSPI rises", "link": "https://a.example/1"},
            ],
        ),
        (
            "뉴욕증시",
            [
                {"title": "Wall St down", "link": "https://b.example/2"},
                {"title": "KOSPI rises", "link": "https://a.example/1"},
            ],
        ),
    ]
    merged = naver_mod.merge_news_feed_items(batches, max_items=10)
    assert len(merged) == 2
    assert merged[0]["query"] == "코스피"
    assert merged[1]["query"] == "뉴욕증시"


def test_load_premarket_profile_reads_config() -> None:
    doc = naver_mod.load_premarket_profile(naver_mod.PREMARKET_CONFIG)
    assert doc.get("schema") == "kospi_premarket_news_ingest_v1"
    assert "코스피" in (doc.get("news_queries") or [])


def test_build_overnight_prefers_fresher_yfinance_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "nasdaq.csv"
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2026-06-25,1,1,1,100,1\n"
        "2026-06-26,1,1,1,98,1\n",
        encoding="utf-8",
    )
    yf = overnight_mod._index_from_csv(csv_path, row_id="nasdaq", label_ko="나스닥", source="test")
    snap = {"id": "nasdaq", "session_date": "2026-06-03", "change_pct": -0.87}
    picked = overnight_mod._pick_fresher_index(yf, snap)
    assert picked is not None
    assert picked["session_date"] == "2026-06-26"
    assert picked.get("overrides_snapshot") is True


def test_build_overnight_injects_pre_news_headlines(tmp_path: Path) -> None:
    pre_news = tmp_path / "pre_news.json"
    pre_news.write_text(
        json.dumps(
            {
                "rows": [
                    {"headline": "뉴욕증시 약세 마감"},
                    {"headline": "코스피 반등 기대"},
                ]
            }
        ),
        encoding="utf-8",
    )
    headlines = overnight_mod._headlines_from_pre_news(pre_news)
    assert headlines[0] == "뉴욕증시 약세 마감"
    doc = overnight_mod.build_doc(nasdaq_csv=tmp_path / "missing.csv", pre_news_path=pre_news)
    assert doc["schema"] == "global_market_overnight_signals_v1"
    assert "뉴욕증시 약세 마감" in doc["news_headlines"]
