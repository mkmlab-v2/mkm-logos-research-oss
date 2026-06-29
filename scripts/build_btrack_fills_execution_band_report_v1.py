#!/usr/bin/env python3
"""[HYPO] Fills-only execution band summary (days with fills but no prophecy panel row).

MS copy evidence — real fills corpus, not OHLCV backtest. research_only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIDE = ROOT / "reports/btrack_fills_prophecy_join_wide_v1_latest.csv"
DEFAULT_META = ROOT / "reports/btrack_fills_prophecy_join_wide_v1_latest.meta.json"
DEFAULT_EVAL = ROOT / "reports/btrack_fills_execution_eval_lane_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_fills_execution_band_fills_only_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _f(cell: str) -> float | None:
    s = str(cell).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-csv", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--join-meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--eval-lane-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.wide_csv.is_file():
        print(f"missing wide csv: {args.wide_csv}", file=sys.stderr)
        return 1

    fills_only: list[dict[str, Any]] = []
    with args.wide_csv.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("has_fills") != "1" or row.get("has_prophecy") == "1":
                continue
            fills_only.append(
                {
                    "utc_date": row.get("utc_date"),
                    "fill_count": _f(row.get("fill_fill_count", "")),
                    "realized_pnl_sum": _f(row.get("fill_realized_pnl_sum", "")),
                    "quote_qty_sum": _f(row.get("fill_quote_qty_sum", "")),
                    "commission_sum": _f(row.get("fill_commission_sum", "")),
                }
            )

    fills_only.sort(key=lambda r: str(r.get("utc_date") or ""))
    pnl_vals = [r["realized_pnl_sum"] for r in fills_only if r.get("realized_pnl_sum") is not None]
    fill_counts = [r["fill_count"] for r in fills_only if r.get("fill_count") is not None]

    meta = {}
    if args.join_meta_json.is_file():
        try:
            meta = json.loads(args.join_meta_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            meta = {}

    eval_lane = {}
    if args.eval_lane_json.is_file():
        try:
            eval_lane = json.loads(args.eval_lane_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            eval_lane = {}

    date_min = fills_only[0]["utc_date"] if fills_only else None
    date_max = fills_only[-1]["utc_date"] if fills_only else None

    doc: dict[str, Any] = {
        "schema": "btrack_fills_execution_band_fills_only_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "band": "fills_only_no_prophecy_panel",
        "counts": {
            "n_fills_only_days": len(fills_only),
            "n_fills_days_total": (meta.get("counts") or {}).get("n_fills_days"),
            "n_overlap_days": (meta.get("counts") or {}).get("n_overlap_days"),
        },
        "ranges": {
            "fills_only_date_min": date_min,
            "fills_only_date_max": date_max,
            "fills_corpus_min": (eval_lane.get("corpus") or {}).get("date_min"),
            "fills_corpus_max": (eval_lane.get("corpus") or {}).get("date_max"),
        },
        "aggregates_fills_only_band": {
            "realized_pnl_sum": round(sum(pnl_vals), 8) if pnl_vals else None,
            "avg_realized_pnl_per_day": round(sum(pnl_vals) / len(pnl_vals), 8) if pnl_vals else None,
            "avg_fill_count_per_day": round(sum(fill_counts) / len(fill_counts), 4) if fill_counts else None,
            "positive_pnl_days": sum(1 for v in pnl_vals if v > 0),
            "negative_pnl_days": sum(1 for v in pnl_vals if v < 0),
        },
        "days": fills_only,
        "headline_ko": (
            f"실체결 전용 밴드 {len(fills_only)}일 "
            f"({date_min}~{date_max}) — 예언 패널 없음; OHLCV 백테스트 아님."
        ),
        "ms_copy_one_liner_ko": (
            f"BTCUSDT 실체결 일별 {len(fills_only)}일(예언 미겹침) · "
            f"PnL합 {round(sum(pnl_vals), 2) if pnl_vals else 'n/a'} USDT · research_only"
        ),
        "evidence": {
            "wide_csv": _rel(args.wide_csv),
            "join_meta": _rel(args.join_meta_json) if args.join_meta_json.is_file() else None,
            "eval_lane": _rel(args.eval_lane_json) if args.eval_lane_json.is_file() else None,
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
