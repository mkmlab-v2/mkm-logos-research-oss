#!/usr/bin/env python3
"""Validate Logos ontology mapping registry (schema + Fact-Lock invariants)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "artifacts" / "schemas" / "logos_ontology_schema_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_schema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        return ["jsonschema_missing: pip install jsonschema"]
    schema = _read_json(schema_path)
    validator = Draft7Validator(schema)
    return [f"schema:{e.message} ({'/'.join(str(x) for x in e.path)})" for e in validator.iter_errors(doc)]


def validate_invariants(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    guard = doc.get("guardrails") if isinstance(doc.get("guardrails"), dict) else {}
    if guard.get("non_gating_only") is not True:
        errors.append("invariant:guardrails.non_gating_only must be true")
    if guard.get("price_mapping_forbidden") is not True:
        errors.append("invariant:guardrails.price_mapping_forbidden must be true")
    if guard.get("execution_trigger_allowed") is not False:
        errors.append("invariant:guardrails.execution_trigger_allowed must be false")

    relations = doc.get("relations") if isinstance(doc.get("relations"), list) else []
    rule_ids: set[str] = set()
    for idx, row in enumerate(relations):
        if not isinstance(row, dict):
            continue
        rid = str(row.get("rule_id") or "")
        if rid in rule_ids:
            errors.append(f"invariant:duplicate rule_id `{rid}` at relations[{idx}]")
        rule_ids.add(rid)
        falsification = row.get("falsification_trigger")
        if not isinstance(falsification, list) or not falsification:
            errors.append(f"invariant:relations[{idx}].falsification_trigger must be non-empty")

    atoms = doc.get("entities", {}).get("atoms") if isinstance(doc.get("entities"), dict) else []
    atom_ids = {str(a.get("atom_id")) for a in atoms if isinstance(a, dict)}
    for idx, row in enumerate(relations):
        if not isinstance(row, dict):
            continue
        for atom_id in row.get("then_atoms") or []:
            aid = str(atom_id)
            if aid not in atom_ids:
                errors.append(f"invariant:relations[{idx}].then_atoms references unknown atom `{aid}`")

    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    doc = _read_json(Path(args.input))
    schema_path = Path(args.schema).resolve() if args.schema else DEFAULT_SCHEMA
    schema_errors = validate_schema(doc, schema_path)
    inv_errors = validate_invariants(doc) if not schema_errors else []
    errors = [*schema_errors, *inv_errors]
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("OK: logos ontology valid")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    doc = _read_json(Path(args.input))
    obs = doc.get("observation") if isinstance(doc.get("observation"), dict) else {}
    rows = {
        "schema": doc.get("schema"),
        "chaos_score": obs.get("chaos_score"),
        "order_score": obs.get("order_score"),
        "tension_score": obs.get("tension_score"),
        "phase_label": obs.get("phase_label"),
        "relations": len(doc.get("relations") or []),
    }
    print(json.dumps(rows, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate ontology JSON")
    p_val.add_argument("--input", "-i", required=True)
    p_val.add_argument("--schema", default="", help="Optional schema path")
    p_val.set_defaults(func=cmd_validate)

    p_sum = sub.add_parser("summary", help="Print compact summary")
    p_sum.add_argument("--input", "-i", required=True)
    p_sum.set_defaults(func=cmd_summary)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
