# -*- coding: utf-8 -*-
"""commander_profile_v1 example validates against schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "commander_profile_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs" / "final" / "artifacts" / "commander_profile_v1.example.json"


@pytest.mark.skipif(not SCHEMA_PATH.is_file(), reason="schema missing")
def test_commander_profile_example_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8-sig"))
    jsonschema.validate(doc, schema)
    assert doc["sasang_reference"]["auto_merge_with_myeongni"] is False
    assert doc["cognition_hypothesis"]["rail"] == "Track_B_HYPO"
    assert doc["myeongni_fact_ref"]["element_counts_visible"]["화"] == 0
