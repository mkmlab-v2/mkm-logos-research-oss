#!/usr/bin/env python3
"""Append or validate MKM prior-art search log rows (JSONL).

  py scripts/append_mkm_prior_art_search_log_v1.py --validate-only
  py scripts/append_mkm_prior_art_search_log_v1.py --from-json row.json
  py scripts/append_mkm_prior_art_search_log_v1.py --seed-template
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "docs/research/nextgen_ltm_knowledge_os/PRIOR_ART_SEARCH_LOG.jsonl"
DEFAULT_TEMPLATE = ROOT / "docs/research/nextgen_ltm_knowledge_os/PRIOR_ART_SEARCH_LOG_TEMPLATE.jsonl"
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_prior_art_search_log_row_v1.schema.json"
ROW_SCHEMA = "mkm_prior_art_search_log_row_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_row(row: dict[str, Any], *, strict_schema: bool) -> list[str]:
    errors: list[str] = []
    if row.get("schema") != ROW_SCHEMA:
        errors.append(f"schema must be {ROW_SCHEMA!r}")
    for key in (
        "recorded_at_utc",
        "topic",
        "claim_under_review",
        "classification",
        "source_title",
        "overlap_summary",
        "search_method",
    ):
        if not str(row.get(key) or "").strip():
            errors.append(f"missing or empty: {key}")
    cls = row.get("classification")
    if cls not in {"FACT", "HYPO", "ROADMAP", "reference_only"}:
        errors.append(f"invalid classification: {cls!r}")
    if strict_schema:
        try:
            import jsonschema

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
            jsonschema.validate(row, schema)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            errors.append(f"jsonschema: {exc}")
    return errors


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            rows.append(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{i}: {exc}") from exc
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--from-json", type=Path, default=None, help="single row JSON file to append")
    ap.add_argument("--seed-template", action="store_true", help="copy template rows into log if log empty")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--strict-schema", action="store_true")
    args = ap.parse_args()

    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else ROOT / args.log_jsonl

    if args.seed_template:
        if log_path.is_file() and log_path.read_text(encoding="utf-8").strip():
            print(f"SKIP seed: log not empty: {log_path}")
        else:
            template = DEFAULT_TEMPLATE if DEFAULT_TEMPLATE.is_file() else None
            if not template:
                print(f"FAIL: missing template: {DEFAULT_TEMPLATE}", file=sys.stderr)
                return 1
            rows = _read_jsonl(template)
            for row in rows:
                errs = _validate_row(row, strict_schema=args.strict_schema)
                if errs:
                    print(f"FAIL template row: {errs}", file=sys.stderr)
                    return 1
            _write_jsonl(log_path, rows)
            print(f"SEEDED: {log_path} rows={len(rows)}")

    if args.from_json:
        src = args.from_json if args.from_json.is_absolute() else ROOT / args.from_json
        row = json.loads(src.read_text(encoding="utf-8-sig"))
        if not row.get("recorded_at_utc"):
            row["recorded_at_utc"] = _utc()
        if not row.get("schema"):
            row["schema"] = ROW_SCHEMA
        errs = _validate_row(row, strict_schema=args.strict_schema)
        if errs:
            print(f"FAIL: {errs}", file=sys.stderr)
            return 1
        existing = _read_jsonl(log_path)
        existing.append(row)
        _write_jsonl(log_path, existing)
        print(f"APPENDED: {log_path} total_rows={len(existing)}")

    rows = _read_jsonl(log_path)
    all_errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        errs = _validate_row(row, strict_schema=args.strict_schema)
        for err in errs:
            all_errors.append(f"line {i}: {err}")

    if all_errors:
        for err in all_errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(f"OK: {log_path} rows={len(rows)}")
    if not args.validate_only and not args.from_json and not args.seed_template:
        print("hint: --validate-only | --seed-template | --from-json row.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
