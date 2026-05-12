"""JSON Schema validation for M31 thin audit trail (gematria path + RAG metabolism metaphor)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_m31_audit_trail_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/lens_music_m31_audit_trail_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/lens_music_m31_audit_trail_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_rag_metabolism_drift_standalone_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/lens_music_rag_metabolism_drift_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    inst = {
        "schema": "lens_music_rag_metabolism_drift_v1",
        "bounded_drift_0_1": 0.08,
        "source": "chain_doc_rag_digest",
        "digest_fingerprint": "feedface",
        "metaphor_notice": "rag_digestion_metaphor_not_biological_gut_flora",
    }
    jsonschema.validate(instance=inst, schema=schema)
