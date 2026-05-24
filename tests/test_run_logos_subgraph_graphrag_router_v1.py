"""Logos subgraph GraphRAG router v1 smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"
REGISTRY_BUILDER = ROOT / "scripts/build_logos_concept_bridge_registry_v1.py"
COVENANT_BUILDER = ROOT / "scripts/build_logos_concept_bridge_covenant_crisis_poc_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_subgraph_graphrag_router_v1.schema.json"


def test_logos_subgraph_router_covenant_query(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query-id",
            "q01",
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
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["bridges_matched"] >= 1
    assert len(doc["paths"]) >= 1
    assert any("Ps.89" in v or "Jer.31" in v or "Job.24" in v for v in doc["verse_ids"])
