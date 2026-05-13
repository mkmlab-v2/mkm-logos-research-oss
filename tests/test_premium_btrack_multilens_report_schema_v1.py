from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_premium_btrack_multilens_report_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "docs/final/schemas/premium_btrack_multilens_report_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/premium_btrack_multilens_report_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)
