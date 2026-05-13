"""Smoke: build_aramaic_graph_edges_v1 CLI emits JSONL rows matching aramaic_graph_edge_v1 schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_aramaic_graph_edges_v1.py"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "aramaic_graph_edge_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_aramaic_graph_edges_cli_smoke(tmp_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    nodes = tmp_path / "nodes.jsonl"
    out = tmp_path / "edges.jsonl"
    base = {
        "schema": "aramaic_graph_node_v1",
        "corpus": "aramaic",
        "time_bucket": "ancient_empire_cycle",
        "theme_tags": [],
        "regime_tags": [],
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
    }
    rows = [
        {
            **base,
            "node_id": "aramaic::Dan.2.4",
            "ref": "Dan.2.4",
            "text_norm": "alpha beta gamma",
        },
        {
            **base,
            "node_id": "aramaic::Dan.2.5",
            "ref": "Dan.2.5",
            "text_norm": "beta gamma delta",
        },
    ]
    nodes.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-jsonl",
            str(nodes),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
    for ln in lines:
        obj = json.loads(ln)
        jsonschema.validate(instance=obj, schema=schema)
        assert obj.get("schema") == "aramaic_graph_edge_v1"
