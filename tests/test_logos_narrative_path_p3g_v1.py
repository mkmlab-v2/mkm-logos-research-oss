"""P3g narrative 24→28 curation + eval contract."""

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
def p3g_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_path_p3g_chain_v1.py",
            "--skip-pytest",
            "--skip-router",
            "--skip-cdn-purge",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_sample_count_twenty_eight(p3g_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 28
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in (
        "cloak_to_shelter_refuge",
        "cup_to_wine_covenant",
        "chains_to_deliverance_freedom",
        "bitterness_to_honey_sweetness",
    ):
        assert sid in samples


def test_p3g_eval_contract(p3g_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["narrative_sample_count"] >= 28
    assert doc["summary"]["path_ok_rate"] == 1.0
    assert doc["summary"]["sample_pass_rate"] == 1.0


def test_p3g_bloom_presets(p3g_chain: None) -> None:
    doc = json.loads(SLICE.read_text(encoding="utf-8"))
    pmap = doc.get("preset_narrative_map") or {}
    assert pmap["motif_refuge"] == "cloak_to_shelter_refuge"
    assert pmap["motif_freedom"] == "chains_to_deliverance_freedom"
    assert len(doc.get("narrative_path_samples") or []) >= 28


def test_p3g_inter_hop_and_lemma(p3g_chain: None) -> None:
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    assert inter["summary"]["inter_hop_pair_count"] >= 30
    assert inter["summary"]["bridge_pair_rate"] == 1.0
    assert overlap["summary"]["hop_lemma_edge_hit_rate"] == 1.0
    assert overlap["summary"]["curated_bridge_pair_rate"] == 1.0
