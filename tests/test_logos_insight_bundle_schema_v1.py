"""JSON Schema validation for Logos insight bundle v1 (B-track observational contract)."""

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
def test_logos_insight_bundle_non_degraded_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)
    assert example.get("degraded") is False
    assert example.get("missing_upstream") == []


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_logos_insight_bundle_minimal_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.minimal.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_logos_insight_bundle_tension_hypothesis_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    base = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.minimal.example.json").read_text(
            encoding="utf-8"
        )
    )
    base["tension_hypotheses"] = [
        {
            "tension_axis_id": "structural_edge_density_mismatch_v0",
            "description_neutral": "Cross-corpus bridge edge count ratio differs from semantic edge quality baseline (observational).",
            "confidence_0_1": 0.42,
            "evidence_refs": [
                {
                    "verse_id": "GEN.1.1",
                    "quote_hash": "abc123deadbeef",
                    "edge_type": "cross_lens_confirm",
                    "source_track": "B",
                }
            ],
            "supporting_metrics": {"bridge_edges": 12, "quality_mean": 0.31},
            "counter_evidence_refs": [],
        }
    ]
    jsonschema.validate(instance=base, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_logos_insight_bundle_citation_requires_snippet() -> None:
    schema_path = ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    base = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.minimal.example.json").read_text(
            encoding="utf-8"
        )
    )
    base["citation_pack"] = [
        {
            "verse_id": "PSA.23.1",
            "quote_hash": "def456cafebabe",
            "snippet": "The Lord is my shepherd; I shall not want.",
            "source_track": "B",
        }
    ]
    jsonschema.validate(instance=base, schema=schema)
