#!/usr/bin/env python3
"""Offline gate: moment_bundle_pair_registry_v1 — visual↔BGM pair SSOT."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/moment_bundle_pair_registry_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/moment_bundle_pair_registry_v1.schema.json"
CHARTER = ROOT / "docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md"
PUBLIC = ROOT / "projects/no1kmedi/public/data/moment_bundle_pair_registry_v1.json"
GATE_EXAMPLE = ROOT / "docs/final/schemas/audio_bgm_gate_report_v1.example.json"


def main() -> int:
    missing = [p for p in (REGISTRY, SCHEMA, CHARTER) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"MISSING: {p}", file=sys.stderr)
        return 1

    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema") != "moment_bundle_pair_registry_v1":
        print("bad schema field", file=sys.stderr)
        return 1

    try:
        import jsonschema
    except ImportError:
        print("jsonschema not installed — run pytest for full validation", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)

    pairs = doc.get("pairs") or []
    ids = [p.get("moment_bundle_id") for p in pairs]
    if len(ids) != len(set(ids)):
        print("duplicate moment_bundle_id", file=sys.stderr)
        return 1

    wildcard = [p for p in pairs if p.get("match", {}).get("pathology_state") == "*"]
    if not wildcard:
        print("missing wildcard fallback pair", file=sys.stderr)
        return 1

    for pair in pairs:
        ref = (pair.get("bgm") or {}).get("audio_gate_report_ref")
        if ref and not (ROOT / ref).is_file():
            print(f"missing audio_gate_report_ref: {ref}", file=sys.stderr)
            return 1

    if PUBLIC.is_file():
        public = json.loads(PUBLIC.read_text(encoding="utf-8"))
        if public.get("registry_version") != doc.get("registry_version"):
            print("public registry drift — sync watch-personadiary-artifacts-dev", file=sys.stderr)
            return 1

    if not GATE_EXAMPLE.is_file():
        print(f"MISSING: {GATE_EXAMPLE}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "overall_ok": True,
                "registry_version": doc.get("registry_version"),
                "pair_count": len(pairs),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
