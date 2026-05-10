# Purpose: Regression — mkm_bianzheng_tri_layer_v1 schema validates fixture (standalone).
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

SCHEMA = ROOT / "docs/final/schemas/mkm_bianzheng_tri_layer_v1.schema.json"
FIXTURE = ROOT / "tests/fixtures/mkm_bianzheng_tri_layer_v1.example.json"


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_tri_layer_fixture_validates_standalone() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
