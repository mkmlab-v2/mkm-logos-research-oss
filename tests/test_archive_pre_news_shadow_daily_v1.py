"""Tests for pre_news archive + merged headline lookup."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.archive_pre_news_shadow_daily_v1 import archive_pre_news_snapshot
from scripts.btrack_macro_news_shock_headline_verify_lib_v1 import (
    headline_gt_for_session,
    load_merged_pre_news_doc,
)


def test_archive_and_merge_dedupe(tmp_path: Path) -> None:
    latest = tmp_path / "latest.json"
    archive = tmp_path / "archive.jsonl"
    latest.write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-06-26T10:00:00Z",
                "rows": [
                    {
                        "row_id": "a1",
                        "pub_date": "2026-06-26",
                        "headline": "코스피 급락 우려",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r1 = archive_pre_news_snapshot(latest_path=latest, archive_path=archive, archive_kst="2026-06-26")
    assert r1["appended"] == 1
    r2 = archive_pre_news_snapshot(latest_path=latest, archive_path=archive, archive_kst="2026-06-27")
    assert r2["appended"] == 0
    assert r2["skipped_duplicates"] == 1

    merged = load_merged_pre_news_doc(latest_path=latest, archive_path=archive)
    assert merged["n_rows"] == 1
    gt = headline_gt_for_session(merged, "2026-06-26", min_macro_hits=1, min_bear_hits=1)
    assert gt.get("headline_scorable") is True
    assert gt.get("n_headlines") == 1
