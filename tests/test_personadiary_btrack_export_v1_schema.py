"""Schema smoke for personadiary_btrack_export_v1 (B-track manual inbox · research_only)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_btrack_export_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs/final/artifacts/fixtures/personadiary_btrack_export_v1.example.json"
OPS_EXAMPLE = ROOT / "docs/final/artifacts/fixtures/personadiary_mobile_ops_v1.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_personadiary_btrack_export_example_validates(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["hypothesis_tier"] == "B"
    assert doc["research_only"] is True
    assert doc["auto_upload"] is False
    assert doc["send_gate"] == "HOLD"
    assert doc["human_gate_ack"]["acknowledged"] is True
    assert doc["redaction"]["pii_redact_applied"] is True
    assert "local_birth_profile_v1" in doc["redaction"]["fields_removed"]


def test_build_personadiary_btrack_export_from_ops_example(schema: dict) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_personadiary_btrack_export_v1",
        ROOT / "scripts/build_personadiary_btrack_export_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    ops = json.loads(OPS_EXAMPLE.read_text(encoding="utf-8"))
    doc = mod.build_btrack_export(ops, pii_redact=True, human_gate_ack=True)
    jsonschema.validate(instance=doc, schema=schema)
    assert "diary_lane_stats" in doc["payload"]
    assert "diary_entries_redacted" not in doc["payload"]


def test_build_requires_human_gate(schema: dict) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_personadiary_btrack_export_v1",
        ROOT / "scripts/build_personadiary_btrack_export_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    ops = json.loads(OPS_EXAMPLE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="human_gate_ack"):
        mod.build_btrack_export(ops, human_gate_ack=False)
