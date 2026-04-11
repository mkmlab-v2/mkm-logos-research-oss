#!/usr/bin/env python3
"""Apply field-level patches to general_prophecy_latest (B rail) without hand-editing the big JSON.

Patch file schema (JSON):
  {
    "schema": "general_prophecy_registry_patch_v1",
    "patches": [
      {
        "question_id": "existing_slug",
        "layer3_interpretation_ref": "docs/final/NOTEBOOKLM_....md",
        "resolution_criteria": "optional — replaces full rubric if present",
        "prophecy_track": "general | financial | personalized",
        "personalization_scope_v1": { "mode": "cohort", "cohort_id": "pilot.v1" }
      }
    ]
  }

Only whitelisted question fields are merged (see PATCH_KEYS). Unknown question_id → exit 2.
Does not call NotebookLM; use this after exporting a note to a repo path or pasting a pointer string.

Validates output against docs/final/GENERAL_PROPHECY_SCHEMA_V1.json (requires jsonschema).
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
DEFAULT_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"

PATCH_SCHEMA = "general_prophecy_registry_patch_v1"
# Safe, schema-backed fields for in-place updates (no forecasts/L1 overwrite by default).
PATCH_KEYS = frozenset(
    {
        "layer3_interpretation_ref",
        "resolution_criteria",
        "domain_tags",
        "boundary_ack",
        "prophecy_track",
        "personalization_scope_v1",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_registry(doc: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def _index_questions(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out[q["question_id"]] = q
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Target registry JSON (default: general_prophecy_latest.json)",
    )
    ap.add_argument("--patch", "-p", type=Path, required=True, help="Patch JSON file")
    ap.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write result here (default: overwrite --registry)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate only; no write")
    ns = ap.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    if not ns.registry.is_file():
        print(f"missing registry: {ns.registry}", file=sys.stderr)
        return 2
    if not ns.patch.is_file():
        print(f"missing patch: {ns.patch}", file=sys.stderr)
        return 2

    raw = _load_json(ns.patch)
    if raw.get("schema") != PATCH_SCHEMA:
        print(f"patch schema must be {PATCH_SCHEMA}", file=sys.stderr)
        return 2
    patches = raw.get("patches")
    if not isinstance(patches, list):
        print("patches must be a list", file=sys.stderr)
        return 2

    doc = _load_json(ns.registry)
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("registry must be general_prophecy_registry_v1", file=sys.stderr)
        return 2

    by_id = _index_questions(doc)
    applied = 0
    for i, p in enumerate(patches, 1):
        if not isinstance(p, dict):
            print(f"patch[{i}]: not an object", file=sys.stderr)
            return 2
        qid = p.get("question_id")
        if not isinstance(qid, str) or not qid.strip():
            print(f"patch[{i}]: missing question_id", file=sys.stderr)
            return 2
        if qid not in by_id:
            print(f"patch[{i}]: unknown question_id: {qid}", file=sys.stderr)
            return 2
        tgt = by_id[qid]
        n = 0
        for k in PATCH_KEYS:
            if k not in p:
                continue
            val = p[k]
            if val is None:
                continue
            tgt[k] = val
            n += 1
        if n:
            applied += 1

    doc["generated_at_utc"] = _utc_now()
    _validate_registry(doc)

    out_path = ns.output or ns.registry
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.dry_run:
        print(f"ok dry-run: would apply patches touching {applied} question(s); write {out_path}")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(str(out_path.resolve()))
    print(f"patches applied: {applied} question(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
