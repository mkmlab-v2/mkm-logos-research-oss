# @MKM12-METADATA
# Type: Logic
# Purpose: logos_verse_4d_v1 row + corpus manifest schema regression.
# Keywords: logos, track_b, verse_4d, schema

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_ROW_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_v1.schema.json"
_CORPUS_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_corpus_v1.schema.json"
_EXAMPLE = _ROOT / "docs/final/artifacts/fixtures/logos_verse_4d_v1.example.json"
_BUILDER = _ROOT / "scripts/build_logos_verse_4d_corpus_v1.py"


def test_row_schema_validates_example() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_ROW_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_corpus_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_CORPUS_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_builder_smoke_max_3(tmp_path: Path) -> None:
    src = _ROOT / "data/logos/verse_decoded_v2.jsonl"
    if not src.is_file():
        pytest.skip("verse_decoded_v2.jsonl not present")
    out_jsonl = tmp_path / "verse_4d.jsonl"
    out_manifest = tmp_path / "manifest.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_BUILDER),
            "--input-jsonl",
            str(src),
            "--out-jsonl",
            str(out_jsonl),
            "--out-manifest",
            str(out_manifest),
            "--max-rows",
            "3",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_ROW_SCHEMA.read_text(encoding="utf-8"))
    for ln in lines:
        jsonschema.Draft7Validator(schema).validate(json.loads(ln))
    manifest = json.loads(out_manifest.read_text(encoding="utf-8"))
    corpus_schema = json.loads(_CORPUS_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(corpus_schema).validate(manifest)
