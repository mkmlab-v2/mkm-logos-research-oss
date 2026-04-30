# Keywords: join_news_observation_direction_labels_walkforward_v1
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "join_news_observation_direction_labels_walkforward_v1.py"
NEWS_FIX = ROOT / "tests" / "fixtures" / "join_walkforward_smoke_v1.news.jsonl"
LAB_FIX = ROOT / "tests" / "fixtures" / "join_walkforward_smoke_v1.labels.jsonl"


def test_join_walkforward_smoke(tmp_path: Path):
    out = tmp_path / "joined.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(NEWS_FIX),
            "--labels-jsonl",
            str(LAB_FIX),
            "--instrument-id",
            "KOSPI",
            "--horizon",
            "1d",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    o0 = json.loads(lines[0])
    o1 = json.loads(lines[1])
    assert o0["label_date"] == "2024-01-03"
    assert o0["direction"] == "up"
    assert o1["label_date"] == "2024-01-05"
    assert o1["direction"] == "up"


def test_join_strict_all_fails_when_no_label(tmp_path: Path):
    # One news row as_of after last label
    news = tmp_path / "n.jsonl"
    news.write_text(
        '{"schema_version":"news_observation_v1",'
        '"observation_id":"33333333-3333-4333-8333-333333333301",'
        '"as_of_utc":"2024-12-30T12:00:00Z","published_utc":"2024-12-30T12:00:00Z",'
        '"source_id":"x","canonical_text":"z",'
        '"text_sha256":"82fd08fdb7a2207c41e223dbaa1fc9d5f28d34d1d503db5f7e41e0eb6d31c480",'
        '"ingested_at_utc":"2024-12-30T13:00:00Z",'
        '"dataset_partition":"train_holdout","hypothesis_tag":"[HYPO]"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "j.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--labels-jsonl",
            str(LAB_FIX),
            "--instrument-id",
            "KOSPI",
            "--horizon",
            "1d",
            "--output",
            str(out),
            "--strict-all",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
