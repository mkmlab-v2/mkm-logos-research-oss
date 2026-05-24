"""Hardset news gold builder + modern_boost AB smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_hardset_gold_and_text_blind_eval(tmp_path: Path) -> None:
    news = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
    chrono = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
    if not news.is_file() or not chrono.is_file():
        return

    gold_out = tmp_path / "hardset_gold.json"
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_hardset_news_era_gold_v1.py"), "--output-json", str(gold_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    gold = json.loads(gold_out.read_text(encoding="utf-8"))
    assert gold["n_events"] >= 20

    eval_out = tmp_path / "hardset_eval.json"
    cp2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"),
            "--gold-json",
            str(gold_out),
            "--chronology-json",
            str(chrono),
            "--tag-mode",
            "text_blind",
            "--output-json",
            str(eval_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp2.returncode == 0, cp2.stderr
    ev = json.loads(eval_out.read_text(encoding="utf-8"))
    assert ev["summary"]["n_non_synthetic"] == gold["n_events"]
    assert ev["summary"]["hit_at_1_strict"] is not None


def test_modern_boost_ab_runs(tmp_path: Path) -> None:
    gold = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not gold.is_file():
        return
    out = tmp_path / "ab.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_chronology_era_modern_boost_ab_v1.py"),
            "--gold-json",
            str(gold),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_era_modern_boost_ab_v1"
    assert "boost_on" in doc["variants"]
