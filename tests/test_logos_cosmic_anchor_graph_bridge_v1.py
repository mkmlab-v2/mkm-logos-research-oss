"""ADV-3 cosmic anchor GraphRAG bridge + Bible advancement closure."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"


@pytest.fixture(scope="module")
def adv3_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_bridge_schema_and_guards(adv3_chain: None) -> None:
    doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_cosmic_anchor_graph_bridge_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["materialize_batch"] is False
    assert doc["kernel_recipe_id"] == "gematria_bridge_v1"
    assert doc["anchor_count"] == 339


def test_narrative_samples_include_isa_to_jhn_light(adv3_chain: None) -> None:
    doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    samples = {s["sample_id"]: s for s in doc.get("narrative_path_samples") or []}
    assert "isa53_wound_to_jhn_light" in samples
    path = samples["isa53_wound_to_jhn_light"]["path"]
    verses = [hop["verse_ref"] for hop in path]
    assert "Isa.53.5" in verses
    assert "Jhn.1.5" in verses


def test_lemma_and_resonance_summary(adv3_chain: None) -> None:
    doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    summary = doc["summary"]
    assert summary["lemma_hit_anchors"] >= 15
    assert summary["meaning_graph_hit_anchors"] >= 50
    assert summary["narrative_sample_count"] >= 8
    assert summary["resonance_edge_count"] > 0


def test_completion_closure_artifact() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_bible_advancement_completion_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert closure["send_gate"] == "HOLD"
    assert closure["anchor_count"] == 339
    assert closure["dual_gate_all_research"] is True
