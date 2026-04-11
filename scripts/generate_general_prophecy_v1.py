#!/usr/bin/env python3
"""General prophecy registry pass-through + optional stub forecasts (B rail only).

Validates payload against docs/final/GENERAL_PROPHECY_SCHEMA_V1.json, refreshes
generated_at_utc, optionally appends baseline forecasts for empty slots.

Does not call external APIs (Polymarket, etc.). See CONSTITUTION Prophecy section.
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
DEFAULT_IN = ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"


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


def _stub_forecasts(doc: dict[str, Any]) -> None:
    if doc.get("schema") != "general_prophecy_registry_v1":
        return
    now = _utc_now()
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        fc = q.get("forecasts")
        if isinstance(fc, list) and len(fc) > 0:
            continue
        q["forecasts"] = [
            {
                "issued_at_utc": now,
                "probability_0_1": 0.5,
                "source_kind": "baseline",
                "source_detail": "generate_general_prophecy_v1_stub",
                "brier_ready": True,
            }
        ]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", "-i", type=Path, default=DEFAULT_IN, help="Registry JSON")
    p.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT, help="Output path")
    p.add_argument(
        "--stub-forecasts",
        action="store_true",
        help="Append baseline 0.5 forecast when forecasts[] empty",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate only; no write")
    p.add_argument("--stdout-only", action="store_true", help="Print JSON; no file write")
    ns = p.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2

    doc = _load_json(ns.input)
    if ns.stub_forecasts:
        _stub_forecasts(doc)
    doc["generated_at_utc"] = _utc_now()
    _validate(doc)

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.dry_run:
        print("ok", doc.get("schema"), len(doc.get("questions") or []))
        return 0
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(text, encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
