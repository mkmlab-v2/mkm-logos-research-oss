#!/usr/bin/env python3
"""Validate commander profile JSON against schema + RQ-028 track-wall guards."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/commander_profile_v1.schema.json"


def _import_resolver():
    path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import profile resolver: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _policy_errors(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sasang = doc.get("sasang_reference") or {}
    if sasang.get("auto_merge_with_myeongni") is True:
        errors.append("sasang_reference.auto_merge_with_myeongni must be false")
    cognition = doc.get("cognition_hypothesis") or {}
    if cognition and cognition.get("rail") not in {None, "Track_B_HYPO"}:
        errors.append("cognition_hypothesis.rail must be Track_B_HYPO when present")
    coaching = doc.get("assist_coaching_v1") or {}
    if not coaching.get("track_wall"):
        errors.append("assist_coaching_v1.track_wall required")
    return errors


def validate_profile_doc(doc: dict[str, Any], *, schema_path: Path = SCHEMA_PATH) -> list[str]:
    errors: list[str] = []
    if not schema_path.is_file():
        return [f"schema missing: {schema_path}"]
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package required"]

    schema = _load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        errors.append(f"schema:{err.message}")
    errors.extend(_policy_errors(doc))
    return errors


def validate_profile_path(profile_path: Path) -> dict[str, Any]:
    doc = _load_json(profile_path)
    errors = validate_profile_doc(doc)
    return {
        "ok": not errors,
        "profile_path": str(profile_path),
        "schema": doc.get("schema"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate commander_profile_v1")
    parser.add_argument("--profile", type=Path, default=None, help="default: resolver chain")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    resolver = _import_resolver()
    profile_path, profile_source = resolver.resolve_commander_profile_path(args.profile)
    doc = _load_json(profile_path)
    errors = validate_profile_doc(doc, schema_path=args.schema)
    report = {
        "schema": "commander_profile_validation_report_v1",
        "ok": not errors,
        "profile_path": str(profile_path.relative_to(ROOT)).replace("\\", "/"),
        "profile_source": profile_source,
        "commander_profile_schema": doc.get("schema"),
        "errors": errors,
    }
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {args.out_json}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print(f"OK: {profile_path} source={profile_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
