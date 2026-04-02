# @MKM12-METADATA
# Type: Test
# Purpose: B-track hypothesis inventory JSON schema lock

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_INV = _ROOT / "docs" / "final" / "artifacts" / "B_TRACK_HYPOTHESIS_INVENTORY_V1.json"
_SCHEMA = _ROOT / "docs" / "final" / "B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json"
_VALIDATOR = _ROOT / "scripts" / "validate_b_track_hypothesis_inventory.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_b_track_hypothesis_inventory", _VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_hypothesis_inventory_exists_and_schema() -> None:
    assert _INV.is_file(), f"missing: {_INV}"
    doc = json.loads(_INV.read_text(encoding="utf-8"))
    assert doc.get("schema") == "b_track_hypothesis_inventory_v1"
    assert "disclaimer" in doc and str(doc["disclaimer"]).strip()
    assert doc.get("constitution_ref")
    assert "entries" in doc and isinstance(doc["entries"], list)


def test_hypothesis_inventory_validates_against_json_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    assert _SCHEMA.is_file()
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(_INV.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_sample_entry_would_validate() -> None:
    """Template row: not persisted in SSOT until human review."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(_INV.read_text(encoding="utf-8"))
    sample = {
        "hypothesis_id": "HYP_TEMPLATE_0001",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "pillar": "state_resonance",
        "ontology_layer": "unspecified",
        "lens_family": "none",
        "title": "[HYPO] template row",
        "falsification_condition": "Any evidence that breaks thematic-only linkage.",
        "promotion_status": "draft",
    }
    entry_schema = schema["definitions"]["hypothesis_entry"]
    jsonschema.Draft7Validator(entry_schema).validate(sample)


def test_inventory_cross_links_resolve_against_ssot() -> None:
    mod = _load_validator()
    doc = json.loads(_INV.read_text(encoding="utf-8"))
    errs = mod.collect_cross_link_errors(doc, _ROOT)
    assert errs == [], errs


def test_collect_cross_link_errors_flags_dangling_entry_id() -> None:
    mod = _load_validator()
    doc = {
        "entries": [
            {
                "hypothesis_id": "HYP_BAD_LINK_0001",
                "cross_links": [
                    {
                        "target_artifact": "CROSS_REF_DSS_TO_STATES_DRAFT",
                        "entry_ids": ["ENTRY_01", "ENTRY_DOES_NOT_EXIST_99999"],
                        "join_note": "test fixture",
                    }
                ],
            }
        ]
    }
    errs = mod.collect_cross_link_errors(doc, _ROOT)
    assert any("ENTRY_DOES_NOT_EXIST_99999" in e for e in errs), errs


def test_logos_state_mapping_accepts_state_id_strings() -> None:
    mod = _load_validator()
    doc = {
        "entries": [
            {
                "hypothesis_id": "HYP_LOGOS_OK",
                "cross_links": [
                    {
                        "target_artifact": "LOGOS_STATE_MAPPING_V1",
                        "entry_ids": ["13"],
                        "join_note": "pilot anchor state",
                    }
                ],
            }
        ]
    }
    errs = mod.collect_cross_link_errors(doc, _ROOT)
    assert errs == [], errs
