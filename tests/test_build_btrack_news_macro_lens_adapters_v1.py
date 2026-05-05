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
