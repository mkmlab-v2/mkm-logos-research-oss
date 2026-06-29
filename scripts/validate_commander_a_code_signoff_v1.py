#!/usr/bin/env python3
"""Validate commander A-code sign-off JSON (RQ-029; human gate only)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/commander_a_code_signoff_v1.schema.json"


def _import_resolver():
    path = ROOT / "scripts/a_code_commander_signoff_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_signoff_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import signoff resolver: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _policy_errors(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    wall = doc.get("track_wall") or {}
    if wall.get("track_a_auto_promotion") is not False:
        errors.append("track_wall.track_a_auto_promotion must be false")
    if wall.get("live_trading_auto_trigger") is not False:
        errors.append("track_wall.live_trading_auto_trigger must be false")
    if doc.get("approved") is True:
        if not str(doc.get("signoff_by") or "").strip():
            errors.append("signoff_by required when approved=true")
        if not doc.get("signoff_utc"):
            errors.append("signoff_utc required when approved=true")
        attest = doc.get("attestations") or {}
        for key in (
            "human_commander_signoff",
            "separate_rq_from_rq026_closed",
            "no_track_a_live_auto_merge",
        ):
            if attest.get(key) is not True:
                errors.append(f"attestations.{key} must be true when approved=true")
    return errors


def validate_signoff_doc(doc: dict[str, Any], *, schema_path: Path = SCHEMA_PATH) -> list[str]:
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


def signoff_summary(doc: dict[str, Any], *, errors: list[str]) -> dict[str, Any]:
    attest = doc.get("attestations") or {}
    approved = bool(doc.get("approved")) and not errors
    return {
        "present": True,
        "ok": not errors,
        "approved": approved,
        "signoff_by": doc.get("signoff_by"),
        "signoff_utc": doc.get("signoff_utc"),
        "attestations": attest,
        "human_signoff_status": (
            "APPROVED"
            if approved and attest.get("human_commander_signoff") is True
            else ("PENDING" if doc.get("approved") is not True else "INVALID")
        ),
        "errors": errors,
    }


def validate_signoff_path(signoff_path: Path) -> dict[str, Any]:
    doc = _load_json(signoff_path)
    errors = validate_signoff_doc(doc)
    summary = signoff_summary(doc, errors=errors)
    summary["signoff_path"] = str(signoff_path)
    summary["schema"] = doc.get("schema")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate commander_a_code_signoff_v1")
    parser.add_argument("--signoff", type=Path, default=None)
    parser.add_argument("--allow-example", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    resolver = _import_resolver()
    signoff_path, source = resolver.resolve_commander_a_code_signoff_path(
        args.signoff,
        allow_example=args.allow_example,
    )
    if signoff_path is None:
        out = {
            "ok": True,
            "present": False,
            "source": source,
            "human_signoff_status": "ABSENT",
            "note_ko": "sign-off 파일 없음 — MANUAL 체크리스트 유지",
        }
        if args.out_json:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: signoff absent (source={source})")
        return 0

    doc = _load_json(signoff_path)
    errors = validate_signoff_doc(doc, schema_path=args.schema)
    result = {
        "ok": not errors,
        "source": source,
        **signoff_summary(doc, errors=errors),
    }
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for e in errors:
            print(f"ERR: {e}", file=sys.stderr)
        print(f"FAIL: {signoff_path}")
        return 1
    print(f"OK: {signoff_path} approved={result.get('approved')} status={result.get('human_signoff_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
