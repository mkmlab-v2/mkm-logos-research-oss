"""Smoke tests for Logos news theme overlay (keyword mapping)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_theme_overlay_matches_fire_keyword(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    row = {
        "schema_version": "news_observation_v1",
        "observation_id": "00000000-0000-4000-8000-000000000001",
        "as_of_utc": "2026-06-01T00:00:00Z",
        "published_utc": "2026-06-01T00:00:00Z",
        "source_id": "korea_disaster_exa",
        "canonical_text": "경북 산불 진화 완료",
        "text_sha256": "a" * 64,
        "ingested_at_utc": "2026-06-04T00:00:00Z",
        "dataset_partition": "train_holdout",
        "hypothesis_tag": "[HYPO]",
    }
    news.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "overlay.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_logos_news_theme_overlay_v1.py"),
            "--news-jsonl",
            str(news),
            "--date-from",
            "2026-06-02",
            "--date-to",
            "2026-06-02",
            "--lag-days",
            "7",
            "-o",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_news_theme_overlay_v1"
    assert doc["labels"] == ["HYPO", "NON_GATING", "research_only"]
    day = doc["days"][0]
    slugs = {t["theme_slug"] for t in day["themes"]}
    assert "elijah_carmel" in slugs
