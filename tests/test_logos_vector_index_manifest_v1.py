# @MKM12-METADATA
# Type: Logic
# Purpose: Logos vector index manifest v1 regression.
# Keywords: logos, track_b, vector_index

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_logos_vector_index_manifest_v1.py"
_SCHEMA = _ROOT / "docs/final/schemas/logos_vector_index_manifest_v1.schema.json"
_CONTRACT = _ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_MANIFEST_V1_CONTRACT.json"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()


def test_builder_default_paths_ok(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "manifest.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("schema") == "logos_vector_index_manifest_v1"
    assert doc.get("non_gating_ack") is True
    assert doc.get("index_build", {}).get("embeddings_computed") is False


def test_builder_minimal_fixture(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "schema": "logos_vector_index_policy_v1",
                "version": "1.0.0",
                "hypothesis_tier": "B",
                "purpose": "test",
                "status": "stub",
                "embedding": {"model_id": "stub"},
                "corpus_alignment": {"required_preconditions": []},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    man = tmp_path / "corpus_manifest.json"
    man.write_text(
        json.dumps(
            {
                "schema": "logos_corpus_manifest_v1",
                "version": "1.0.0",
                "verse_count": 2,
                "input_sha256": "a" * 64,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "schema": "logos_corpus_graph_bundle_v1",
                "version": "1.0.0",
                "dedupe_bundle_key_sha256": "b" * 64,
                "manifest_snapshot": {"corpus_input_sha256": "c" * 64},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(policy),
            "--corpus-manifest",
            str(man),
            "--bundle-json",
            str(bundle),
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
    assert doc["corpus_alignment"]["verse_count"] == 2
