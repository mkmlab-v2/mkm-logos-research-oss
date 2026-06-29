"""P3b narrative path eval (B-track, not Track A alignment_pass_rate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


@pytest.fixture(scope="module")
def p3b_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_path_eval_chain_v1.py",
            "--skip-pytest",
            "--skip-router",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_sample_count_eight(p3b_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 8
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in (
        "isa53_wound_to_jhn_light",
        "wrath_to_healing_restoration",
        "vine_to_door_abiding_access",
        "living_water_to_well_jhn4",
        "harbor_to_tent_sojourn",
    ):
        assert sid in samples


def test_narrative_eval_artifact_contract(p3b_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_narrative_path_eval_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["narrative_sample_count"] >= 8
    assert doc["summary"]["path_ok_rate"] == 1.0
    assert doc["summary"]["sample_pass_rate"] == 1.0
    assert doc["summary"]["router_hit_rate"] == 1.0


def test_bloom_slice_preset_restoration_map(p3b_chain: None) -> None:
    slice_path = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
    doc = json.loads(slice_path.read_text(encoding="utf-8"))
    assert doc["preset_narrative_map"]["motif_restoration"] == "wrath_to_healing_restoration"
    assert len(doc.get("narrative_path_samples") or []) >= 8
