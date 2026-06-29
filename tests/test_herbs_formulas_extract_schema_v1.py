"""JSON Schema validation for herbs_formulas_extract_v1 (B-track draft)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/herbs_formulas_extract_v1.schema.json"
FIXTURE_PATH = ROOT / "tests/fixtures/herbs_formulas_extract_minimal_v1.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_herbs_formulas_extract_minimal_fixture_validates() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)
    assert instance["research_only"] is True
    assert instance["expert_review_required"] is True
    assert instance["send_gate"] == "HOLD"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_herbs_formulas_extract_rejects_missing_clinical_required_field() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    del instance["payload"]["clinical"]["primary_pathology"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)
