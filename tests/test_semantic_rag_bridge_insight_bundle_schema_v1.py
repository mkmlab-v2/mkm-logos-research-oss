"""JSON Schema validation for internal semantic+RAG bridge insight bundle v1."""

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
def test_insight_bundle_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_insight_bundle_minimal_myeongri_kind_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    inst = {
        "schema": "semantic_rag_bridge_insight_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": "2026-05-14T12:00:01Z",
        "rag_evidence": [],
        "calibration_reference": {
            "kind": "myeongri_vector_4d",
            "artifact_path_rel": "docs/final/artifacts/market_myeongni_lens_latest.json",
            "summary_line": "B-track myeongni lens snapshot pointer only."
        },
        "structured_insight_slots": [
            {"slot_id": "axis.summary", "text": "S/L/K/M surface vector summarized for coordinator."}
        ],
        "policy": {"track": "B-track", "gating": "advisory", "hypothesis_label": None},
    }
    jsonschema.validate(instance=inst, schema=schema)
