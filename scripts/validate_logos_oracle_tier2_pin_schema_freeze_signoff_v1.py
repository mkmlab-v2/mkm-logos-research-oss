#!/usr/bin/env python3
"""Validate commander pin-schema freeze signoff for Oracle Logos Tier-2 ([HYPO] / human gate)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs/final/artifacts/logos_oracle_tier2_pin_schema_freeze_signoff_v1_latest.json"

from logos_oracle_tier2_incremental_append_lib_v1 import (  # noqa: E402
    READINESS_REL,
    pin_schema_snapshot_sha256,
    validate_signoff_doc,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT)
    ap.add_argument("--print-snapshot-sha256", action="store_true")
    args = ap.parse_args()

    if args.print_snapshot_sha256:
        readiness_path = ROOT / READINESS_REL
        if not readiness_path.is_file():
            print(f"FAIL: missing {READINESS_REL}", file=sys.stderr)
            return 1
        doc = json.loads(readiness_path.read_text(encoding="utf-8-sig"))
        snap = doc.get("tier2_pin_schema_snapshot") or {}
        digest = pin_schema_snapshot_sha256(snap)
        print(digest)
        print(f"artifact={READINESS_REL}")
        return 0

    path = args.path
    if not path.is_file():
        print(f"FAIL: missing signoff: {path}", file=sys.stderr)
        return 1

    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_signoff_doc(doc, root=ROOT)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(
        f"OK: approved={doc.get('approved')} send_gate={doc.get('send_gate')} "
        f"signoff_by={doc.get('signoff_by')!r}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
