# Keywords: build_news_observation_jsonl_from_csv_v1
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_news_observation_jsonl_from_csv_v1.py"


def test_csv_to_jsonl_roundtrip_validates(tmp_path: Path):
    csv_path = tmp_path / "in.csv"
    out_path = tmp_path / "out.jsonl"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "published_utc",
                "source_id",
                "canonical_text",
                "dataset_partition",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "published_utc": "2025-01-15T09:00:00Z",
                "source_id": "test_feed",
                "canonical_text": "CSV ingest smoke line.",
                "dataset_partition": "train_holdout",
            }
        )

    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(csv_path), "--output", str(out_path), "--validate"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_path.is_file()
    assert "news_observation_v1" in out_path.read_text(encoding="utf-8")
