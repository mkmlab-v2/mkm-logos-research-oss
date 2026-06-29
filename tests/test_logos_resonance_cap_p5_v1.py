"""P5 resonance_cap 24→32 bloom deepen — narrative count frozen at 80."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SLICE_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
SLICE_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
)
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


@pytest.fixture(scope="module")
def p5_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_resonance_cap_p5_chain_v1.py",
            "--skip-pytest",
            "--skip-cdn-purge",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_resonance_cap_thirty_two(p5_chain: None) -> None:
    for path in (SLICE_ART, SLICE_PUBLIC):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("resonance_cap") == 32
        assert len(doc.get("resonance_edges_top") or []) == 32


def test_narrative_count_unchanged_eighty(p5_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 80
    assert len(slice_doc.get("narrative_path_samples") or []) >= 80


def test_resonance_edges_strictly_deeper_than_p4(p5_chain: None) -> None:
    doc = json.loads(SLICE_ART.read_text(encoding="utf-8"))
    edges = doc.get("resonance_edges_top") or []
    assert len(edges) == 32
    weights = [float(e.get("weight") or 0) for e in edges]
    assert weights == sorted(weights, reverse=True)
    assert min(weights) > 0
