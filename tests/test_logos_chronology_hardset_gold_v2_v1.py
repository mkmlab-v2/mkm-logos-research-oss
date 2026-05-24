"""Hardset gold v2 builder + compare smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_v2_diversifies_era_ids(tmp_path: Path) -> None:
    news = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
    chrono = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
    if not news.is_file() or not chrono.is_file():
        return
    out = tmp_path / "gold_v2.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_logos_hardset_news_era_gold_v2_v1.py"),
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
    dist = doc.get("era_id_distribution") or {}
    assert doc["n_events"] >= 20
    assert len(dist) >= 2, f"expected diversified eras, got {dist}"


def test_hardset_mode_compare_runs(tmp_path: Path) -> None:
    news = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
    if not news.is_file():
        return
    out = tmp_path / "cmp.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_hardset_gold_mode_compare_v1.py"),
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
    assert "v1_uniform_modern" in doc and "v2_rank_top1" in doc
