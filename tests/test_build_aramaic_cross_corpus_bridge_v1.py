"""Smoke: build_aramaic_cross_corpus_bridge_v1 CLI emits bridge nodes/edges JSONL."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_aramaic_cross_corpus_bridge_v1.py"
NODE_SCHEMA = ROOT / "docs" / "final" / "schemas" / "aramaic_graph_node_v1.schema.json"
EDGE_SCHEMA = ROOT / "docs" / "final" / "schemas" / "aramaic_graph_edge_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_aramaic_cross_corpus_bridge_cli_smoke(tmp_path: Path) -> None:
    node_schema = json.loads(NODE_SCHEMA.read_text(encoding="utf-8"))
    edge_schema = json.loads(EDGE_SCHEMA.read_text(encoding="utf-8"))
    inp = tmp_path / "aramaic_nodes.jsonl"
    on = tmp_path / "bridge_nodes.jsonl"
    oe = tmp_path / "bridge_edges.jsonl"
    row = {
        "schema": "aramaic_graph_node_v1",
        "node_id": "aramaic::Dan.2.4",
        "corpus": "aramaic",
        "ref": "Dan.2.4",
        "text_norm": "alpha beta",
        "time_bucket": "ancient_empire_cycle",
        "theme_tags": [],
        "regime_tags": [],
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
    }
    inp.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--aramaic-nodes-jsonl",
            str(inp),
            "--output-nodes-jsonl",
            str(on),
            "--output-edges-jsonl",
            str(oe),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    nlines = [ln for ln in on.read_text(encoding="utf-8").splitlines() if ln.strip()]
    elines = [ln for ln in oe.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(nlines) == 2  # hebrew + greek
    assert len(elines) == 2
    for ln in nlines:
        jsonschema.validate(instance=json.loads(ln), schema=node_schema)
    for ln in elines:
        jsonschema.validate(instance=json.loads(ln), schema=edge_schema)
