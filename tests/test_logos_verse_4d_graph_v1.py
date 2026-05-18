# @MKM12-METADATA
# Type: Logic
# Purpose: logos_verse_4d graph edges + medoid manifest smoke.
# Keywords: logos, track_b, verse_4d, graph, medoid

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_EDGE_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_graph_edges_v1.schema.json"
_MEDOID_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_medoids_v1.schema.json"
_BUILDER = _ROOT / "scripts/build_logos_verse_4d_graph_v1.py"
_DEFAULT_IN = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def test_graph_schemas_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    for path in (_EDGE_SCHEMA, _MEDOID_SCHEMA):
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator.check_schema(schema)


def test_builder_smoke_max_20(tmp_path: Path) -> None:
    src = _DEFAULT_IN
    if not src.is_file():
        pytest.skip("logos_verse_4d_v1_latest.jsonl not present")
    out_edges = tmp_path / "edges.jsonl"
    out_medoids = tmp_path / "medoids.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_BUILDER),
            "--input-jsonl",
            str(src),
            "--out-edges",
            str(out_edges),
            "--out-medoids",
            str(out_medoids),
            "--max-rows",
            "20",
            "--top-k-neighbors",
            "4",
            "--top-medoids",
            "10",
            "--top-medoids-per-cluster",
            "3",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    edge_lines = [ln for ln in out_edges.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(edge_lines) == 20 * 4
    jsonschema = pytest.importorskip("jsonschema")
    edge_schema = json.loads(_EDGE_SCHEMA.read_text(encoding="utf-8"))
    for ln in edge_lines[:5]:
        jsonschema.Draft7Validator(edge_schema).validate(json.loads(ln))
    medoids = json.loads(out_medoids.read_text(encoding="utf-8"))
    medoid_schema = json.loads(_MEDOID_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(medoid_schema).validate(medoids)
    assert medoids["counts"]["rows_used"] == 20
    assert len(medoids["global_medoids"]) == 10
    assert medoids["global_medoids"][0]["verse_id"]
