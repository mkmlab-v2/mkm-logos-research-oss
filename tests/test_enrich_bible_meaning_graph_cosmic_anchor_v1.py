"""Cosmic-anchor verse enrichment for bible_meaning_graph (HYPO)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENRICH_STATS = ROOT / "docs/final/artifacts/bible_meaning_graph_cosmic_anchor_enrich_v1_latest.json"


@pytest.fixture(scope="module")
def enrich_once() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_enrich_stats_idempotent_second_run(enrich_once: None) -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    stats = json.loads(ENRICH_STATS.read_text(encoding="utf-8"))
    assert stats["nodes_appended"] == 0
    assert stats["edges_appended"] == 0


def test_enrich_dry_run_reports_new_verse_nodes() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py",
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout)
    assert doc["schema"] == "bible_meaning_graph_cosmic_anchor_enrich_v1"
    assert doc["new_verse_nodes"] >= 0
