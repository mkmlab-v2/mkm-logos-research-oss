"""JSON Schema: insight_survivor_health_alert_v1 (committed example + synthetic instances)."""

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
def test_survivor_health_alert_example_json_validates() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_alert_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    example = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_alert_v1.example.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_survivor_health_alert_stable_below_threshold_synthetic_validates() -> None:
    schema = json.loads(
        (ROOT / "docs/final/schemas/insight_survivor_health_alert_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    instance = {
        "schema": "insight_survivor_health_alert_v1",
        "generated_at_utc": "2026-05-13T12:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "T",
        "should_alert": False,
        "reason": "stable_below_threshold",
        "latest": {"survivor_count": 2, "survivor_mean_score": 0.6},
        "history_latest_snapshots": 1,
        "drift_threshold_mean": 0.05,
        "drift_threshold_count": 1,
        "deltas": {"survivor_count": 0.0, "survivor_mean_score": 0.0},
        "max_abs_delta": 0.0,
        "webhook": {"sent": False, "status": "skipped_should_false"},
    }
    jsonschema.validate(instance=instance, schema=schema)
