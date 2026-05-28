"""Lane contract for Logos vs Pet subgraph routers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_graph_subgraph_router_lane_contract_v1.py"
OUT = ROOT / "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json"


def test_build_lane_contract_has_dual_lanes_and_prohibitions():
    cp = subprocess.run([sys.executable, str(BUILDER)], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "graph_subgraph_router_lane_contract_v1"
    assert "logos_bible" in doc["lanes"]
    assert "pet_b2c_device" in doc["lanes"]
    assert len(doc["four_prohibition_lines"]) >= 4
    pet = doc["lanes"]["pet_b2c_device"]
    assert "mkm_ops_memory_graph" in pet["must_not_merge_with"]
