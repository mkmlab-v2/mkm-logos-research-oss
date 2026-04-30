# Keywords: check_news_label_join_temporal_v1, lookahead guard
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_news_label_join_temporal_v1.py"
PAIRED_NEWS = ROOT / "tests" / "fixtures" / "news_observation_v1.paired_join_smoke.jsonl"
PAIRED_LBL = ROOT / "tests" / "fixtures" / "direction_label_bar_v1.paired_join_smoke.jsonl"


def test_join_checker_ok_on_paired_fixtures():
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(PAIRED_NEWS),
            "--labels-jsonl",
            str(PAIRED_LBL),
            "--strict-as-of-date-before-label-date",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_join_checker_fails_when_same_day(tmp_path: Path):
    bad_news = tmp_path / "n.jsonl"
    bad_lbl = tmp_path / "l.jsonl"
    n = json.loads(PAIRED_NEWS.read_text(encoding="utf-8").splitlines()[0])
    l = json.loads(PAIRED_LBL.read_text(encoding="utf-8").splitlines()[0])
    l["label_date"] = "2024-06-02"
    bad_news.write_text(json.dumps(n, ensure_ascii=False) + "\n", encoding="utf-8")
    bad_lbl.write_text(json.dumps(l, ensure_ascii=False) + "\n", encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(bad_news),
            "--labels-jsonl",
            str(bad_lbl),
            "--strict-as-of-date-before-label-date",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
