"""commander_a_code_signoff_v1 validator tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/personalization/commander_a_code_signoff_v1.local.json.example"
SCHEMA = ROOT / "docs/final/schemas/commander_a_code_signoff_v1.schema.json"


def _load_validator():
    path = ROOT / "scripts/validate_commander_a_code_signoff_v1.py"
    spec = importlib.util.spec_from_file_location("validate_commander_a_code_signoff", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_example_signoff_schema_valid() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    errors = mod.validate_signoff_doc(doc, schema_path=SCHEMA)
    assert errors == []
    assert doc.get("approved") is False


def test_approved_requires_attestations_and_utc() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["approved"] = True
    doc["signoff_utc"] = "2026-06-05T10:00:00Z"
    errors = mod.validate_signoff_doc(doc, schema_path=SCHEMA)
    assert any("human_commander_signoff" in e for e in errors)


def test_approved_passes_when_attestations_true() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["approved"] = True
    doc["signoff_utc"] = "2026-06-05T10:00:00Z"
    doc["attestations"] = {
        "human_commander_signoff": True,
        "separate_rq_from_rq026_closed": True,
        "no_track_a_live_auto_merge": True,
    }
    errors = mod.validate_signoff_doc(doc, schema_path=SCHEMA)
    assert errors == []
    summary = mod.signoff_summary(doc, errors=errors)
    assert summary["human_signoff_status"] == "APPROVED"


def test_track_wall_must_block_promotion() -> None:
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["track_wall"]["track_a_auto_promotion"] = True
    errors = mod.validate_signoff_doc(doc, schema_path=SCHEMA)
    assert any("track_a_auto_promotion" in e for e in errors)
