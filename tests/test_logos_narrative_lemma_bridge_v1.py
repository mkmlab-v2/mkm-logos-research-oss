"""Narrative lemma bridge PoC — bidirectional atoms merged into lemma edges."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
REPORT = ROOT / "docs/final/artifacts/logos_narrative_lemma_bridge_v1_latest.json"


@pytest.fixture(scope="module")
def narrative_lemma_bridge_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_lemma_bridge_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_lemma_bridge_report_contract(narrative_lemma_bridge_chain: None) -> None:
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_narrative_lemma_bridge_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["inputs"]["narrative_verse_count"] >= 16
    assert doc["summary"]["edges_built"] >= 16
    assert doc["summary"]["verses_missing_atoms"] == 0


def test_narrative_lemma_bridge_increases_anchor_hits(narrative_lemma_bridge_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["lemma_hit_anchors"] >= 27


def test_narrative_hop_lemma_coverage_full(narrative_lemma_bridge_chain: None) -> None:
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    assert overlap["summary"]["hop_lemma_edge_hit_rate"] == 1.0
    assert overlap["summary"]["path_lemma_edge_coverage_rate"] == 1.0
    assert overlap["summary"]["path_full_bidirectional_coverage_rate"] == 1.0
