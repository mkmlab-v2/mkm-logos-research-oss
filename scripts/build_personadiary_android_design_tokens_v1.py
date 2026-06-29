#!/usr/bin/env python3
"""Build/sync PersonaDiary Android design tokens SSOT artifact."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_android_design_tokens_v1 import (  # noqa: E402
    DEFAULT_SSOT,
    SCHEMA_PATH,
    load_ssot,
    validate_ssot,
)

REPORTS_OUT = ROOT / "reports/personadiary_android_design_tokens_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot-json", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    if not args.ssot_json.is_file():
        print(f"MISSING: {args.ssot_json}", file=sys.stderr)
        return 1

    doc = load_ssot(args.ssot_json)
    errors = validate_ssot(doc)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    if args.check_only:
        print(json.dumps({"ok": True, "ssot": str(args.ssot_json.relative_to(ROOT))}, ensure_ascii=False))
        return 0

    doc = dict(doc)
    doc["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    args.ssot_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORTS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.ssot_json}")
    print(f"WROTE: {REPORTS_OUT}")
    print(f"SCHEMA: {SCHEMA_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
