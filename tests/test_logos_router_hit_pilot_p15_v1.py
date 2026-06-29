"""P15 router-hit pilot — 200 narratives with GraphRAG router overlap."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"
SLICE = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"


@pytest.fixture(scope="module")
def p15_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_router_hit_pilot_p15_chain_v1.py",
            "--skip-pytest",
            "--skip-cdn-purge",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_router_hit_rate_one(p15_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["narrative_sample_count"] >= 200
    assert doc["summary"]["router_hit_rate"] == 1.0
    assert doc["summary"]["router_hit_count"] == 200


def test_closure_synced_two_hundred(p15_chain: None) -> None:
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert closure["narrative_sample_count"] >= 200
    assert closure["narrative_path_eval"]["router_hit_rate"] == 1.0


def test_bloom_cap_unchanged_eighty(p15_chain: None) -> None:
    doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert doc.get("resonance_cap") == 88
    assert len(doc.get("resonance_edges_top") or []) == 80
    assert len(doc.get("narrative_path_samples") or []) >= 200
