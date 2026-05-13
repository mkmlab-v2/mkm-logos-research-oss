"""Contract: bible_meaning_graph_node_v1 / bible_meaning_graph_edge_v1 row shape + JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]

NODE_REQUIRED = frozenset({"schema", "node_id", "kind", "label"})
EDGE_REQUIRED = frozenset({"schema", "src_node_id", "dst_node_id", "edge_type", "weight"})


def test_bible_meaning_graph_node_row_shape() -> None:
    row = {
        "schema": "bible_meaning_graph_node_v1",
        "node_id": "theme::exile",
        "kind": "theme",
        "label": "exile",
    }
    assert NODE_REQUIRED <= row.keys()
    assert row["schema"] == "bible_meaning_graph_node_v1"


def test_bible_meaning_graph_edge_row_shape() -> None:
    row = {
        "schema": "bible_meaning_graph_edge_v1",
        "src_node_id": "aramaic::Dan.2.4",
        "dst_node_id": "theme::exile",
        "edge_type": "theme_association",
        "weight": 0.6,
    }
    assert EDGE_REQUIRED <= row.keys()
    assert row["schema"] == "bible_meaning_graph_edge_v1"
    assert isinstance(row["weight"], (int, float))


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_bible_meaning_graph_node_v1_schema_file_validates_minimal() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/bible_meaning_graph_node_v1.schema.json").read_text(encoding="utf-8")
    )
    instance = {
        "schema": "bible_meaning_graph_node_v1",
        "node_id": "theme::exile",
        "kind": "theme",
        "label": "exile",
    }
    jsonschema.validate(instance=instance, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_bible_meaning_graph_edge_v1_schema_file_validates_minimal() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/bible_meaning_graph_edge_v1.schema.json").read_text(encoding="utf-8")
    )
    instance = {
        "schema": "bible_meaning_graph_edge_v1",
        "src_node_id": "aramaic::Dan.2.4",
        "dst_node_id": "theme::exile",
        "edge_type": "theme_association",
        "weight": 0.6,
    }
    jsonschema.validate(instance=instance, schema=schema)
