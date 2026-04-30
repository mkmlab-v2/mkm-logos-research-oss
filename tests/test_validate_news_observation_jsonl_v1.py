# Keywords: validate_news_observation_jsonl_v1, jsonl, B-track
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_news_observation_jsonl_v1.py"
NEWS_FIX = ROOT / "tests" / "fixtures" / "news_observation_v1.sample.jsonl"
LBL_FIX = ROOT / "tests" / "fixtures" / "direction_label_bar_v1.sample.jsonl"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_cli_ok_on_sample_fixtures():
    r = _run(
        "--news-jsonl",
        str(NEWS_FIX),
        "--labels-jsonl",
        str(LBL_FIX),
        "--verify-label-hashes",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_cli_fails_on_bad_text_sha256(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    row = json.loads(NEWS_FIX.read_text(encoding="utf-8").splitlines()[0])
    row["text_sha256"] = "0" * 64
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    r = _run("--news-jsonl", str(bad))
    assert r.returncode != 0


def test_cli_fails_on_as_of_before_published(tmp_path: Path):
    bad = tmp_path / "bad2.jsonl"
    row = json.loads(NEWS_FIX.read_text(encoding="utf-8").splitlines()[0])
    row["as_of_utc"] = "2020-01-01T00:00:00Z"
    row["published_utc"] = "2024-06-03T02:00:00Z"
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    r = _run("--news-jsonl", str(bad))
    assert r.returncode != 0
    assert "as_of_utc" in r.stderr or "published_utc" in r.stderr


def test_labels_only_mode():
    r = _run("--labels-jsonl-only", "--labels-jsonl", str(LBL_FIX), "--verify-label-hashes")
    assert r.returncode == 0, r.stderr + r.stdout
