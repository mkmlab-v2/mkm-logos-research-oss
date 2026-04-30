#!/usr/bin/env python3
"""Validate news_observation_v1 and optional direction_label_bar_v1 JSONL (B-track, research).

Exit 0 if all rows pass; exit 1 on first error (or aggregate with --continue-on-error).

Extra checks beyond JSON Schema:
- text_sha256 == SHA256(UTF-8 bytes of canonical_text)
- as_of_utc >= published_utc (and >= embargo_lift_utc when present)
- duplicate observation_id within the news file
- optional: direction labels hash matches canonical payload (see --verify-label-hashes)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NEWS_SCHEMA = ROOT / "docs" / "final" / "schemas" / "news_observation_v1.schema.json"
LABEL_SCHEMA = ROOT / "docs" / "final" / "schemas" / "direction_label_bar_v1.schema.json"


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc(s: str) -> datetime:
    t = str(s).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iter_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    text = path.read_text(encoding="utf-8-sig")
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        out.append((i, json.loads(line)))
    return out


def _validate_news_row(
    row: dict[str, Any],
    line_no: int,
    *,
    validator: Any,
    seen_ids: set[str],
) -> list[str]:
    errs: list[str] = []
    try:
        validator.validate(row)
    except Exception as e:
        errs.append(f"line {line_no}: schema: {e}")
        return errs

    oid = str(row.get("observation_id") or "")
    if oid in seen_ids:
        errs.append(f"line {line_no}: duplicate observation_id {oid!r}")
    seen_ids.add(oid)

    ct = row.get("canonical_text")
    if isinstance(ct, str):
        h = hashlib.sha256(ct.encode("utf-8")).hexdigest()
        if str(row.get("text_sha256") or "") != h:
            errs.append(f"line {line_no}: text_sha256 mismatch canonical_text")

    try:
        pub = _parse_utc(str(row["published_utc"]))
        as_of = _parse_utc(str(row["as_of_utc"]))
        if as_of < pub:
            errs.append(f"line {line_no}: as_of_utc < published_utc (lookahead risk)")
        emb = row.get("embargo_lift_utc")
        if emb:
            emb_dt = _parse_utc(str(emb))
            if as_of < emb_dt:
                errs.append(f"line {line_no}: as_of_utc < embargo_lift_utc")
            if emb_dt < pub:
                errs.append(f"line {line_no}: embargo_lift_utc < published_utc")
    except Exception as e:
        errs.append(f"line {line_no}: datetime parse: {e}")

    return errs


def _label_canonical_payload(row: dict[str, Any]) -> str | None:
    """Must match fixtures used to build label_sha256 (direction_label_bar_v1 samples)."""
    ins = row.get("instrument_id")
    ld = row.get("label_date")
    hz = row.get("horizon")
    d = row.get("direction")
    if not all(isinstance(x, str) for x in (ins, ld, hz, d)):
        return None
    nb = row.get("neutral_bps")
    if nb is None:
        return None
    return f"direction_label_bar_v1|{ins}|{ld}|{hz}|{d}|neutral_bps={nb}|v1"


def _validate_label_row(
    row: dict[str, Any],
    line_no: int,
    *,
    validator: Any,
    verify_hashes: bool,
) -> list[str]:
    errs: list[str] = []
    try:
        validator.validate(row)
    except Exception as e:
        errs.append(f"labels line {line_no}: schema: {e}")
        return errs
    if verify_hashes:
        payload = _label_canonical_payload(row)
        if payload is None:
            errs.append(f"labels line {line_no}: cannot verify label_sha256 (missing neutral_bps or fields)")
        else:
            h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if str(row.get("label_sha256") or "") != h:
                errs.append(f"labels line {line_no}: label_sha256 mismatch canonical payload")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate news_observation_v1 / direction_label_bar_v1 JSONL.")
    ap.add_argument(
        "--news-jsonl",
        type=Path,
        help="Path to news_observation JSONL (required unless --labels-jsonl-only).",
    )
    ap.add_argument("--labels-jsonl", type=Path, default=None, help="Optional direction_label_bar JSONL.")
    ap.add_argument(
        "--labels-jsonl-only",
        action="store_true",
        help="Only validate --labels-jsonl (skip news file).",
    )
    ap.add_argument(
        "--verify-label-hashes",
        action="store_true",
        help="Recompute direction_label_bar_v1 label_sha256 from canonical payload (needs neutral_bps).",
    )
    ap.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Report all errors instead of stopping after first batch.",
    )
    ap.add_argument("--max-rows", type=int, default=0, help="Max rows per file (0 = no limit).")
    args = ap.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("ERROR: pip install jsonschema", file=sys.stderr)
        return 1

    all_errs: list[str] = []

    if args.labels_jsonl_only and not args.labels_jsonl:
        print("ERROR: --labels-jsonl required with --labels-jsonl-only", file=sys.stderr)
        return 1
    if not args.labels_jsonl_only and not args.news_jsonl:
        print("ERROR: --news-jsonl required (or use --labels-jsonl-only with --labels-jsonl)", file=sys.stderr)
        return 1

    if not args.labels_jsonl_only:
        news_path = Path(args.news_jsonl).resolve()
        if not news_path.is_file():
            print(f"ERROR: not found: {news_path}", file=sys.stderr)
            return 1

        schema = _load_schema(NEWS_SCHEMA)
        v = jsonschema.Draft7Validator(schema)
        seen: set[str] = set()
        rows = _iter_jsonl(news_path)
        if args.max_rows > 0:
            rows = rows[: args.max_rows]
        for line_no, row in rows:
            all_errs.extend(_validate_news_row(row, line_no, validator=v, seen_ids=seen))
            if all_errs and not args.continue_on_error:
                break

    if args.labels_jsonl:
        lp = Path(args.labels_jsonl).resolve()
        if not lp.is_file():
            print(f"ERROR: labels file not found: {lp}", file=sys.stderr)
            return 1
        schema = _load_schema(LABEL_SCHEMA)
        v = jsonschema.Draft7Validator(schema)
        rows = _iter_jsonl(lp)
        if args.max_rows > 0:
            rows = rows[: args.max_rows]
        for line_no, row in rows:
            all_errs.extend(
                _validate_label_row(
                    row,
                    line_no,
                    validator=v,
                    verify_hashes=bool(args.verify_label_hashes),
                )
            )
            if all_errs and not args.continue_on_error:
                break

    if all_errs:
        for e in all_errs:
            print(e, file=sys.stderr)
        print(f"validate_news_observation_jsonl_v1: failed ({len(all_errs)} issue(s))", file=sys.stderr)
        return 1

    print("validate_news_observation_jsonl_v1: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
