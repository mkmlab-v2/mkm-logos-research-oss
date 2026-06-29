#!/usr/bin/env python3
"""Validate PUBLIC_FACING audit record for Oracle Logos Tier-2 incremental append."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs/final/artifacts/logos_oracle_tier2_public_facing_audit_v1_latest.json"

from logos_oracle_tier2_incremental_append_lib_v1 import validate_audit_doc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT)
    args = ap.parse_args()

    path = args.path
    if not path.is_file():
        print(f"FAIL: missing audit: {path}", file=sys.stderr)
        return 1

    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_audit_doc(doc, root=ROOT)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(f"OK: audit_pass={doc.get('audit_pass')} auditor={doc.get('auditor')!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
