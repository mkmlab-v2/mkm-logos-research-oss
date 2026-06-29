#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate AI Hub 2026 beta B-track catalog JSON against draft-07 schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError as e:
    print("jsonschema required: pip install jsonschema", file=sys.stderr)
    raise SystemExit(2) from e

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "aihub"
    / "aihub_2026_beta_catalog_v1.json"
)
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "aihub_2026_beta_catalog_v1.schema.json"


def validate_catalog(catalog_path: Path, schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"missing schema: {schema_path}"]
    if not catalog_path.is_file():
        return [f"missing catalog: {catalog_path}"]

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(catalog), key=lambda e: list(e.path))
    if errors:
        return [f"{list(e.path)}: {e.message}" for e in errors]

    msgs: list[str] = []
    if catalog.get("research_only") is not True:
        msgs.append("research_only must be true")
    if catalog.get("track_a_active_write") is not False:
        msgs.append("track_a_active_write must be false")

    for entry in catalog.get("entries", []):
        if entry.get("sample_status") == "received":
            sp = entry.get("sample_path")
            if not sp:
                msgs.append(f"{entry.get('dataset_id')}: sample_status=received requires sample_path")
            elif not (ROOT / sp).is_file():
                msgs.append(f"{entry.get('dataset_id')}: sample file missing at {sp}")

    return msgs


def main() -> int:
    p = argparse.ArgumentParser(description="Validate aihub_2026_beta_catalog_v1.json")
    p.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = p.parse_args()

    msgs = validate_catalog(args.catalog, args.schema)
    if msgs:
        for m in msgs:
            print(m, file=sys.stderr)
        return 1

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    pending = sum(1 for e in catalog["entries"] if e.get("sample_status") == "pending")
    print(
        f"OK: aihub_2026_beta_catalog_v1 entries={len(catalog['entries'])} "
        f"sample_pending={pending} research_only=True"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
