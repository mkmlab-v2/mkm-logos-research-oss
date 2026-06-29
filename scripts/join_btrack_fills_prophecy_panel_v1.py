#!/usr/bin/env python3
"""[HYPO] Shadow join: daily fills feature cache × per-date prophecy panel (UTC date key).

Left spine options: ``union`` (default, shadow coverage), ``fills``, or ``prophecy``.
Does not alter trading gates, Track A ACTIVE, or live execution. research_only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILLS = ROOT / "reports/btrack_fills_daily_feature_cache_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports/per_date_v1_180d.json"
DEFAULT_EVAL_LANE = ROOT / "reports/btrack_fills_execution_eval_lane_v1_latest.json"
DEFAULT_OUT_CSV = ROOT / "reports/btrack_fills_prophecy_join_wide_v1_latest.csv"
DEFAULT_OUT_OVERLAP_CSV = ROOT / "reports/btrack_fills_prophecy_join_overlap_v1_latest.csv"
DEFAULT_OUT_META = ROOT / "reports/btrack_fills_prophecy_join_wide_v1_latest.meta.json"

FILL_COLS = (
    "fill_count",
    "buy_fill_count",
    "sell_fill_count",
    "buy_sell_imbalance",
    "maker_ratio",
    "quote_qty_sum",
    "realized_pnl_sum",
    "commission_sum",
    "price_mean",
    "price_dispersion",
)

PRP_COLS = (
    "predicted_direction",
    "confidence",
    "weighted_score",
    "preliminary_direction",
    "instrument",
    "ensemble_mode",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _norm_date(cell: str) -> str | None:
    s = str(cell).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        head = s[:10]
        if head[0].isdigit():
            return head
    return None


def _load_fills_daily(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path)
    daily = payload.get("daily_by_utc_date")
    if not isinstance(daily, dict):
        return {}, payload
    out: dict[str, dict[str, Any]] = {}
    for k, v in daily.items():
        dk = _norm_date(k)
        if dk and isinstance(v, dict):
            out[dk] = v
    return out, payload


def _load_prophecy_by_date(
    path: Path,
    *,
    instrument: str | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    want = (instrument or "").strip().lower() or None
    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        ed = _norm_date(str(r.get("eval_date") or ""))
        if not ed:
            continue
        inst = str(r.get("instrument") or "").strip().lower()
        if want and inst and inst != want:
            continue
        if ed in by_date and want is None and inst:
            existing_inst = str(by_date[ed].get("instrument") or "").lower()
            if existing_inst == "btc" and inst != "btc":
                continue
        by_date[ed] = r
    return by_date, payload


def _spine_dates(
    fills: dict[str, dict[str, Any]],
    prophecy: dict[str, dict[str, Any]],
    mode: str,
) -> list[str]:
    fill_keys = set(fills)
    prp_keys = set(prophecy)
    if mode == "fills":
        keys = fill_keys
    elif mode == "prophecy":
        keys = prp_keys
    else:
        keys = fill_keys | prp_keys
    return sorted(keys)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fills-cache", type=Path, default=DEFAULT_FILLS)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--eval-lane-json", type=Path, default=DEFAULT_EVAL_LANE)
    ap.add_argument(
        "--instrument",
        type=str,
        default="btc",
        help="Filter prophecy rows by instrument (default btc). Empty = no filter.",
    )
    ap.add_argument(
        "--spine",
        choices=("union", "fills", "prophecy"),
        default="union",
        help="Date spine: union (shadow coverage), fills-only, or prophecy-only.",
    )
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    ap.add_argument(
        "--out-overlap-csv",
        type=Path,
        default=DEFAULT_OUT_OVERLAP_CSV,
        help="Rows with both fills and prophecy (shadow correlate spine).",
    )
    ap.add_argument("--out-meta-json", type=Path, default=DEFAULT_OUT_META)
    ap.add_argument("--utf8-bom", action="store_true")
    args = ap.parse_args()

    if not args.fills_cache.is_file():
        print(f"missing fills cache: {args.fills_cache}", file=sys.stderr)
        return 1
    if not args.per_date_json.is_file():
        print(f"missing per-date prophecy json: {args.per_date_json}", file=sys.stderr)
        return 1

    fills, fills_payload = _load_fills_daily(args.fills_cache)
    inst_filter = args.instrument.strip() or None
    prophecy, prp_payload = _load_prophecy_by_date(args.per_date_json, instrument=inst_filter)

    dates = _spine_dates(fills, prophecy, args.spine)
    fieldnames = (
        ["utc_date", "has_fills", "has_prophecy"]
        + [f"fill_{c}" for c in FILL_COLS]
        + [f"prp_{c}" for c in PRP_COLS]
    )

    merged: list[dict[str, str]] = []
    n_both = 0
    n_fills_only = 0
    n_prp_only = 0
    for d in dates:
        fr = fills.get(d)
        pr = prophecy.get(d)
        has_f = fr is not None
        has_p = pr is not None
        if has_f and has_p:
            n_both += 1
        elif has_f:
            n_fills_only += 1
        elif has_p:
            n_prp_only += 1

        row: dict[str, str] = {
            "utc_date": d,
            "has_fills": "1" if has_f else "0",
            "has_prophecy": "1" if has_p else "0",
        }
        for c in FILL_COLS:
            val = fr.get(c) if fr else ""
            row[f"fill_{c}"] = "" if val is None else str(val)
        for c in PRP_COLS:
            val = pr.get(c) if pr else ""
            row[f"prp_{c}"] = "" if val is None else str(val)
        merged.append(row)

    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    def _write_csv(path: Path, rows_out: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding=encoding) as fp:
            w = csv.DictWriter(fp, fieldnames=fieldnames)
            w.writeheader()
            for r in rows_out:
                w.writerow(r)

    _write_csv(args.out_csv, merged)
    overlap_rows = [r for r in merged if r["has_fills"] == "1" and r["has_prophecy"] == "1"]
    if args.out_overlap_csv:
        _write_csv(args.out_overlap_csv, overlap_rows)

    eval_lane: dict[str, Any] = {}
    if args.eval_lane_json.is_file():
        try:
            eval_lane = _load_json(args.eval_lane_json)
        except Exception:
            eval_lane = {}

    fill_dates = sorted(fills)
    prp_dates = sorted(prophecy)
    overlap_min = max(fill_dates[0], prp_dates[0]) if fill_dates and prp_dates else None
    overlap_max = min(fill_dates[-1], prp_dates[-1]) if fill_dates and prp_dates else None

    meta: dict[str, Any] = {
        "schema": "btrack_fills_prophecy_join_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_active_write": False,
        "join_key": {
            "utc_date": "YYYY-MM-DD",
            "spine": args.spine,
            "instrument_filter": inst_filter,
        },
        "inputs": {
            "fills_cache": _rel(args.fills_cache),
            "per_date_json": _rel(args.per_date_json),
            "eval_lane_json": _rel(args.eval_lane_json) if args.eval_lane_json.is_file() else None,
        },
        "counts": {
            "n_rows": len(merged),
            "n_fills_days": len(fills),
            "n_prophecy_days": len(prophecy),
            "n_overlap_days": n_both,
            "n_fills_only_days": n_fills_only,
            "n_prophecy_only_days": n_prp_only,
        },
        "ranges": {
            "fills_date_min": fill_dates[0] if fill_dates else None,
            "fills_date_max": fill_dates[-1] if fill_dates else None,
            "prophecy_date_min": prp_dates[0] if prp_dates else None,
            "prophecy_date_max": prp_dates[-1] if prp_dates else None,
            "overlap_date_min": overlap_min,
            "overlap_date_max": overlap_max,
        },
        "headline_ko": (
            f"실체결 일별 {len(fills)}일 · 예언 패널 {len(prophecy)}일 · "
            f"겹침 {n_both}일 · spine={args.spine}. "
            "OHLCV 백테스트가 아닌 실체결 코퍼스 조인; n·기간·갭 병기 필수."
        ),
        "gap_flags": eval_lane.get("gap_flags") if isinstance(eval_lane.get("gap_flags"), dict) else {},
        "corpus": eval_lane.get("corpus") if isinstance(eval_lane.get("corpus"), dict) else {},
        "fills_cache_stats": fills_payload.get("stats"),
        "per_date_schema": prp_payload.get("schema"),
        "out_csv": _rel(args.out_csv),
        "out_overlap_csv": _rel(args.out_overlap_csv) if args.out_overlap_csv else None,
        "warnings": [],
    }
    if not n_both:
        meta["warnings"].append("zero_overlap_days: fills and prophecy calendars do not intersect on spine")

    args.out_meta_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote_csv": _rel(args.out_csv),
                "wrote_overlap_csv": _rel(args.out_overlap_csv) if args.out_overlap_csv else None,
                "wrote_meta": _rel(args.out_meta_json),
                "n_rows": len(merged),
                "n_overlap_days": n_both,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
