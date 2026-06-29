#!/usr/bin/env python3
"""Validate commander A-code promotion RQ scope ack (RQ-031 second human gate)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/commander_a_code_promotion_rq_ack_v1.schema.json"


def _import_resolver():
    path = ROOT / "scripts/a_code_promotion_rq_ack_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_promotion_rq_ack_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import ack resolver: {path}")
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
    if doc.get("acknowledged") is True:
        if not str(doc.get("ack_by") or "").strip():
            errors.append("ack_by required when acknowledged=true")
        if not doc.get("ack_utc"):
            errors.append("ack_utc required when acknowledged=true")
        if not str(doc.get("ack_reference") or "").strip():
            errors.append("ack_reference required when acknowledged=true")
        scope = doc.get("scope_confirmed") or {}
        for key in (
            "operator_assist_trackc_only",
            "no_track_a_live_ms_merge",
            "separate_pr_for_constitution",
        ):
            if scope.get(key) is not True:
                errors.append(f"scope_confirmed.{key} must be true when acknowledged=true")
    return errors


def validate_ack_doc(doc: dict[str, Any], *, schema_path: Path = SCHEMA_PATH) -> list[str]:
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


def ack_summary(doc: dict[str, Any], *, errors: list[str]) -> dict[str, Any]:
    scope = doc.get("scope_confirmed") or {}
    acknowledged = bool(doc.get("acknowledged")) and not errors
    return {
        "present": True,
        "ok": not errors,
        "acknowledged": acknowledged,
        "ack_by": doc.get("ack_by"),
        "ack_utc": doc.get("ack_utc"),
        "ack_reference": doc.get("ack_reference"),
        "scope_confirmed": scope,
        "promotion_rq_ack_status": "ACKNOWLEDGED" if acknowledged else "PENDING",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ack", type=Path, default=None)
    parser.add_argument("--allow-example", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    resolver = _import_resolver()
    ack_path, source = resolver.resolve_promotion_rq_ack_path(args.ack, allow_example=args.allow_example)
    if ack_path is None:
        out = {
            "ok": True,
            "present": False,
            "source": source,
            "promotion_rq_ack_status": "ABSENT",
        }
        if args.out_json:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: promotion rq ack absent (source={source})")
        return 0

    doc = _load_json(ack_path)
    errors = validate_ack_doc(doc, schema_path=args.schema)
    result = {"ok": not errors, "source": source, **ack_summary(doc, errors=errors)}
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for e in errors:
            print(f"ERR: {e}", file=sys.stderr)
        return 1
    print(
        f"OK: {ack_path} acknowledged={result.get('acknowledged')} "
        f"status={result.get('promotion_rq_ack_status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
