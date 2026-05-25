"""Compression B2B pilot metering appendix builder + schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/compression_b2b_pilot_metering_appendix_v1.schema.json"
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/compression_b2b_pilot_metering_appendix_v1.example.json"
BUILDER = ROOT / "scripts/build_compression_b2b_pilot_metering_appendix_v1.py"


def test_example_matches_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_builder_seed_demo_validates(tmp_path: Path) -> None:
    log = tmp_path / "meter.jsonl"
    out = tmp_path / "appendix.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--metering-log",
            str(log),
            "--out",
            str(out),
            "--seed-demo",
            "--tenant-id",
            "pytest-tenant",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["metering"]["events_total"] == 3
    assert doc["governance"]["publish_allowed"] is False
    assert 0.0 <= doc["metering"]["aggregate"]["global_saving_rate"] <= 1.0


def test_billing_meter_required_fields() -> None:
    from scripts.core.billing_meter import append_meter_event, validate_meter_event

    row = {"sla_track": "active", "tokens_before": 10, "tokens_after": 5}
    validate_meter_event(row)
    log = ROOT / "reports/constitution/btrack_pilot/_pytest_meter_touch.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        res = append_meter_event(row)
        assert res.get("accepted") is True
    finally:
        if log.is_file():
            log.unlink()
