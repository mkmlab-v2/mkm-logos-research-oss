#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate showroom_public_bundle_v1.json — structure + public redaction (no wallet fields)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

REQUIRED_EVENT_KEYS: List[str] = [
    "timestamp",
    "active_character_id",
    "risk_level",
    "public_signal_direction",
    "abstract_reason",
    "schema_version",
    "event_id",
    "source",
]

FORBIDDEN_SUBSTRINGS: List[str] = [
    "balance_total_usdt",
    "balance_available",
    "api_key",
    "secret",
    "private_key",
]


def _flatten_strings(obj: Any, out: List[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _flatten_strings(v, out)


def _collect_keys(obj: Any, prefix: str, keys: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(f"{prefix}.{k}" if prefix else k)
            _collect_keys(v, f"{prefix}.{k}" if prefix else k, keys)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _collect_keys(v, f"{prefix}[{i}]", keys)


def validate_bundle(path: Path) -> List[str]:
    errors: List[str] = []
    raw = path.read_text(encoding="utf-8-sig")
    doc = json.loads(raw)
    if doc.get("schema") != "showroom_public_bundle_v1":
        errors.append("schema must be showroom_public_bundle_v1")

    pub = doc.get("public_event_v1")
    if not isinstance(pub, dict):
        errors.append("public_event_v1 must be an object")
        return errors

    for k in REQUIRED_EVENT_KEYS:
        if k not in pub:
            errors.append(f"public_event_v1 missing required key: {k}")

    if pub.get("schema_version") != "public-event.v1":
        errors.append("public_event_v1.schema_version must be public-event.v1")

    if pub.get("disclaimer_ref") != "jemaai_showroom_v1":
        errors.append("public_event_v1.disclaimer_ref must be jemaai_showroom_v1")

    dm = pub.get("delayed_metrics")
    if isinstance(dm, dict):
        ds = dm.get("delay_seconds")
        if ds is not None and not isinstance(ds, int):
            errors.append("delayed_metrics.delay_seconds must be int if present")
        if "pnl_pct_vs_start" in dm and dm["pnl_pct_vs_start"] is not None:
            p = dm["pnl_pct_vs_start"]
            if not isinstance(p, (int, float)):
                errors.append("delayed_metrics.pnl_pct_vs_start must be numeric if present")

    # Redaction: no obvious wallet leakage in public_event_v1 JSON text
    pub_text = json.dumps(pub, ensure_ascii=False)
    lower = pub_text.lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in lower:
            errors.append(f"public_event_v1 contains forbidden token: {bad}")

    strings: List[str] = []
    _flatten_strings(pub, strings)
    for s in strings:
        if re.search(r"\b1[0-9]{3}\.[0-9]{4,}\b", s):
            errors.append("public_event_v1 may contain large decimal resembling balance (redaction)")

    keys: Set[str] = set()
    _collect_keys(pub, "", keys)
    forbidden_key_fragments = ("balance", "position_size", "unrealized", "available_usdt")
    for fk in forbidden_key_fragments:
        if any(fk in k.lower() for k in keys):
            errors.append(f"public_event_v1 must not expose key containing: {fk}")

    pui = doc.get("public_ui")
    if pui is not None:
        if not isinstance(pui, dict):
            errors.append("public_ui must be an object if present")
        else:
            if pui.get("schema") != "showroom_public_ui_v1":
                errors.append("public_ui.schema must be showroom_public_ui_v1")
            pui_text = json.dumps(pui, ensure_ascii=False).lower()
            for bad in FORBIDDEN_SUBSTRINGS:
                if bad in pui_text:
                    errors.append(f"public_ui contains forbidden token: {bad}")

    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "path",
        nargs="?",
        default="docs/final/artifacts/showroom_public_bundle_v1.json",
        help="Path to showroom_public_bundle_v1.json",
    )
    args = p.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"[validate-showroom] FAIL: file not found: {path}", file=sys.stderr)
        return 2
    errs = validate_bundle(path)
    if errs:
        for e in errs:
            print(f"[validate-showroom] FAIL: {e}", file=sys.stderr)
        return 1
    print(f"[validate-showroom] OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
