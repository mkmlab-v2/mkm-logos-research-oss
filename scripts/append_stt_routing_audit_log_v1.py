# Keywords: stt_routing_audit_log_v1, append-only, Silver STT audit
"""Append one validated JSON line to an STT routing audit JSONL (research / B-track boundary)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "stt_routing_audit_log_v1.schema.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate(row: Dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as e:  # pragma: no cover
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=row, schema=schema)


def _build_row(
    *,
    route: str,
    audio_duration_ms: int,
    session_id: str | None,
    provider: str | None,
    latency_ms: int | None,
    pii_redaction: str,
    hypothesis_tag: str,
    event_id: str | None,
) -> Dict[str, Any]:
    eid = event_id or str(uuid.uuid4())
    row: Dict[str, Any] = {
        "schema_version": "stt_routing_audit_log_v1",
        "event_id": eid,
        "occurred_at_utc": _utc_now_z(),
        "route": route,
        "audio_duration_ms": int(audio_duration_ms),
        "pii_redaction": pii_redaction,
        "hypothesis_tag": hypothesis_tag,
    }
    if session_id:
        row["session_id"] = session_id
    if provider is not None:
        row["provider"] = provider
    if latency_ms is not None:
        row["latency_ms"] = int(latency_ms)
    return row


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "reports" / "stt_routing_audit_log_v1.jsonl")
    p.add_argument("--route", choices=("local", "vendor", "rejected"), required=True)
    p.add_argument("--audio-ms", type=int, required=True)
    p.add_argument("--session-id", default="")
    p.add_argument("--provider", default="")
    p.add_argument("--latency-ms", type=int, default=None)
    p.add_argument(
        "--pii-redaction",
        default="redacted_full",
        choices=("redacted_full", "redacted_partial", "not_applicable", "unknown"),
    )
    p.add_argument("--hypothesis-tag", default="[HYPO]")
    p.add_argument("--event-id", default="", help="UUID for idempotent replay; default random v4")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    provider: str | None = args.provider or None
    if args.route != "vendor":
        provider = None if not (args.provider or "").strip() else args.provider

    row = _build_row(
        route=args.route,
        audio_duration_ms=args.audio_ms,
        session_id=(args.session_id or None),
        provider=provider,
        latency_ms=args.latency_ms,
        pii_redaction=args.pii_redaction,
        hypothesis_tag=args.hypothesis_tag,
        event_id=(args.event_id or None),
    )
    _validate(row)
    if args.dry_run:
        print(json.dumps(row, ensure_ascii=False))
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
