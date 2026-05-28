"""Apply pet device bridge hints to local graph slice."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts/apply_pet_companion_bridge_hints_to_local_graph_v1.py"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/pet_companion_device_memory_bridge_v1_fixture.json"


def test_apply_bridge_hints_increases_graph_nodes(tmp_path: Path) -> None:
    base_slice = tmp_path / "base_slice.json"
    base_slice.write_text(
        json.dumps(
            {"schema": "pet_companion_local_graph_slice_v1", "nodes": [], "edges": []},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out_slice.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--fixture-json",
            str(FIXTURE),
            "--input-slice-json",
            str(base_slice),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["node_count"] >= 2
    assert doc["edge_count"] >= 1
    assert doc["hints_applied"]["nodes_upserted"]
    assert doc["policy"]["bridge_lane"] == "pet_companion_device_memory_bridge_v1"
