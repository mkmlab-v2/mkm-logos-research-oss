"""Tests for B-track news/macro lens adapter (deterministic scores)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def mod():
    import scripts.build_btrack_news_macro_lens_adapters_v1 as m

    return m


def test_news_headline_tilt_bull(mod, tmp_path: Path) -> None:
    pre = tmp_path / "pre.json"
    pre.write_text(
        json.dumps(
            {
                "schema": "pre_news_shadow_input_v1",
                "rows": [{"headline": "Equity rally continues after stabilization measures"}],
            }
        ),
        encoding="utf-8",
    )
    nout = tmp_path / "news.json"
    mout = tmp_path / "macro.json"
    assert (
        mod.main(
            [
                "--pre-news-input",
                str(pre),
                "--external-feed",
                str(pre),
                "--news-out",
                str(nout),
                "--macro-out",
                str(mout),
            ]
        )
        == 0
    )
    news = json.loads(nout.read_text(encoding="utf-8"))
    assert news["schema"] == "news_independent_lens_v0"
    assert news["scores"]["direction_score"] > 0


def test_macro_empty_feed_zero(mod, tmp_path: Path) -> None:
    feed = tmp_path / "feed.json"
    feed.write_text(json.dumps({"schema": "external_feed_drop_v1", "data": []}), encoding="utf-8")
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"schema": "pre_news_shadow_input_v1", "rows": []}), encoding="utf-8")
    nout = tmp_path / "news.json"
    mout = tmp_path / "macro.json"
    assert (
        mod.main(
            [
                "--pre-news-input",
                str(pre),
                "--external-feed",
                str(feed),
                "--news-out",
                str(nout),
                "--macro-out",
                str(mout),
            ]
        )
        == 0
    )
    macro = json.loads(mout.read_text(encoding="utf-8"))
    assert macro["scores"]["direction_score"] == 0.0
    assert macro["scores"]["confidence"] == 0.0


def test_naver_news_feed_contributes_to_news_score(mod, tmp_path: Path) -> None:
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"schema": "pre_news_shadow_input_v1", "rows": []}), encoding="utf-8")
    feed = tmp_path / "feed.json"
    feed.write_text(json.dumps({"schema": "external_feed_drop_v1", "data": []}), encoding="utf-8")
    naver_news = tmp_path / "naver_news.json"
    external_news = tmp_path / "external_news.json"
    external_news.write_text(
        json.dumps(
            {
                "schema": "external_news_feed_v1",
                "data": [{"title": "Global macro tightening pressure", "description": ""}],
            }
        ),
        encoding="utf-8",
    )
    naver_news.write_text(
        json.dumps(
            {
                "schema": "naver_news_feed_v1",
                "data": [{"title": "Risk-off shock declines across equities", "description": ""}],
            }
        ),
        encoding="utf-8",
    )
    nout = tmp_path / "news.json"
    mout = tmp_path / "macro.json"
    assert (
        mod.main(
            [
                "--pre-news-input",
                str(pre),
                "--external-feed",
                str(feed),
                "--naver-news-feed",
                str(naver_news),
                "--external-news-feed",
                str(external_news),
                "--news-out",
                str(nout),
                "--macro-out",
                str(mout),
            ]
        )
        == 0
    )
    news = json.loads(nout.read_text(encoding="utf-8"))
    assert news["news_stream_outputs"]["naver_news_text_count"] >= 1
    assert news["news_stream_outputs"]["external_news_text_count"] >= 1
    assert news["scores"]["direction_score"] < 0


def test_naver_multi_group_signals_seed_macro(mod, tmp_path: Path) -> None:
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"schema": "pre_news_shadow_input_v1", "rows": []}), encoding="utf-8")
    feed = tmp_path / "feed.json"
    feed.write_text(json.dumps({"schema": "external_feed_drop_v1", "data": []}), encoding="utf-8")
    naver_signals = tmp_path / "naver_signals.json"
    external_macro = tmp_path / "external_macro.json"
    btc_market = tmp_path / "btc_market.json"
    btc_alt = tmp_path / "btc_alt.json"
    btc_market.write_text(
        json.dumps(
            {
                "schema": "btc_market_signals_v1",
                "market_micro_trend": {"trend": "down", "score": -0.5},
            }
        ),
        encoding="utf-8",
    )
    btc_alt.write_text(
        json.dumps(
            {
                "schema": "btc_alt_public_signals_v1",
                "alt_public_trend": {"trend": "up", "score": 0.33},
            }
        ),
        encoding="utf-8",
    )
    external_macro.write_text(
        json.dumps(
            {
                "schema": "external_macro_signals_v1",
                "macro_trend": {"trend": "down", "score": -0.25},
            }
        ),
        encoding="utf-8",
    )
    naver_signals.write_text(
        json.dumps(
            {
                "schema": "naver_openapi_signals_v1",
                "datalab_search_trend": {"trend": "flat"},
                "datalab_search_trend_per_group": [
                    {"group": "비트코인", "trend": "up", "weight": 0.5},
                    {"group": "환율", "trend": "down", "weight": 0.5},
                ],
            }
        ),
        encoding="utf-8",
    )
    nout = tmp_path / "news.json"
    mout = tmp_path / "macro.json"
    assert (
        mod.main(
            [
                "--pre-news-input",
                str(pre),
                "--external-feed",
                str(feed),
                "--naver-signals",
                str(naver_signals),
                "--external-macro-signals",
                str(external_macro),
                "--btc-market-signals",
                str(btc_market),
                "--btc-alt-public-signals",
                str(btc_alt),
                "--news-out",
                str(nout),
                "--macro-out",
                str(mout),
            ]
        )
        == 0
    )
    macro = json.loads(mout.read_text(encoding="utf-8"))
    assert macro["macro_stream_outputs"]["naver_signal_seed_count"] >= 3
    assert macro["macro_stream_outputs"]["external_macro_seed_count"] >= 1
    assert macro["macro_stream_outputs"]["btc_market_seed_count"] >= 1
    assert macro["macro_stream_outputs"]["btc_alt_public_seed_count"] >= 1
