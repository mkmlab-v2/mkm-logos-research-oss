"""Schema + parity tests for personadiary_moment_intent_weights_v1 SSOT."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_moment_intent_weights_v1 import (  # noqa: E402
    intent_keywords,
    intent_priority,
    intent_weights,
    load_ssot,
    validate_ssot,
)

SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_moment_intent_weights_v1.schema.json"
SSOT_PATH = ROOT / "docs/final/artifacts/personadiary_moment_intent_weights_v1_latest.json"
PUBLIC_PATH = ROOT / "projects/no1kmedi/public/data/personadiary_moment_intent_weights_v1.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_ssot_validates(schema: dict) -> None:
    doc = load_ssot()
    jsonschema.validate(instance=doc, schema=schema)
    assert validate_ssot(doc) == []
    assert doc["prophecy_vote"] == "none"


def test_public_mirror_matches_ssot() -> None:
    assert PUBLIC_PATH.is_file(), "run sync_personadiary_moment_intent_weights_public_v1.py"
    ssot = load_ssot()
    public = json.loads(PUBLIC_PATH.read_text(encoding="utf-8-sig"))
    assert public["intent_weights"] == ssot["intent_weights"]
    assert public["intent_keywords"] == ssot["intent_keywords"]
    assert public["intent_priority"] == ssot["intent_priority"]


def test_py_loader_matches_ssot_json() -> None:
    doc = json.loads(SSOT_PATH.read_text(encoding="utf-8-sig"))
    assert intent_weights() == doc["intent_weights"]
    assert intent_keywords() == {k: tuple(v) for k, v in doc["intent_keywords"].items()}
    assert intent_priority() == tuple(doc["intent_priority"])
