# @MKM12-METADATA
# Type: Logic
# Purpose: Logos corpus + graph bundle v1 (slice 2) regression.
# Keywords: logos, graph, bundle, track_b

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_logos_corpus_graph_bundle_v1.py"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_CORPUS_GRAPH_BUNDLE_V1_CONTRACT.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_corpus_graph_bundle_v1.schema.json"
_CORPUS = _ROOT / "tests" / "fixtures" / "logos_verse_4pipeline_minimal_manifest_v1.json"
_NODES = _ROOT / "tests" / "fixtures" / "logos_graph_bundle_nodes_minimal_v1.jsonl"
_EDGES = _ROOT / "tests" / "fixtures" / "logos_graph_bundle_edges_minimal_v1.jsonl"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "logos_corpus_graph_bundle_v1"


def test_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_bundle_end_to_end_tmp_manifest(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))

    man_script = _ROOT / "scripts" / "build_logos_corpus_manifest_v1.py"
    manifest_path = tmp_path / "manifest.json"
    cp0 = subprocess.run(
        [sys.executable, str(man_script), "--input", str(_CORPUS), "--output", str(manifest_path)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp0.returncode == 0, cp0.stderr

    body = json.loads(manifest_path.read_text(encoding="utf-8"))
    body["input_path"] = str(_CORPUS.relative_to(_ROOT)).replace("\\", "/")
    manifest_path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = tmp_path / "bundle.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--manifest",
            str(manifest_path),
            "--nodes-jsonl",
            str(_NODES),
            "--edges-jsonl",
            str(_EDGES),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["alignment"]["graph_verse_ref_distinct_count"] == 3
    assert doc["alignment"]["graph_refs_in_corpus_count"] == 3
    assert doc["alignment"]["corpus_digest_matches_manifest"] is True
    assert doc["graph_files"]["edge_type_counts"].get("timeline_anchor") == 1
