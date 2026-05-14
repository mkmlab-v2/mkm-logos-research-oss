"""JSON Schema: aramaic_insight_cap_threshold_drift_alert_v1 (drift alert artifact)."""

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
def test_drift_alert_example_json_validates() -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    example = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.example.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_drift_alert_insufficient_history_instance_validates() -> None:
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/aramaic_insight_cap_threshold_drift_alert_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    instance = {
        "schema": "aramaic_insight_cap_threshold_drift_alert_v1",
        "generated_at_utc": "2026-05-13T12:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "history_rows": 0,
        "history_recommended_snapshots": 0,
        "drift_threshold": 0.0001,
        "should_alert": False,
        "reason": "insufficient_history",
        "max_abs_delta": 0.0,
        "drifted_keys": [],
        "deltas": {},
        "webhook": {"sent": False, "status": "skipped_insufficient_history"},
    }
    jsonschema.validate(instance=instance, schema=schema)
