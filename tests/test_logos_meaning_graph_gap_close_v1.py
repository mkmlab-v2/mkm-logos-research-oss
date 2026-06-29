"""Meaning graph 339/339 gap close (numbered-book verse refs)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


@pytest.fixture(scope="module")
def mg_gap_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_meaning_graph_gap_close_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_meaning_graph_full_cover(mg_gap_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["meaning_graph_hit_anchors"] == bridge["anchor_count"]


def test_numbered_book_stems_linked(mg_gap_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    by_stem = {r["file_stem"]: r for r in bridge["per_anchor"]}
    for stem in ("cross", "2chr_18_8", "stronghold"):
        assert int(by_stem[stem]["meaning_graph_edge_count"]) > 0
