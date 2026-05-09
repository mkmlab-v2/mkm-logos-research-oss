"""Append-only fallback trigger event meter (JSONL)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REL = "reports/constitution/btrack_pilot/fallback_trigger_event_log_v1.jsonl"
ENV_KEY = "FALLBACK_TRIGGER_EVENT_LOG_PATH"

REQUIRED_FIELDS = frozenset({"triggered", "tier"})


def default_fallback_log_path() -> Path:
    return ROOT / DEFAULT_REL


def resolve_fallback_log_path() -> Path:
    raw = os.environ.get(ENV_KEY, "").strip()
    return Path(raw) if raw else default_fallback_log_path()


def validate_fallback_event(d: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - d.keys()
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    if not isinstance(d["triggered"], bool):
        raise ValueError("triggered must be bool")
    if not isinstance(d["tier"], str) or not str(d["tier"]).strip():
        raise ValueError("tier must be non-empty string")


def append_fallback_event(raw: dict[str, Any]) -> dict[str, Any]:
    validate_fallback_event(raw)
    event = dict(raw)
    event.setdefault("event_schema", "fallback_trigger_event_v1")
    if "ts_utc" not in event:
        event["ts_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = resolve_fallback_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        rel = str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        rel = str(path.resolve()).replace("\\", "/")
    return {"accepted": True, "event_schema": str(event["event_schema"]), "log_path_relative": rel}

