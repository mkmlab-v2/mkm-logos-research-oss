#!/usr/bin/env python3
"""Gate PersonaDiary moment intent weights SSOT + daily package coverage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_moment_intent_weights_v1 import (  # noqa: E402
    load_ssot,
    package_required_sections,
    validate_ssot,
)

SCHEMA = ROOT / "docs/final/schemas/personadiary_moment_intent_weights_v1.schema.json"
DEFAULT_SSOT = ROOT / "docs/final/artifacts/personadiary_moment_intent_weights_v1_latest.json"
DEFAULT_PACKAGE = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/personadiary_moment_intent_weights_gate_latest.json"


def _section_ids(package: dict) -> set[str]:
    return {
        str(sec["id"])
        for sec in (package.get("sections") or [])
        if isinstance(sec, dict) and sec.get("id")
    }


def check_package_coverage(package: dict) -> dict[str, list[str]]:
    required = package_required_sections()
    present = _section_ids(package)
    missing_by_intent: dict[str, list[str]] = {}
    for intent, req in required.items():
        miss = [sid for sid in req if sid not in present]
        if miss:
            missing_by_intent[intent] = miss
    return missing_by_intent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot-json", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--package-json", type=Path, default=DEFAULT_PACKAGE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    errors: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = load_ssot(str(args.ssot_json))
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"schema:{exc.message}")

    errors.extend(validate_ssot(doc))

    package_missing: dict[str, list[str]] = {}
    if args.package_json.is_file():
        package = json.loads(args.package_json.read_text(encoding="utf-8-sig"))
        package_missing = check_package_coverage(package)
        if package_missing:
            for intent, miss in package_missing.items():
                errors.append(f"package_missing:{intent}:{','.join(miss)}")

    ok = len(errors) == 0
    report = {
        "schema": "personadiary_moment_intent_weights_gate_v1",
        "ok": ok,
        "ssot_json": str(args.ssot_json.relative_to(ROOT)),
        "package_json": str(args.package_json.relative_to(ROOT)) if args.package_json.is_file() else None,
        "package_missing_sections": package_missing,
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
