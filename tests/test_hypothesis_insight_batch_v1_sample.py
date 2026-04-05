"""Validate data/btrack/hypothesis_insight_batch_v1.sample.jsonl against local schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "btrack" / "hypothesis_insight_batch_v1.schema.json"
SAMPLE_PATH = ROOT / "data" / "btrack" / "hypothesis_insight_batch_v1.sample.jsonl"


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file(), f"missing {SCHEMA_PATH}"


def test_sample_jsonl_lines_validate() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    assert SAMPLE_PATH.is_file(), f"missing {SAMPLE_PATH}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    lines = [ln.strip() for ln in SAMPLE_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1, "sample should have at least one row"
    for i, line in enumerate(lines):
        doc = json.loads(line)
        validator.validate(doc)
