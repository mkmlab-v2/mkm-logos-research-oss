#!/usr/bin/env python3
"""Audit mkm_cursor_turn_meta_log.jsonl — suspect_first compliance signals."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports/mkm_cursor_turn_meta_log.jsonl"
DEFAULT_OUT = ROOT / "reports/mkm_cursor_turn_meta_audit_v1_latest.json"

SPARSE_WARN_LINES = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"_parse_error": True, "raw": line[:200]})
    return rows


def audit_turn_meta_log(rows: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[str] = []
    violations: list[str] = []

    if not rows:
        warnings.append("sparse_log:0_lines")
    elif len(rows) < SPARSE_WARN_LINES:
        warnings.append(f"sparse_log:{len(rows)}_lines_lt_{SPARSE_WARN_LINES}")

    parse_errors = sum(1 for r in rows if r.get("_parse_error"))
    if parse_errors:
        violations.append(f"jsonl_parse_errors:{parse_errors}")

    continuity_ids: set[str] = set()
    with_self_audit = 0
    with_violation_flags = 0
    with_missing_ssot = 0
    suspect_first_ok = 0

    for row in rows:
        if row.get("_parse_error"):
            continue
        cid = str(row.get("continuity_id") or "").strip()
        if cid:
            continuity_ids.add(cid)
        sa = row.get("self_audit") if isinstance(row.get("self_audit"), dict) else {}
        if sa:
            with_self_audit += 1
            if sa.get("suspect_first") is True:
                suspect_first_ok += 1
        flags = sa.get("violation_flags") if isinstance(sa, dict) else row.get("unverified_claims")
        if isinstance(flags, list) and flags:
            with_violation_flags += 1
        missing = row.get("required_ssot_missing")
        if isinstance(missing, list) and missing:
            with_missing_ssot += 1

    valid = max(len(rows) - parse_errors, 0)
    if valid and with_self_audit < valid:
        warnings.append(f"self_audit_missing:{valid - with_self_audit}_of_{valid}")
    if valid and suspect_first_ok < valid:
        warnings.append(f"suspect_first_not_true:{valid - suspect_first_ok}_of_{valid}")

    status = "PASS"
    if violations:
        status = "FAIL"
    elif warnings:
        status = "WARN"

    return {
        "schema": "mkm_cursor_turn_meta_audit_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "status": status,
        "log_path": "reports/mkm_cursor_turn_meta_log.jsonl",
        "row_count": len(rows),
        "valid_row_count": valid,
        "continuity_id_count": len(continuity_ids),
        "continuity_ids_sample": sorted(continuity_ids)[:12],
        "with_self_audit": with_self_audit,
        "suspect_first_true_count": suspect_first_ok,
        "rows_with_violation_flags": with_violation_flags,
        "rows_with_required_ssot_missing": with_missing_ssot,
        "warnings": warnings,
        "violations": violations,
        "reproducible_command": "py scripts/check_mkm_cursor_turn_meta_audit_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on violations (not on sparse_log WARN alone).",
    )
    parser.add_argument("--fail-on-sparse", action="store_true", help="Treat sparse_log as exit 1.")
    args = parser.parse_args(argv)

    rows = _read_jsonl(args.log)
    doc = audit_turn_meta_log(rows)
    doc["log_exists"] = args.log.is_file()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={doc['status']} rows={doc['row_count']} continuity_ids={doc['continuity_id_count']}")
    if doc["warnings"]:
        print(f"warnings={doc['warnings']}")
    if doc["violations"]:
        print(f"violations={doc['violations']}", file=sys.stderr)

    if args.strict and doc["violations"]:
        return 1
    if args.fail_on_sparse and any(w.startswith("sparse_log:") for w in doc["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
