#!/usr/bin/env python3
"""Sniff weather CSV encoding, delimiter, and likely date/precip columns (B-track helper)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def sniff_csv(path: Path, *, sample_lines: int = 20) -> dict[str, Any]:
    raw = path.read_bytes()
    encoding = "utf-8-sig"
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    text = raw.decode(encoding, errors="replace")
    lines = text.splitlines()[:sample_lines]
    sample = "\n".join(lines)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.reader(lines, delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("empty csv")
    header = [c.strip() for c in rows[0]]
    data_rows = rows[1:] if header else rows
    if not header or not any(any(ch.isalpha() for ch in c) for c in header):
        header = [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows
    date_col = None
    precip_col = None
    date_format = "%Y-%m-%d"
    for i, name in enumerate(header):
        low = name.lower()
        if date_col is None and any(k in low for k in ("date", "day", "tm", "obs", "일자", "날짜")):
            date_col = name
        if precip_col is None and any(
            k in low for k in ("precip", "rain", "rn", "강수", "rainfall", "prcp")
        ):
            precip_col = name
    if date_col is None and header:
        date_col = header[0]
    if precip_col is None and len(header) > 1:
        precip_col = header[1]
    return {
        "encoding": encoding,
        "delimiter": delimiter,
        "header": header,
        "date_col": date_col,
        "precip_col": precip_col,
        "date_format": date_format,
        "sample_rows": len(data_rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--json", action="store_true", help="Print JSON sniff result")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2
    try:
        result = sniff_csv(ns.input)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for k, v in result.items():
            if k != "header":
                print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
