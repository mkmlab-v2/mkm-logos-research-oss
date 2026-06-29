"""Schema smoke for personadiary_offline_ingest_queue_v1 (Pull-first Intent middleware)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_offline_ingest_queue_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs/final/artifacts/fixtures/personadiary_offline_ingest_queue_v1.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_offline_ingest_queue_example_validates(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["preview_only"] is True
    assert doc["send_gate_default"] == "HOLD"


def test_offline_ingest_queue_rejects_non_hold_gate(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    doc["send_gate_default"] = "OPEN"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=doc, schema=schema)
