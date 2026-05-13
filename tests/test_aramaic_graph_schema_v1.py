"""JSON Schema validation for Aramaic graph node/edge and regime shift score v1 (B-track)."""

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
def test_aramaic_graph_node_v1_minimal_instance_validates() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/aramaic_graph_node_v1.schema.json").read_text(encoding="utf-8")
    )
    instance = {
        "schema": "aramaic_graph_node_v1",
        "node_id": "aramaic::DAN.1.1",
        "corpus": "aramaic",
        "ref": "DAN.1.1",
        "text_norm": "malka",
        "time_bucket": "ancient_empire_cycle",
        "theme_tags": [],
        "regime_tags": [],
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
    }
    jsonschema.validate(instance=instance, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_aramaic_graph_edge_v1_minimal_instance_validates() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/aramaic_graph_edge_v1.schema.json").read_text(encoding="utf-8")
    )
    instance = {
        "schema": "aramaic_graph_edge_v1",
        "src_node_id": "aramaic::A",
        "dst_node_id": "aramaic::B",
        "edge_type": "timeline_anchor",
        "weight": 0.7,
        "confidence": 0.75,
        "evidence": "timeline_anchor: overlap=0.100; shared_tokens=0",
        "as_of_utc": "2020-01-01T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "semantic_overlap": 0.1,
        "shared_token_count": 0,
        "relation_basis": ["token_overlap"],
    }
    jsonschema.validate(instance=instance, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_aramaic_regime_shift_score_v1_minimal_instance_validates() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/aramaic_regime_shift_score_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    instance = {
        "schema": "aramaic_regime_shift_score_v1",
        "generated_at_utc": "2020-01-01T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "edge_count": 3,
        "conflict_ratio": 0.25,
        "insight_signal": 0.0,
        "insight_signal_applied": False,
        "insight_delta_applied": 0.0,
        "insight_cap_bucket": "low_vol",
        "shift_score": 0.55,
        "signal_label": "watch",
    }
    jsonschema.validate(instance=instance, schema=schema)
