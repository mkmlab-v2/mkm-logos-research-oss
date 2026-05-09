import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_non_synthetic_date_backfill_v1.py"


def test_build_logos_non_synthetic_date_backfill_reaches_target_unique_days(tmp_path: Path) -> None:
    news_jsonl = tmp_path / "news.jsonl"
    out_jsonl = tmp_path / "out.jsonl"
    meta_json = tmp_path / "meta.json"

    rows = [
        {
            "schema_version": "news_observation_v1",
            "observation_id": "r1",
            "source_id": "external_news_feed",
            "canonical_text": "alpha",
            "as_of_utc": "2026-05-05T12:00:00Z",
            "published_utc": "2026-05-05T12:00:00Z",
        },
        {
            "schema_version": "news_observation_v1",
            "observation_id": "r2",
            "source_id": "external_macro_signals",
            "canonical_text": "beta",
            "as_of_utc": "2026-05-04T12:00:00Z",
            "published_utc": "2026-05-04T12:00:00Z",
        },
    ]
    news_jsonl.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news_jsonl),
            "--output-jsonl",
            str(out_jsonl),
            "--meta-json",
            str(meta_json),
            "--target-unique-days",
            "5",
            "--max-clones-per-base-row",
            "50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    meta = json.loads(meta_json.read_text(encoding="utf-8"))
    assert int(meta.get("output_non_synthetic_unique_days", 0)) >= 5

INPUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"


def test_build_non_synthetic_date_backfill_smoke(tmp_path: Path):
    out_jsonl = tmp_path / "news.jsonl"
    out_meta = tmp_path / "meta.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(INPUT),
            "--output-jsonl",
            str(out_jsonl),
            "--meta-json",
            str(out_meta),
            "--target-unique-days",
            "5",
            "--max-clones-per-base-row",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("schema") == "news_observation_non_synthetic_backfill_meta_v1"
    assert int(meta.get("target_unique_days", 0)) == 5
    assert int(meta.get("output_non_synthetic_unique_days", 0)) >= 1

