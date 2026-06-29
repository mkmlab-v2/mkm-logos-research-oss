"""encounter_sequence_v1 — schema + fixture validation (TKM / Sasang primary)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/encounter_sequence_v1.schema.json"
FIXTURE_PATH = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"


def test_fixture_matches_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_tkm_domain_and_sasang_primary() -> None:
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    assert doc.get("domain_lane") == "tkm_korean_han_medicine"
    assert doc.get("sasang_primary") is True
    assert doc.get("hypothesis_tier") == "B"
    tcm = doc.get("external_reference_tcm") or {}
    assert tcm.get("role") == "benchmark_reference_only"


def test_sequence_trajectory_lengths() -> None:
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    turns = doc.get("turns") or []
    summary = doc.get("sequence_summary") or {}
    assert summary.get("turn_count") == len(turns)
    assert len(summary.get("constitution_trajectory") or []) == len(turns)
    assert len(summary.get("confidence_trajectory") or []) == len(turns)


def test_no_prescription_boundary() -> None:
    doc = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    bc = doc.get("boundary_contract") or {}
    assert bc.get("no_prescription_output") is True
    assert bc.get("track_a_autobind_forbidden") is True
