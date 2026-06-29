"""B-track narrative × lemma overlap eval — 8 paths vs sparse lemma + 41k bi-index."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


@pytest.fixture(scope="module")
def lemma_overlap_chain() -> None:
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


def test_narrative_lemma_overlap_artifact_contract(lemma_overlap_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_narrative_lemma_overlap_eval_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["send_gate"] == "HOLD"
    assert doc["narrative_sample_count"] >= 8
    assert doc["inputs"]["lexicon_row_count"] == 41658
    assert doc["summary"]["hop_bidirectional_atom_hit_rate"] == 1.0
    assert doc["summary"]["path_full_bidirectional_coverage_rate"] == 1.0
    assert doc["summary"]["total_hops"] >= 16


def test_narrative_lemma_edge_hit_rate_full_coverage(lemma_overlap_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    rate = doc["summary"]["hop_lemma_edge_hit_rate"]
    assert rate == 1.0
    assert doc["summary"].get("curated_bridge_pair_rate", 0) == 1.0
    assert doc["summary"].get("mean_inter_hop_bridge_lemma_jaccard", 0) >= 0.5


def test_bridge_narrative_ids_present(lemma_overlap_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    sample_ids = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    eval_ids = {s["sample_id"] for s in json.loads(EVAL.read_text(encoding="utf-8"))["samples"]}
    assert eval_ids == sample_ids
