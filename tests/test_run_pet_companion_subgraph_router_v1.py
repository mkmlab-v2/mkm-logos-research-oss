"""Pet companion subgraph router smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_BUILDER = ROOT / "scripts/build_pet_companion_observation_bridge_registry_v1.py"
SLICE_BUILDER = ROOT / "scripts/build_pet_companion_local_graph_slice_v1.py"
ROUTER = ROOT / "scripts/run_pet_companion_subgraph_router_v1.py"


def test_pet_subgraph_router_health_check_query(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(SLICE_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "pet_router.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            "산책 패턴이 계속 반복돼요",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "pet_companion_subgraph_router_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["non_gating"] is True
    assert doc["bridges_matched"] >= 1
    assert len(doc["paths"]) >= 1
