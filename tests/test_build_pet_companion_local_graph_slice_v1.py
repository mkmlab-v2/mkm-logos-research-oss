"""Pet local graph slice cap smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_BUILDER = ROOT / "scripts/build_pet_companion_observation_bridge_registry_v1.py"
SLICE_BUILDER = ROOT / "scripts/build_pet_companion_local_graph_slice_v1.py"
OUT = ROOT / "docs/final/artifacts/pet_companion_local_graph_slice_v1_latest.json"


def test_pet_local_graph_slice_respects_cap():
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    cp = subprocess.run(
        [sys.executable, str(SLICE_BUILDER), "--max-nodes", "128", "--max-edges", "140"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "pet_companion_local_graph_slice_v1"
    assert doc["node_count"] <= 128
    assert doc["edge_count"] <= 140
