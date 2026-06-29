"""Smoke tests for G2-ext edge quality + Studio summary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_edge_join_quality_report_builds() -> None:
    out = ROOT / "reports/logos_corpus_sasang_edge_join_quality_v1_latest.json"
    cp = subprocess.run(
        [sys.executable, "scripts/build_logos_corpus_sasang_edge_join_quality_report_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_corpus_sasang_edge_join_quality_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert doc["summary"]["edge_total"] >= doc["summary"]["edges_touching_corpus"]


def test_studio_sasang_network_summary_builds() -> None:
    out = ROOT / "docs/final/artifacts/logos_studio_sasang_network_summary_v1_latest.json"
    cp = subprocess.run(
        [sys.executable, "scripts/build_logos_studio_sasang_network_summary_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_studio_sasang_network_summary_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert int(doc["headline"]["corpus_verse_count"]) >= 0
    assert isinstance(doc["cards"], list) and len(doc["cards"]) >= 3
