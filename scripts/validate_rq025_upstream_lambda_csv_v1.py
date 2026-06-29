#!/usr/bin/env python3
"""[HYPO] Validate upstream sgp_history CSV schema before RQ-025 injection."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_upstream_lambda_csv_validation_v1_latest.json"
SCHEMA = "rq025_upstream_lambda_csv_validation_v1"
REQUIRED_NUMERIC = ("S", "L", "K", "M", "lambda_t")
OPTIONAL_NUMERIC = ("lambda_ma", "lambda_std", "z_score", "gradient")
MIN_ROWS = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_date(row: dict[str, str]) -> str:
    dk = str(row.get("") or row.get("date") or "").strip()[:10]
    return dk if len(dk) == 10 else ""


def validate_csv(path: Path, *, min_rows: int = MIN_ROWS) -> dict[str, Any]:
    errors: list[str] = []
    if not path.is_file():
        return {"ok": False, "errors": [f"missing file: {path}"], "row_count": 0}

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    if not fields:
        errors.append("empty header")
    missing = [k for k in REQUIRED_NUMERIC if k not in fields]
    if missing:
        errors.append(f"missing columns: {missing}")

    dates: list[str] = []
    bad_required = 0
    bad_optional = 0
    for i, row in enumerate(rows):
        dk = _row_date(row)
        if dk:
            dates.append(dk)
        for k in REQUIRED_NUMERIC:
            if k not in fields:
                continue
            try:
                float(row[k])
            except (TypeError, ValueError):
                bad_required += 1
                if bad_required <= 3:
                    errors.append(f"row {i + 2} invalid required {k}")
        for k in OPTIONAL_NUMERIC:
            if k not in fields:
                continue
            raw = (row.get(k) or "").strip()
            if not raw:
                continue
            try:
                float(raw)
            except (TypeError, ValueError):
                bad_optional += 1
                if bad_optional <= 3:
                    errors.append(f"row {i + 2} invalid optional {k}")

    if len(rows) < min_rows:
        errors.append(f"row_count {len(rows)} < min_rows {min_rows}")
    if bad_required > 0:
        errors.append(f"invalid required numeric cells: {bad_required} total")
    if bad_optional > 3:
        errors.append(f"invalid optional numeric cells: {bad_optional} total")

    dates.sort()
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "row_count": len(rows),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "fields": fields,
        "is_full_history_guess": len(rows) >= 500,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--min-rows", type=int, default=MIN_ROWS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    path = args.csv_path if args.csv_path.is_absolute() else ROOT / args.csv_path
    result = validate_csv(path, min_rows=args.min_rows)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "csv_path": str(path),
        **result,
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} ok={result['ok']} rows={result['row_count']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
