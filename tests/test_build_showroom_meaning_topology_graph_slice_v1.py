# Keywords: build_showroom_meaning_topology_graph_slice_v1, showroom, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_showroom_meaning_topology_graph_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_meaning_topology_graph_slice_v1.schema.json"
CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_insight_candidates_latest.json"
NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    assert CANDIDATES.is_file()
    assert NODES.is_file()
    assert EDGES.is_file()


def test_build_slice_default_out(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--no-mirror-artifact",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_meaning_topology_graph_slice_v1"
    assert doc["research_only"] is True
    assert doc["hypothesis_tier"] == "B"
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["stats"]["node_count"] >= 1
    assert doc["stats"]["edge_count"] >= 1
    assert doc["nodes"][0]["id"]
    assert doc["edges"][0]["src"]
    overlay = doc.get("inference_overlay") or {}
    assert overlay.get("schema") == "logos_oracle_inference_graph_overlay_v1"
    assert len(overlay.get("four_d_families") or []) == 4


def test_build_slice_json_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "slice2.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--no-mirror-artifact",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
