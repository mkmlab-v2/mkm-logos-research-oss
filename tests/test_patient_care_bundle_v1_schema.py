# -*- coding: utf-8 -*-
"""JSON Schema contract for patient_care_bundle_v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.schema.json"
EXAMPLE = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.minimal.example.json"


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_example_validates_against_schema() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_logos_included_requires_non_gating_ack() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    slots = example["patient_slots"]
    for i, s in enumerate(slots):
        if s["slot_id"] == "logos_opt":
            bad = json.loads(json.dumps(example))
            bad["patient_slots"][i] = {
                **s,
                "included": True,
                "body_markdown": "x",
            }
            bad["patient_slots"][i].pop("non_gating_ack", None)
            with pytest.raises(jsonschema.exceptions.ValidationError):
                jsonschema.validate(instance=bad, schema=schema)
            return
    raise AssertionError("logos_opt slot missing")


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_optional_post_process_provenance_fields_validate() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    prov = example.setdefault("provenance", {})
    prov.update(
        {
            "slot_templates_applied_utc": "2026-05-14T12:00:00Z",
            "slot_templates_json_path": "docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json",
            "generation_policy_validated_utc": "2026-05-14T12:01:00Z",
            "generation_policy_json_path": "docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json",
            "patient_facing_markdown_written_utc": "2026-05-14T12:02:00Z",
            "patient_facing_markdown_path": "reports/patient_bundle.md",
        }
    )
    jsonschema.validate(instance=example, schema=schema)
