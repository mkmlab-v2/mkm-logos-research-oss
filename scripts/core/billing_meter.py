"""Append-only Track A metering log (JSONL) for shadow / API instrumentation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REL = "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl"
ENV_KEY = "TRACK_A_METERING_LOG_PATH"

REQUIRED_FIELDS = frozenset({"sla_track", "tokens_before", "tokens_after"})


def default_meter_log_path() -> Path:
    return ROOT / DEFAULT_REL


def resolve_meter_log_path() -> Path:
    raw = os.environ.get(ENV_KEY, "").strip()
    return Path(raw) if raw else default_meter_log_path()


def validate_meter_event(d: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - d.keys()
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    if not isinstance(d["sla_track"], str) or not str(d["sla_track"]).strip():
        raise ValueError("sla_track must be a non-empty string")
    for key in ("tokens_before", "tokens_after"):
        v = d[key]
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"{key} must be int >= 0")


def append_meter_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate, stamp schema/time, append one JSON line. No secrets in payload."""
    validate_meter_event(raw)
    event = dict(raw)
    event.setdefault("meter_schema", "track_a_metering_log_v1")
    if "ts_utc" not in event:
        event["ts_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = resolve_meter_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        rel = str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        rel = str(path.resolve()).replace("\\", "/")
    return {
        "accepted": True,
        "meter_schema": str(event["meter_schema"]),
        "log_path_relative": rel,
    }
