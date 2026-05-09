#!/usr/bin/env python3
"""Ensure lens penalty shadow state artifact exists."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_STATE = ART / "lens_penalty_shadow_state_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    args = ap.parse_args()

    if args.state_json.is_file():
        print(f"OK: state exists: {args.state_json}")
        return 0

    payload = {
        "schema": "lens_penalty_shadow_state_v1",
        "updated_at_utc": _now(),
        "lens_state": {},
    }
    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.state_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
