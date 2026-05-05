# @MKM12-METADATA
# Type: Logic
# Purpose: Logos corpus manifest v1 builder regression (slice 1).
# Keywords: logos, corpus, manifest, track_b

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_logos_corpus_manifest_v1.py"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_CORPUS_MANIFEST_V1_CONTRACT.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_corpus_manifest_v1.schema.json"
_FIXTURE_OK = _ROOT / "tests" / "fixtures" / "logos_verse_4pipeline_minimal_manifest_v1.json"
_FIXTURE_DUP = _ROOT / "tests" / "fixtures" / "logos_verse_4pipeline_duplicate_manifest_v1.json"


def test_contract_and_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "logos_corpus_manifest_v1"
    assert doc.get("runner") == "scripts/build_logos_corpus_manifest_v1.py"


def test_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_manifest_builder_minimal_fixture(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "manifest.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--input", str(_FIXTURE_OK), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["verse_count"] == 3
    assert doc["integrity"]["null_verse_id_count"] == 0
    assert doc["integrity"]["duplicate_verse_id_detected"] is False
    assert "Gen.1.1" in doc["sample_verse_ids_head"]


def test_manifest_detects_duplicate_verse_id(tmp_path: Path) -> None:
    out = tmp_path / "manifest_dup.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--input", str(_FIXTURE_DUP), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["verse_count"] == 2
    assert doc["integrity"]["duplicate_verse_id_detected"] is True
