"""P17 bloom resonance_cap 120→128 — final scheduled deepen; narrative frozen at 200."""

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
HD_MISSION = ROOT / "docs/final/artifacts/logos_oracle_lemma_60_hd_mission_v1_latest.json"


@pytest.fixture(scope="module")
def p17_bloom_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_resonance_cap_p17_bloom_chain_v1.py",
            "--skip-pytest",
            "--skip-cdn-purge",
            "--skip-deploy",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_resonance_cap_one_hundred_twenty_eight(p17_bloom_chain: None) -> None:
    for path in (SLICE_ART, SLICE_PUBLIC):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("resonance_cap") == 128
        assert len(doc.get("resonance_edges_top") or []) == 128


def test_bloom_deepen_frozen_in_hd_mission(p17_bloom_chain: None) -> None:
    doc = json.loads(HD_MISSION.read_text(encoding="utf-8-sig"))
    assert doc["baseline_facts"]["resonance_cap"] == 128
    assert doc["baseline_facts"].get("bloom_deepen_frozen") is True
    assert doc["baseline_facts"].get("bloom_deepen_max_cap") == 128


def test_narrative_still_two_hundred(p17_bloom_chain: None) -> None:
    doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert len(doc.get("narrative_path_samples") or []) >= 200
