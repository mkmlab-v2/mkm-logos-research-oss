"""Chronology era topology seed bundle tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_showroom_chronology_era_topology_seed_bundle_v1.py"
CHRONO = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)


def test_era_seed_bundle_includes_genesis_verses(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-artifact", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    node_ids = set(doc.get("node_ids") or [])
    assert any("Gen.1.1" in nid for nid in node_ids)
    assert any("Gen.3.6" in nid for nid in node_ids)
    genesis_verses = doc.get("era_verse_map", {}).get("genesis_order_and_fall") or []
    assert len(genesis_verses) == 2
    edges = doc.get("edges") or []
    assert any(
        e.get("src") == "era::genesis_order_and_fall" and e.get("edge_type") == "era_verse"
        for e in edges
    )
