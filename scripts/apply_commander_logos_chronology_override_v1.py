#!/usr/bin/env python3
"""Apply commander-authored logos_chronology_v1 JSON as SSOT, then print bundle command."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_chronology_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/logos_chronology_commander_override_v1.example.json"


def _validate(doc: dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema required: pip install jsonschema") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Commander logos_chronology_v1 JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--backup", action="store_true", help="Copy previous SSOT to .bak.<utc>")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input not found: {args.input}")
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    if doc.get("schema") != "logos_chronology_v1":
        raise SystemExit("schema must be logos_chronology_v1")
    _validate(doc)
    eras = doc.get("eras") or []
    bridges = doc.get("modern_bridges") or []
    if not eras:
        raise SystemExit("eras must be non-empty")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "would_write": str(args.out),
                    "eras": len(eras),
                    "modern_bridges": len(bridges),
                    "example_fixture": str(EXAMPLE),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.backup and args.out.is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = args.out.with_suffix(args.out.suffix + f".bak.{stamp}")
        shutil.copy2(args.out, bak)
        print(f"Backup: {bak}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} (eras={len(eras)}, bridges={len(bridges)})")
    print(
        "Next: powershell -NoProfile -ExecutionPolicy Bypass -File "
        "scripts\\Invoke-LogosChronologyParallelBundle_v1.ps1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
