#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Left-join session Myeongni panel CSV with optional weather + daily OHLCV (B-track, no APIs).

**Work order (Fact-Lock):**
  1) Build panel: ``build_btrack_session_instant_myeongni_panel_v1.py`` → CSV + ``.meta.json``.
  2) Prepare weather features CSV (any pipeline) keyed by **local calendar date** aligned with
     ``session_local_date`` semantics (operator responsibility).
  3) Prepare daily OHLCV (YFinance-style ``Date`` + OHLCV columns, or legacy ``Price`` header).
  4) Run this script → wide CSV + join ``.meta.json`` (counts + optional Pearson).

Join key: string ``YYYY-MM-DD`` equal to panel column ``--panel-date-col`` (default
``session_local_date``). Weather/OHLCV date cells are normalized to the same ``YYYY-MM-DD``
prefix when possible.

Does not call external HTTP. Not a live trading trigger. [HYPO] / B-track only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _norm_date_key(cell: str) -> str | None:
    s = str(cell).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        head = s[:10]
        if head[0].isdigit():
            return head
    return None


def _find_header(headers: list[str], want: str) -> str | None:
    w = want.strip().lower()
    for h in headers:
        if h.strip().lower() == w:
            return h
    return None


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return [], []
    r = csv.DictReader(lines)
    h = r.fieldnames or []
    rows = []
    for row in r:
        rows.append({k: (v if v is not None else "") for k, v in row.items()})
    return list(h), rows


def _load_side_by_date(
    path: Path,
    date_col_arg: str,
    prefix: str,
) -> tuple[dict[str, dict[str, str]], list[str], str, list[str]]:
    """Return (by_date, value_fieldnames_prefixed, resolved_date_header, warnings)."""
    headers, rows = _read_csv_rows(path)
    if not headers:
        return {}, [], "", ["empty_csv"]
    resolved = _find_header(headers, date_col_arg)
    if not resolved:
        return {}, [], "", [f"date_col_not_found:{date_col_arg}"]
    warns: list[str] = []
    by_date: dict[str, dict[str, str]] = {}
    val_cols_orig = [h for h in headers if h != resolved]
    val_cols_out = [f"{prefix}{h}" for h in val_cols_orig]
    for row in rows:
        dk = _norm_date_key(row.get(resolved, ""))
        if not dk:
            continue
        out: dict[str, str] = {}
        for ho, hp in zip(val_cols_orig, val_cols_out):
            out[hp] = str(row.get(ho, "") or "")
        if dk in by_date:
            warns.append(f"duplicate_side_date:{dk}")
        by_date[dk] = out
    return by_date, val_cols_out, resolved, warns


def _pearson(xs: list[float], ys: list[float]) -> tuple[float | None, int]:
    n = len(xs)
    if n < 3 or n != len(ys):
        return None, n
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0.0 or deny == 0.0:
        return None, n
    return num / (denx * deny), n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, required=True, help="Output of build_btrack_session_instant_myeongni_panel_v1.py")
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta-json", type=Path, default=None)
    ap.add_argument("--panel-date-col", type=str, default="session_local_date")
    ap.add_argument("--weather-csv", type=Path, default=None)
    ap.add_argument("--weather-date-col", type=str, default="date")
    ap.add_argument("--weather-prefix", type=str, default="wthr_")
    ap.add_argument("--ohlcv-csv", type=Path, default=None)
    ap.add_argument("--ohlcv-date-col", type=str, default="Date")
    ap.add_argument("--ohlcv-prefix", type=str, default="ohlcv_")
    ap.add_argument(
        "--pearson-x",
        type=str,
        default=None,
        metavar="COL",
        help="Merged CSV column name for Pearson r (requires --pearson-y; min 3 finite pairs).",
    )
    ap.add_argument("--pearson-y", type=str, default=None, metavar="COL")
    ap.add_argument("--utf8-bom", action="store_true")
    args = ap.parse_args()

    if not args.panel_csv.is_file():
        print(f"missing panel csv: {args.panel_csv}", file=sys.stderr)
        return 2
    if (args.pearson_x or args.pearson_y) and (not args.pearson_x or not args.pearson_y):
        print("both --pearson-x and --pearson-y are required together", file=sys.stderr)
        return 2

    ph, panel_rows = _read_csv_rows(args.panel_csv)
    if not ph or not panel_rows:
        print("panel csv empty", file=sys.stderr)
        return 2
    p_date_h = _find_header(ph, args.panel_date_col)
    if not p_date_h:
        print(f"panel date column not found: {args.panel_date_col}", file=sys.stderr)
        return 2

    w_by: dict[str, dict[str, str]] = {}
    w_cols: list[str] = []
    w_warns: list[str] = []
    if args.weather_csv:
        if not args.weather_csv.is_file():
            print(f"missing weather csv: {args.weather_csv}", file=sys.stderr)
            return 2
        w_by, w_cols, _, w_warns = _load_side_by_date(args.weather_csv, args.weather_date_col, args.weather_prefix)

    o_by: dict[str, dict[str, str]] = {}
    o_cols: list[str] = []
    o_warns: list[str] = []
    if args.ohlcv_csv:
        if not args.ohlcv_csv.is_file():
            print(f"missing ohlcv csv: {args.ohlcv_csv}", file=sys.stderr)
            return 2
        o_by, o_cols, _, o_warns = _load_side_by_date(args.ohlcv_csv, args.ohlcv_date_col, args.ohlcv_prefix)

    out_fieldnames = list(ph) + [c for c in w_cols if c not in ph] + [c for c in o_cols if c not in ph]

    n_weather_hit = 0
    n_ohlcv_hit = 0
    merged: list[dict[str, str]] = []
    for row in panel_rows:
        dk = _norm_date_key(row.get(p_date_h, ""))
        out = {k: str(row.get(k, "") or "") for k in ph}
        if dk and dk in w_by:
            n_weather_hit += 1
            out.update(w_by[dk])
        else:
            for c in w_cols:
                out[c] = ""
        if dk and dk in o_by:
            n_ohlcv_hit += 1
            out.update(o_by[dk])
        else:
            for c in o_cols:
                out[c] = ""
        merged.append({k: out.get(k, "") for k in out_fieldnames})

    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding=encoding) as fp:
        w = csv.DictWriter(fp, fieldnames=out_fieldnames)
        w.writeheader()
        for r in merged:
            w.writerow(r)

    pearson: dict[str, Any] | None = None
    if args.pearson_x and args.pearson_y:
        xs: list[float] = []
        ys: list[float] = []
        for r in merged:
            try:
                xv = float(str(r.get(args.pearson_x, "")).strip())
                yv = float(str(r.get(args.pearson_y, "")).strip())
            except ValueError:
                continue
            if math.isfinite(xv) and math.isfinite(yv):
                xs.append(xv)
                ys.append(yv)
        r_val, n_p = _pearson(xs, ys)
        pearson = {
            "x": args.pearson_x,
            "y": args.pearson_y,
            "n_pairs": n_p,
            "pearson_r": None if r_val is None else round(r_val, 8),
        }

    meta = {
        "schema": "btrack_session_panel_weather_ohlcv_join_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "join_key": {
            "panel_date_column": p_date_h,
            "normalized_key": "YYYY-MM-DD prefix of panel date cell",
            "weather_date_column": args.weather_date_col if args.weather_csv else None,
            "ohlcv_date_column": args.ohlcv_date_col if args.ohlcv_csv else None,
            "note_ko": (
                "날씨 CSV는 패널의 session_local_date와 동일한 '로컬 영업일 달력' 의미로 맞춘 "
                "행을 지휘관이 준비해야 한다. 실시간 기상 API를 이 스크립트가 호출하지 않는다."
            ),
        },
        "inputs": {
            "panel_csv": str(args.panel_csv.resolve()),
            "weather_csv": str(args.weather_csv.resolve()) if args.weather_csv else None,
            "ohlcv_csv": str(args.ohlcv_csv.resolve()) if args.ohlcv_csv else None,
        },
        "counts": {
            "n_panel_rows": len(merged),
            "n_rows_with_any_weather_cell_nonblank": n_weather_hit,
            "n_rows_with_any_ohlcv_cell_nonblank": n_ohlcv_hit,
        },
        "warnings": w_warns + o_warns,
        "pearson": pearson,
        "out_csv": str(args.out_csv.resolve()),
    }
    meta_path = args.out_meta_json or args.out_csv.with_suffix(".join.meta.json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE rows={len(merged)} csv={args.out_csv.resolve()} meta={meta_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
