from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_va_cooldown_policy_example_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "docs/final/schemas/va_cooldown_policy_v1.schema.json").read_text(encoding="utf-8"))
    example = json.loads((ROOT / "docs/final/schemas/va_cooldown_policy_v1.example.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


def test_va_cooldown_event_example_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "docs/final/schemas/va_cooldown_event_v1.schema.json").read_text(encoding="utf-8"))
    example = json.loads((ROOT / "docs/final/schemas/va_cooldown_event_v1.example.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)
