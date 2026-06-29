"""regime_lens_style_focus_locked_v1 artifact vs schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/final/artifacts/regime_lens_style_focus_locked_v1.json"
SCHEMA = ROOT / "docs/final/schemas/regime_lens_style_focus_locked_v1.schema.json"


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="artifact missing")
@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_style_focus_locked_validates_against_schema() -> None:
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:
        pytest.skip("jsonschema not installed")

    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["prohibited_zones"]["canvas_to_audio_runtime_binding"] is True


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="artifact missing")
def test_style_focus_send_gate_ref_exists() -> None:
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    ref = doc["track_wall"]["send_gate_ref"]
    assert (ROOT / ref.replace("/", "\\")).is_file() or (ROOT / ref).is_file()
