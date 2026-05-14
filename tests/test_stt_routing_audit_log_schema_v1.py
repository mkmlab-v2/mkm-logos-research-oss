# Keywords: stt_routing_audit_log_v1, jsonschema, Silver STT audit

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "final" / "schemas" / "stt_routing_audit_log_v1.schema.json"
EXAMPLE = ROOT / "docs" / "final" / "schemas" / "stt_routing_audit_log_v1.minimal.example.json"


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_minimal_example_validates() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    jsonschema.validate(instance=example, schema=schema)


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_vendor_route_accepts_latency_and_provider() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    row = {
        "schema_version": "stt_routing_audit_log_v1",
        "event_id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
        "occurred_at_utc": "2026-05-15T10:01:00Z",
        "route": "vendor",
        "provider": "gcp_speech_v2",
        "audio_duration_ms": 8000,
        "latency_ms": 340,
        "error_code": None,
        "pii_redaction": "redacted_full",
        "hypothesis_tag": "[HYPO]",
    }
    jsonschema.validate(instance=row, schema=schema)


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_missing_required_field_fails() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    import jsonschema.exceptions

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    bad = {
        "schema_version": "stt_routing_audit_log_v1",
        "event_id": "cccccccc-cccc-4ccc-cccc-cccccccccccc",
        "occurred_at_utc": "2026-05-15T10:02:00Z",
        "route": "rejected",
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)
