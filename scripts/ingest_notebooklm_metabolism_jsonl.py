#!/usr/bin/env python3
"""Normalize NotebookLM / chat exports into LOG_METABOLISM JSONL (Fact-Lock).

- Strips optional Markdown ``` / ```json fences.
- Unwraps `nlm source content --json` style payloads: top-level {"value":{"content":"..."}}.
- Accepts either newline-delimited JSON objects or a single JSON array of objects.
- Validates required keys per LOG_METABOLISM_COHORT_ROW_V1 (minimal contract).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("window_start_utc", "egress_pressure", "throttle_events")


def _strip_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^\s*```(?:json)?\s*\r?\n?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\r?\n?\s*```\s*$", "", t, flags=re.IGNORECASE)
    return t.strip()


def _unwrap_nlm_json_wrapper(raw: str) -> str:
    s = raw.lstrip("\ufeff").strip()
    if not s.startswith("{"):
        return raw
    try:
        doc = json.loads(s)
    except json.JSONDecodeError:
        return raw
    if not isinstance(doc, dict):
        return raw
    val = doc.get("value")
    if isinstance(val, dict) and isinstance(val.get("content"), str):
        return val["content"]
    return raw


def _try_whole_file_as_json_array(text: str) -> list[dict[str, Any]] | None:
    t = text.strip()
    if not t or t[0] != "[":
        return None
    try:
        v = json.loads(t)
    except json.JSONDecodeError:
        return None
    if not isinstance(v, list):
        return None
    if not v:
        return []
    if not all(isinstance(x, dict) for x in v):
        return None
    return v


def _rows_from_text(text: str) -> list[dict[str, Any]]:
    body = _strip_fences(_unwrap_nlm_json_wrapper(text))
    arr = _try_whole_file_as_json_array(body)
    if arr is not None:
        return arr
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(body.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"line {i}: invalid JSON: {e}") from e
        if not isinstance(o, dict):
            raise ValueError(f"line {i}: expected object, got {type(o).__name__}")
        rows.append(o)
    return rows


def _validate_row(o: dict[str, Any], line_no: int) -> None:
    missing = [k for k in REQUIRED if k not in o]
    if missing:
        raise ValueError(f"line {line_no}: missing keys: {missing}")
    if not isinstance(o["window_start_utc"], str):
        raise ValueError(f"line {line_no}: window_start_utc must be string")
    for k in ("egress_pressure", "throttle_events"):
        v = o[k]
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ValueError(f"line {line_no}: {k} must be number (non-bool)")


def parse_and_validate_metabolism_jsonl(raw: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (rows, errors). rows is non-empty only when every row passes schema checks."""
    try:
        rows = _rows_from_text(raw)
    except ValueError as e:
        return [], [str(e)]
    errs: list[str] = []
    for i, o in enumerate(rows, start=1):
        try:
            _validate_row(o, i)
        except ValueError as e:
            errs.append(str(e))
    if errs:
        return [], errs
    return rows, []


def _fetch_via_nlm(source_id: str, nlm_bin: str) -> str:
    fd, name = tempfile.mkstemp(suffix="_nlm_source.txt")
    os.close(fd)
    tmp_path = Path(name)
    try:
        cp = subprocess.run(
            [nlm_bin, "source", "content", source_id, "-o", str(tmp_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if cp.returncode != 0:
            msg = (cp.stderr or cp.stdout or f"exit {cp.returncode}").strip()
            raise RuntimeError(f"nlm source content failed: {msg}")
        return tmp_path.read_text(encoding="utf-8", errors="replace")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", help="Raw text / nlm JSON export / pasted chat file.")
    ap.add_argument("--source-id", dest="source_id", help="Fetch raw via: nlm source content SOURCE_ID -o tmp")
    ap.add_argument("--nlm-bin", default="nlm", help="nlm executable name/path (default: nlm)")
    ap.add_argument(
        "--out",
        help="Output JSONL path (one compact JSON object per line). Required unless --dry-run.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate only; print JSON summary to stdout; no --out write.",
    )
    ap.add_argument(
        "--report",
        help="Optional JSON report path (valid_rows, errors).",
    )
    args = ap.parse_args()
    if bool(args.in_path) == bool(args.source_id):
        ap.error("Provide exactly one of --in or --source-id")
    if not args.dry_run and not args.out:
        ap.error("--out is required unless --dry-run")

    if args.source_id:
        raw = _fetch_via_nlm(args.source_id.strip(), args.nlm_bin.strip() or "nlm")
    else:
        in_path = Path(args.in_path)
        if not in_path.is_file():
            print(f"ERROR: --in not found: {in_path}", file=sys.stderr)
            return 2
        raw = in_path.read_text(encoding="utf-8-sig", errors="replace")

    rows, val_errs = parse_and_validate_metabolism_jsonl(raw)
    errors: list[dict[str, Any]] = [{"line": 0, "error": e} for e in val_errs]

    if args.report:
        rep = {
            "schema": "ingest_notebooklm_metabolism_jsonl_report_v1",
            "valid_rows": len(rows),
            "error_rows": len(val_errs),
            "errors": errors[:200],
        }
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(rep, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if val_errs:
        for e in val_errs[:50]:
            print(f"ERROR: {e}", file=sys.stderr)
        if len(val_errs) > 50:
            print(f"... and {len(val_errs) - 50} more errors", file=sys.stderr)
        if not args.dry_run:
            print("ERROR: no output written (fix rows and retry)", file=sys.stderr)
        if args.dry_run:
            print(
                json.dumps(
                    {"dry_run_ok": False, "valid_rows": 0, "errors": val_errs[:20]},
                    ensure_ascii=False,
                )
            )
        return 1

    if args.dry_run:
        print(
            json.dumps(
                {"dry_run_ok": True, "valid_rows": len(rows)},
                ensure_ascii=False,
            )
        )
        return 0

    out_lines = [
        json.dumps(o, ensure_ascii=False, separators=(",", ":")) for o in rows
    ]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")

    print(f"OK: wrote {out_path} valid_rows={len(out_lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
