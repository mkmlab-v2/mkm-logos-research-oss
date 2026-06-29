#!/usr/bin/env python3
"""Human sign-off ack validation for System2 gated apply paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    REPO_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "schemas"
    / "mkm_system2_human_signoff_ack_v1.schema.json"
)


def validate_signoff(path: Path, *, required_scope: str, schema_path: Path | None = None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        return [f"jsonschema_missing:{e}"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((schema_path or DEFAULT_SCHEMA).read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(doc)
    except Exception as exc:
        return [f"signoff_schema:{exc}"]
    errs: list[str] = []
    if doc.get("acknowledged") is not True:
        errs.append("acknowledged_not_true")
    scopes = doc.get("scopes") or []
    if required_scope not in scopes:
        errs.append(f"missing_scope:{required_scope}")
    return errs


def signoff_summary(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        "actor": doc.get("actor"),
        "scopes": doc.get("scopes"),
        "ack_at_utc": doc.get("ack_at_utc"),
    }
