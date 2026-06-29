"""Schema smoke for personadiary_mobile_ops_v1 (PWA local ops · preview_only)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_mobile_ops_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs/final/artifacts/fixtures/personadiary_mobile_ops_v1.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_personadiary_mobile_ops_example_validates(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["preview_only"] is True
    assert doc["send_gate_default"] == "HOLD"
    assert doc["notification_policy"]["push_enabled"] is False


def test_personadiary_mobile_ops_weekly_cap(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    doc["weekly_top5"] = [
        {
            "id": f"w{i}",
            "text": f"goal {i}",
            "status": "pending",
            "lane": "mind",
        }
        for i in range(5)
    ]
    jsonschema.validate(instance=doc, schema=schema)
    with pytest.raises(jsonschema.ValidationError):
        doc["weekly_top5"].append(
            {"id": "w6", "text": "overflow", "status": "pending", "lane": "mind"}
        )
        jsonschema.validate(instance=doc, schema=schema)


def test_personadiary_mobile_ops_valid_without_north_star(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    doc.pop("north_star_by_lane_hypo_v1", None)
    jsonschema.validate(instance=doc, schema=schema)


def test_personadiary_mobile_ops_north_star_hypo_tier_b(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert doc.get("north_star_by_lane_hypo_v1", {}).get("hypothesis_tier") == "B"
    lanes = doc["north_star_by_lane_hypo_v1"]["lanes"]
    assert set(lanes.keys()) == {"body", "mind", "work", "rest"}
    jsonschema.validate(instance=doc, schema=schema)


def test_personadiary_mobile_ops_local_birth_profile_optional(schema: dict) -> None:
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert doc["local_birth_profile_v1"]["schema"] == "local_birth_profile_v1"
    jsonschema.validate(instance=doc, schema=schema)
    doc.pop("local_birth_profile_v1", None)
    jsonschema.validate(instance=doc, schema=schema)
