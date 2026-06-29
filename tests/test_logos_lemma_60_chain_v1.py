"""Lemma-60 spike chain (B-track, HYPO)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
SPIKE = ROOT / "docs/final/artifacts/logos_lemma_anchor_spike_v1_latest.json"


@pytest.fixture(scope="module")
def lemma_60_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_lemma_60_chain_v1.py", "--skip-pytest", "--skip-baseline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_lemma_hit_anchors_at_least_sixty(lemma_60_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["lemma_hit_anchors"] >= 60


def test_lemma_spike_artifact(lemma_60_chain: None) -> None:
    doc = json.loads(SPIKE.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_lemma_anchor_spike_v1"
    assert doc["target_lemma_hit_anchors"] in (60, 100, 200, 300, 339)
    assert bridge["summary"]["lemma_hit_anchors"] >= doc["target_lemma_hit_anchors"]
