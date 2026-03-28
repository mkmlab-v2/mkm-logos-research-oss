#!/usr/bin/env python3
"""
Verify Logos manuscript JSONL rows (DSS, apocrypha, etc.): UTF-8, schema, optional char_len/sha256.

Unlike IJEOMA chunk tables (line-range join to canonical TXT), manuscript rows are self-contained.
Canonical string for hashing (per row):
  - If ``text`` is non-empty after strip: use ``text``.
  - Else: (text_hebrew or "") + (text_greek or "")  (no separator; matches fragment-style glue)

When ``char_len`` and ``sha256`` are present on a row, they MUST match recomputed values.
Run from repo root:  py scripts/verify_logos_manuscripts_integrity.py
No PYTHONPATH required (stdlib + pathlib only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def canonical_text_for_row(row: dict[str, Any]) -> str:
    t = (row.get("text") or "").strip()
    if t:
        return row.get("text") or ""
    h = row.get("text_hebrew") or ""
    g = row.get("text_greek") or ""
    return f"{h}{g}"


def row_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _append_failure(
    failures: list[dict[str, Any]],
    max_failures: int,
    rec: dict[str, Any],
) -> bool:
    """Return True if caller should stop processing (cap reached)."""
    failures.append(rec)
    return len(failures) >= max_failures


def verify_jsonl(
    path: Path,
    strict_hashes: bool,
    max_failures: int,
) -> tuple[int, int, list[dict[str, Any]]]:
    """
    Returns (exit_code_hint, rows_ok, failures).
    exit_code_hint: 0 all pass, 1 has failures (caller may also use file missing -> 2).
    """
    failures: list[dict[str, Any]] = []
    rows_ok = 0
    line_no = 0

    with path.open(encoding="utf-8") as f:
        for raw in f:
            line_no += 1
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                if _append_failure(
                    failures,
                    max_failures,
                    {"path": str(path), "line": line_no, "reason": f"JSON decode: {e}"},
                ):
                    break
                continue

            if not isinstance(row, dict):
                if _append_failure(
                    failures,
                    max_failures,
                    {"path": str(path), "line": line_no, "reason": "row is not an object"},
                ):
                    break
                continue

            missing = [k for k in ("source", "verse_id") if k not in row]
            if missing:
                if _append_failure(
                    failures,
                    max_failures,
                    {
                        "path": str(path),
                        "line": line_no,
                        "verse_id": row.get("verse_id"),
                        "reason": f"missing required key(s): {missing}",
                    },
                ):
                    break
                continue

            ct = canonical_text_for_row(row)
            if not ct.strip():
                if _append_failure(
                    failures,
                    max_failures,
                    {
                        "path": str(path),
                        "line": line_no,
                        "verse_id": row.get("verse_id"),
                        "reason": "empty canonical text (text, text_hebrew, text_greek all empty)",
                    },
                ):
                    break
                continue

            got_len = len(ct.encode("utf-8"))
            got_sha = row_sha256(ct)

            has_len = "char_len" in row
            has_sha = "sha256" in row
            if has_len ^ has_sha:
                if _append_failure(
                    failures,
                    max_failures,
                    {
                        "path": str(path),
                        "line": line_no,
                        "verse_id": row.get("verse_id"),
                        "reason": "char_len and sha256 must both be set if either is present",
                    },
                ):
                    break
                continue

            if has_len and has_sha:
                try:
                    exp_len = int(row["char_len"])
                except (TypeError, ValueError) as e:
                    if _append_failure(
                        failures,
                        max_failures,
                        {
                            "path": str(path),
                            "line": line_no,
                            "verse_id": row.get("verse_id"),
                            "reason": f"invalid char_len: {e}",
                        },
                    ):
                        break
                    continue
                exp_sha = str(row["sha256"]).strip().lower()
                if got_len != exp_len or got_sha != exp_sha:
                    if _append_failure(
                        failures,
                        max_failures,
                        {
                            "path": str(path),
                            "line": line_no,
                            "verse_id": row.get("verse_id"),
                            "expected_len": exp_len,
                            "got_len": got_len,
                            "expected_sha256": exp_sha,
                            "got_sha256": got_sha,
                        },
                    ):
                        break
                    continue
            elif strict_hashes:
                if _append_failure(
                    failures,
                    max_failures,
                    {
                        "path": str(path),
                        "line": line_no,
                        "verse_id": row.get("verse_id"),
                        "reason": "strict: char_len and sha256 required on each row",
                    },
                ):
                    break
                continue

            rows_ok += 1

    return (0 if not failures else 1, rows_ok, failures)


def main() -> int:
    root = repo_root()
    default_dss = root / "data/logos/manuscripts/dss_parsed.jsonl"
    default_apo = root / "data/logos/manuscripts/apocrypha_std.jsonl"

    ap = argparse.ArgumentParser(
        description="Verify Logos manuscript JSONL integrity (schema, UTF-8, optional char_len/sha256)"
    )
    ap.add_argument(
        "--jsonl",
        type=Path,
        nargs="*",
        default=[default_dss, default_apo],
        help="One or more JSONL files under data/logos/manuscripts/",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Require char_len and sha256 on every row (pipeline-ready)",
    )
    ap.add_argument(
        "--max-failures",
        type=int,
        default=50,
        help="Stop reporting after N failures",
    )
    args = ap.parse_args()

    any_missing = False
    overall_failures: list[dict[str, Any]] = []
    total_rows = 0

    for p in args.jsonl:
        p = p.resolve()
        if not p.is_file():
            print(f"ERROR: file missing: {p}", file=sys.stderr)
            any_missing = True
            continue

        code, n_ok, fails = verify_jsonl(p, args.strict, args.max_failures)
        total_rows += n_ok
        print(f"File: {p}")
        print(f"  Rows OK (passed checks): {n_ok}")
        if fails:
            overall_failures.extend(fails)
        if code != 0 and not fails:
            # e.g. empty file
            print(f"  WARN: no rows passed (empty or all failed before ok count)")

    if any_missing:
        return 2

    if overall_failures:
        print(f"\nFAIL: {len(overall_failures)} issue(s) (showing up to {args.max_failures}):")
        for m in overall_failures[: args.max_failures]:
            print(json.dumps(m, ensure_ascii=False))
        return 1

    print(f"\nOK: all manuscript JSONL checks passed ({total_rows} row(s)).")
    if not args.strict:
        print(
            "Note: rows without char_len/sha256 are accepted; use --strict after backfilling hashes."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
