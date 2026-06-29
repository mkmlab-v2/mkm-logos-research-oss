"""P4a narrative 60→64 (P4 round-2) curation + eval contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
SLICE = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
INTER = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"


@pytest.fixture(scope="module")
def p4a_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_path_p4a_chain_v1.py",
            "--skip-pytest",
            "--skip-router",
            "--skip-cdn-purge",
            "--skip-drift-baseline",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_sample_count_sixty_four(p4a_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 64
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in (
        "tribulation_to_deliverance_endurance",
        "weeping_to_healing_comfort",
        "wing_to_eagle_shelter",
        "worm_to_ashes_humility",
    ):
        assert sid in samples


def test_p4a_eval_contract(p4a_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["narrative_sample_count"] >= 64
    assert doc["summary"]["path_ok_rate"] == 1.0
    assert doc["summary"]["sample_pass_rate"] == 1.0


def test_p4a_bloom_presets(p4a_chain: None) -> None:
    doc = json.loads(SLICE.read_text(encoding="utf-8"))
    pmap = doc.get("preset_narrative_map") or {}
    assert pmap["motif_comfort"] == "weeping_to_healing_comfort"
    assert pmap["motif_humility"] == "worm_to_ashes_humility"
    assert len(doc.get("narrative_path_samples") or []) >= 64


def test_p4a_inter_hop_and_lemma(p4a_chain: None) -> None:
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    assert inter["summary"]["inter_hop_pair_count"] >= 66
    assert inter["summary"]["bridge_pair_rate"] == 1.0
    assert overlap["summary"]["hop_lemma_edge_hit_rate"] == 1.0
    assert overlap["summary"]["curated_bridge_pair_rate"] == 1.0
