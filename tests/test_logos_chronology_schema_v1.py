"""JSON Schema validation for Logos chronology v1 (B-track observational)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_logos_chronology_v1_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/logos_chronology_v1.schema.json"
    example_path = ROOT / "docs/final/artifacts/fixtures/logos_chronology_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)
    assert example["policy"]["non_gating"] is True
