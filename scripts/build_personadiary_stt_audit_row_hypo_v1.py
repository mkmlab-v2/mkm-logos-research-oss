#!/usr/bin/env python3
"""Build stt_routing_audit_log_v1 rows for PersonaDiary voice paste path [HYPO]."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

HYPOTHESIS_TAG = "[HYPO] personadiary_voice_paste_v1"
HYPOTHESIS_TAG_WEBSPEECH = "[HYPO] personadiary_voice_webspeech_v1"


def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_webspeech_stt_audit_row(
    *,
    event_id: str,
    transcript: str,
    session_id: str | None = None,
    route: str = "local",
    audio_duration_ms: int = 0,
) -> dict[str, Any]:
    """Web Speech API path — browser-local STT, no vendor billing."""
    row: dict[str, Any] = {
        "schema_version": "stt_routing_audit_log_v1",
        "event_id": event_id,
        "occurred_at_utc": utc_now_z(),
        "route": route,
        "audio_duration_ms": max(0, int(audio_duration_ms)),
        "pii_redaction": "redacted_full",
        "hypothesis_tag": HYPOTHESIS_TAG_WEBSPEECH,
        "chars_out": len(transcript or ""),
    }
    if session_id:
        row["session_id"] = session_id
    return row


def build_paste_stt_audit_row(
    *,
    event_id: str,
    transcript: str,
    session_id: str | None = None,
    route: str = "local",
    audio_duration_ms: int = 0,
) -> dict[str, Any]:
    """Paste / offline transcript path — route local, no vendor billing."""
    row: dict[str, Any] = {
        "schema_version": "stt_routing_audit_log_v1",
        "event_id": event_id,
        "occurred_at_utc": utc_now_z(),
        "route": route,
        "audio_duration_ms": max(0, int(audio_duration_ms)),
        "pii_redaction": "redacted_full",
        "hypothesis_tag": HYPOTHESIS_TAG,
        "chars_out": len(transcript or ""),
    }
    if session_id:
        row["session_id"] = session_id
    return row


def validate_stt_audit_row(row: dict[str, Any], schema_path) -> None:
    import json
    from pathlib import Path

    try:
        import jsonschema
    except ImportError as e:
        raise SystemExit("jsonschema required") from e
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema.validate(instance=row, schema=schema)


def append_stt_audit_row(row: dict[str, Any], out_path) -> None:
    import json
    from pathlib import Path

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
