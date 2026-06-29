"""P3c narrative 8→12 curation + eval contract."""

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


@pytest.fixture(scope="module")
def p3c_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_path_p3c_chain_v1.py",
            "--skip-pytest",
            "--skip-router",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_sample_count_twelve(p3c_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 12
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in (
        "shepherd_to_door_pastoral",
        "blood_to_cross_covenant",
        "fire_to_rock_refuge",
        "cross_to_lamb_redeemer",
    ):
        assert sid in samples


def test_p3c_eval_contract(p3c_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["narrative_sample_count"] >= 12
    assert doc["summary"]["path_ok_rate"] == 1.0
    assert doc["summary"]["sample_pass_rate"] == 1.0


def test_p3c_bloom_presets(p3c_chain: None) -> None:
    doc = json.loads(SLICE.read_text(encoding="utf-8"))
    pmap = doc.get("preset_narrative_map") or {}
    assert pmap["motif_shepherd"] == "shepherd_to_door_pastoral"
    assert pmap["motif_covenant"] == "blood_to_cross_covenant"
    assert len(doc.get("narrative_path_samples") or []) >= 12


def test_p3c_inter_hop_pairs(p3c_chain: None) -> None:
    doc = json.loads(INTER.read_text(encoding="utf-8"))
    assert doc["summary"]["inter_hop_pair_count"] >= 14
    assert doc["summary"]["bridge_pair_rate"] == 1.0
