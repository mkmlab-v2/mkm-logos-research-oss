"""JSON Schema: showroom_topology_radar_snapshot_v1 (committed example)."""

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
def test_topology_radar_snapshot_example_validates() -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/showroom_topology_radar_snapshot_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    example = json.loads(
        (
            ROOT / "docs/final/schemas/showroom_topology_radar_snapshot_v1.example.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=example, schema=schema)
