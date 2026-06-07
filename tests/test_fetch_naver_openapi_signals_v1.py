from __future__ import annotations

import scripts.fetch_naver_openapi_signals_v1 as mod


def test_build_trend_payload_accepts_multiple_keywords() -> None:
    payload = mod._build_trend_payload(["비트코인", "코스피", "환율"], lookback_days=30)
    groups = payload.get("keywordGroups")
    assert isinstance(groups, list)
    assert len(groups) == 3
    assert groups[0]["groupName"] == "비트코인"


def test_build_signals_doc_has_per_group_entries() -> None:
    datalab_resp = {
        "results": [
            {"title": "비트코인", "data": [{"ratio": 10.0}, {"ratio": 20.0}]},
            {"title": "환율", "data": [{"ratio": 30.0}, {"ratio": 25.0}]},
        ]
    }
    weights = {"비트코인": 0.7, "환율": 0.3}
    doc = mod._build_signals_doc(["비트코인", "환율"], weights, datalab_resp, lookback_days=30)
    assert doc["schema"] == "naver_openapi_signals_v1"
    per_group = doc["datalab_search_trend_per_group"]
    assert isinstance(per_group, list)
    assert len(per_group) == 2
    assert set(x["group"] for x in per_group) == {"비트코인", "환율"}
    assert doc["trend_weights"]["비트코인"] == 0.7
    assert "datalab_search_trend_weighted" in doc


def test_parse_trend_weights_normalizes_and_filters() -> None:
    out = mod._parse_trend_weights("비트코인=2,코스피=1,환율=1", ["비트코인", "코스피", "환율"])
    assert round(out["비트코인"], 6) == 0.5
    assert round(out["코스피"], 6) == 0.25
    assert round(out["환율"], 6) == 0.25


def test_parse_trend_weights_defaults_to_uniform_when_empty() -> None:
    out = mod._parse_trend_weights("", ["비트코인", "코스피", "환율"])
    assert round(out["비트코인"], 6) == round(1.0 / 3.0, 6)
    assert round(out["코스피"], 6) == round(1.0 / 3.0, 6)
    assert round(out["환율"], 6) == round(1.0 / 3.0, 6)


def test_sync_pre_news_shadow_input_writes_rows(tmp_path) -> None:
    news_doc = {
        "schema": "naver_news_feed_v1",
        "ts_utc": "2026-06-07T00:00:00Z",
        "query": "macro",
        "items_count": 2,
        "data": [
            {"title": "Headline A", "link": "https://example.com/a", "pub_date": "Mon, 01 Jan 2024"},
            {"title": "Headline B", "source": "naver"},
        ],
    }
    out = tmp_path / "pre_news_shadow_input_latest.json"
    n = mod._sync_pre_news_shadow_input(news_doc, out)
    assert n == 2
    payload = __import__("json").loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "pre_news_shadow_input_v1"
    assert payload["research_only"] is True
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["headline"] == "Headline A"
