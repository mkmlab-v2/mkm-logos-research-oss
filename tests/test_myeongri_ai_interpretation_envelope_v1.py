# @MKM12-METADATA
# Type: Logic
# Purpose: myeongri AI interpretation envelope schema smoke.
# Keywords: myeongri, btrack, schema, prompt envelope

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "myeongri_ai_interpretation_envelope_v1.schema.json"
_TEMPLATE = _ROOT / "docs" / "final" / "MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md"


def test_schema_and_template_exist() -> None:
    assert _SCHEMA.is_file()
    assert _TEMPLATE.is_file()


def test_minimal_envelope_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    sample = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mkm_advanced_insight": "[HYPO] Pattern narrative tied to attached deterministic JSON only.",
        "confidence_score": 0.6,
        "human_review_required": True,
        "prohibition_ack": "Not live trading, not medical, not doctrinal finality; B-track only.",
    }
    jsonschema.Draft7Validator(schema).validate(sample)
