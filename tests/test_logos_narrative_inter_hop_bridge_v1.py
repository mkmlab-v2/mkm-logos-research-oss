"""Narrative inter-hop bridge curation — curated bridge lemma overlap."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"


@pytest.fixture(scope="module")
def inter_hop_bridge_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_inter_hop_bridge_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_inter_hop_bridge_artifact_contract(inter_hop_bridge_chain: None) -> None:
    doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_narrative_inter_hop_bridge_v1"
    assert doc["summary"]["inter_hop_pair_count"] >= 18
    assert doc["summary"]["bridge_pair_rate"] == 1.0
    assert doc["summary"]["lemma_edges_built"] >= 10


def test_inter_hop_bridge_overlap_metrics(inter_hop_bridge_chain: None) -> None:
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    summary = overlap["summary"]
    assert summary["curated_bridge_pair_rate"] == 1.0
    assert summary["mean_inter_hop_bridge_lemma_jaccard"] >= 0.5
    assert summary["hop_lemma_edge_hit_rate"] == 1.0


def test_curated_pairs_have_shared_bridge_lemmas(inter_hop_bridge_chain: None) -> None:
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    for sample in overlap["samples"]:
        for pair in sample["inter_hop"]:
            assert pair["curated_bridge_pair"] is True
            assert pair["shared_bridge_lemma_count"] >= 1
