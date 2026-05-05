from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_news_observation_from_external_feed_v1.py"


def test_build_news_observation_from_external_feed_smoke(tmp_path: Path) -> None:
    external = tmp_path / "external.json"
    external.write_text(
        json.dumps(
            {
                "schema": "external_feed_drop_v1",
                "generated_at_utc": "2026-05-05T00:00:00Z",
                "source": {"provider": "manual"},
                "data": [
                    {
                        "id": "x1",
                        "published_utc": "2026-05-04T08:00:00Z",
                        "title": "KOSPI opens stronger on export demand",
                        "description": "Semiconductor cycle improves.",
                        "url": "https://example.com/news/1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    existing = tmp_path / "existing.jsonl"
    existing.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "seed-1",
                "as_of_utc": "2026-05-03T00:00:00Z",
                "published_utc": "2026-05-03T00:00:00Z",
                "source_id": "label_guided_seed",
                "canonical_text": "seed text",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": "2026-05-03T00:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--external-feed-json",
            str(external),
            "--append-existing-jsonl",
            str(existing),
            "--output-jsonl",
            str(out),
            "--dataset-partition",
            "locked_eval",
            "--validate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    result = json.loads(cp.stdout.strip())
    assert result.get("built_rows") == 1

    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in lines]
    assert len(rows) == 2
    external_rows = [r for r in rows if r.get("source_id") == "external_feed_manual"]
    assert len(external_rows) == 1
    assert external_rows[0].get("dataset_partition") == "locked_eval"

