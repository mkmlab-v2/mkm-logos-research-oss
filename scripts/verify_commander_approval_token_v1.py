#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_KEYS = {
    "schema",
    "correlation_id",
    "approved_by",
    "approved_actions",
    "risk_level",
    "issued_at_utc",
    "expires_at_utc",
    "one_time",
}


def _parse_iso_utc(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify commander approval token for L2/L3 actions.")
    ap.add_argument("--token", required=True, help="Path to approval token JSON")
    ap.add_argument("--action", required=True, help="Requested action id")
    ap.add_argument("--risk-level", required=True, choices=["L2", "L3"])
    args = ap.parse_args()

    token_path = Path(args.token)
    if not token_path.exists():
        print("token_missing")
        return 2
    try:
        doc: dict[str, Any] = json.loads(token_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"token_json_invalid: {exc}")
        return 2

    missing = [k for k in REQUIRED_KEYS if k not in doc]
    if missing:
        print(f"token_missing_keys: {missing}")
        return 2
    if doc.get("schema") != "commander_approval_token_v1":
        print("token_schema_mismatch")
        return 2
    if doc.get("risk_level") != args.risk_level:
        print("token_risk_level_mismatch")
        return 3
    actions = doc.get("approved_actions")
    if not isinstance(actions, list) or args.action not in actions:
        print("token_action_not_approved")
        return 3
    if bool(doc.get("used")) and bool(doc.get("one_time", True)):
        print("token_already_used")
        return 3
    try:
        exp = _parse_iso_utc(str(doc.get("expires_at_utc")))
    except ValueError:
        print("token_expiry_parse_failed")
        return 2
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if now > exp:
        print("token_expired")
        return 3

    print("token_ok")
    print(f"correlation_id={doc.get('correlation_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

