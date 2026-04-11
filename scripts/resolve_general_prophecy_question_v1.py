#!/usr/bin/env python3
"""Set resolution on one binary question in a general_prophecy registry (B rail).

Does not call external APIs. Validates full registry after mutation.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(doc: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def _find_question(doc: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and q.get("question_id") == question_id:
            return q
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, required=True, help="Registry JSON")
    ap.add_argument("--output", "-o", type=Path, default=None, help="Written registry (omit with --stdout-only or --in-place)")
    ap.add_argument("--in-place", action="store_true", help="Overwrite --input")
    ap.add_argument("--stdout-only", action="store_true", help="Print JSON; no file write")
    ap.add_argument("--question-id", required=True, help="Target question_id")
    ap.add_argument(
        "--outcome",
        choices=("true", "false"),
        required=True,
        help="Binary outcome for resolved questions",
    )
    ap.add_argument("--notes", default="", help="resolver_notes")
    ap.add_argument(
        "--evidence-uri",
        action="append",
        default=[],
        metavar="URI",
        help="Repeatable; each must be length >= 8",
    )
    ns = ap.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2

    if ns.in_place and ns.output is not None:
        print("use only one of --in-place or --output", file=sys.stderr)
        return 2
    if not ns.stdout_only and not ns.in_place and ns.output is None:
        print("provide --output, --in-place, or --stdout-only", file=sys.stderr)
        return 2

    doc = _load_json(ns.input)
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("input must be general_prophecy_registry_v1", file=sys.stderr)
        return 2

    q = _find_question(doc, ns.question_id)
    if q is None:
        print(f"unknown question_id: {ns.question_id}", file=sys.stderr)
        return 2
    if (q.get("outcome_spec") or {}).get("kind") != "binary":
        print("only outcome_spec.kind=binary is supported", file=sys.stderr)
        return 2

    ob = ns.outcome == "true"
    res: dict[str, Any] = {
        "status": "resolved",
        "resolved_at_utc": _utc_now(),
        "outcome_binary": ob,
    }
    if ns.notes.strip():
        res["resolver_notes"] = ns.notes.strip()
    uris = [u for u in ns.evidence_uri if isinstance(u, str) and u.strip()]
    if uris:
        for u in uris:
            if len(u) < 8:
                print(f"evidence-uri too short: {u!r}", file=sys.stderr)
                return 2
        res["evidence_uris"] = uris

    q["resolution"] = res
    doc["generated_at_utc"] = _utc_now()
    _validate(doc)

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    out_path = ns.input if ns.in_place else ns.output
    assert out_path is not None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(str(out_path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
