"""Schema smoke for personadiary_native_shell_hypo_v1 (Capacitor shell · research_only)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_native_shell_hypo_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs/final/artifacts/fixtures/personadiary_native_shell_hypo_v1.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_native_shell_hypo_example_validates(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["push_enabled"] is False
    assert doc["research_only"] is True


def test_native_shell_hypo_rejects_push_enabled(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    doc["push_enabled"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=doc, schema=schema)
