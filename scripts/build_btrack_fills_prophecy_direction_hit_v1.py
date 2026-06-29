#!/usr/bin/env python3
"""[HYPO] Direction hit-rate on fills×prophecy overlap days (OHLCV actual + PnL sign leg).

Reads overlap CSV from join_btrack_fills_prophecy_panel_v1.py. Does not touch live trading or Track A.
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
DEFAULT_OVERLAP = ROOT / "reports/btrack_fills_prophecy_join_overlap_v1_latest.csv"
DEFAULT_JOIN_META = ROOT / "reports/btrack_fills_prophecy_join_wide_v1_latest.meta.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_fills_prophecy_direction_hit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _norm_date(cell: str) -> str | None:
    s = str(cell).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        head = s[:10]
        if head[0].isdigit():
            return head
    return None


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _pnl_direction(pnl: float, *, neutral_usd: float) -> str:
    if pnl > neutral_usd:
        return "bull"
    if pnl < -neutral_usd:
        return "bear"
    return "neutral"


def _row_pair_for_eval_date(rows: list[dict[str, Any]], eval_date: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    by_date = {str(r["date"])[:10]: r for r in rows}
    if eval_date not in by_date:
        return None
    dates = sorted(by_date.keys())
    idx = dates.index(eval_date)
    if idx == 0:
        return None
    prev_d = dates[idx - 1]
    return by_date[prev_d], by_date[eval_date]


def _daily_return(prev_row: dict[str, Any], cur_row: dict[str, Any]) -> float:
    pc = float(prev_row["close"])
    cc = float(cur_row["close"])
    if pc == 0:
        return 0.0
    return (cc - pc) / pc


def _read_overlap_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return [{k: (v if v is not None else "") for k, v in row.items()} for row in reader]


def _hit_metrics(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """pairs: (predicted, actual) excluding empty."""
    hits = 0
    n = 0
    n_pred_neutral = 0
    n_act_neutral = 0
    for pd, ad in pairs:
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        if pd == "neutral":
            n_pred_neutral += 1
        if ad == "neutral":
            n_act_neutral += 1
        if pd == "neutral" or ad == "neutral":
            continue
        n += 1
        if pd == ad:
            hits += 1
    rate = round(hits / n, 6) if n else None
    return {
        "directional_hit_rate": rate,
        "n_evaluated": n,
        "n_hits": hits,
        "n_pred_neutral_excluded": n_pred_neutral,
        "n_actual_neutral_excluded": n_act_neutral,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--overlap-csv", type=Path, default=DEFAULT_OVERLAP)
    ap.add_argument("--join-meta-json", type=Path, default=DEFAULT_JOIN_META)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--neutral-bps", type=float, default=2.0, help="OHLCV actual direction band (recommended chain default).")
    ap.add_argument("--pnl-neutral-usd", type=float, default=0.01, help="|realized_pnl| below this → neutral.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.overlap_csv.is_file():
        print(f"missing overlap csv: {args.overlap_csv}", file=sys.stderr)
        return 1
    if not args.btc_csv.is_file():
        print(f"missing btc ohlcv: {args.btc_csv}", file=sys.stderr)
        return 1

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    ohlcv = load_kospi_yf_rows(args.btc_csv)
    overlap_rows = _read_overlap_csv(args.overlap_csv)

    join_meta: dict[str, Any] = {}
    if args.join_meta_json.is_file():
        try:
            join_meta = json.loads(args.join_meta_json.read_text(encoding="utf-8-sig"))
        except Exception:
            join_meta = {}

    detail_rows: list[dict[str, Any]] = []
    ohlcv_pairs: list[tuple[str, str]] = []
    pnl_pairs: list[tuple[str, str]] = []
    warnings: list[str] = []

    for row in overlap_rows:
        if row.get("has_fills") != "1" or row.get("has_prophecy") != "1":
            continue
        utc_date = _norm_date(row.get("utc_date", ""))
        if not utc_date:
            continue
        pred = str(row.get("prp_predicted_direction") or "").strip().lower()
        if not pred:
            warnings.append(f"missing_predicted_direction:{utc_date}")
            continue

        ohlcv_actual: str | None = None
        ohlcv_ret: float | None = None
        pair = _row_pair_for_eval_date(ohlcv, utc_date)
        if pair is None:
            warnings.append(f"ohlcv_pair_missing:{utc_date}")
        else:
            prev_r, cur_r = pair
            ohlcv_ret = _daily_return(prev_r, cur_r)
            ohlcv_actual = _actual_direction(ohlcv_ret, args.neutral_bps)
            ohlcv_pairs.append((pred, ohlcv_actual))

        pnl_actual: str | None = None
        pnl_val: float | None = None
        try:
            pnl_val = float(str(row.get("fill_realized_pnl_sum") or "").strip())
            pnl_actual = _pnl_direction(pnl_val, neutral_usd=float(args.pnl_neutral_usd))
            pnl_pairs.append((pred, pnl_actual))
        except ValueError:
            warnings.append(f"pnl_parse_failed:{utc_date}")

        detail_rows.append(
            {
                "utc_date": utc_date,
                "predicted_direction": pred,
                "ohlcv_actual_direction": ohlcv_actual,
                "ohlcv_daily_return": None if ohlcv_ret is None else round(ohlcv_ret, 8),
                "pnl_actual_direction": pnl_actual,
                "fill_realized_pnl_sum": pnl_val,
                "fill_commission_sum": row.get("fill_commission_sum"),
                "prp_confidence": row.get("prp_confidence"),
                "prp_weighted_score": row.get("prp_weighted_score"),
                "ohlcv_hit": (
                    pred == ohlcv_actual
                    if ohlcv_actual and pred in ("bull", "bear") and ohlcv_actual in ("bull", "bear")
                    else None
                ),
                "pnl_hit": (
                    pred == pnl_actual
                    if pnl_actual and pred in ("bull", "bear") and pnl_actual in ("bull", "bear")
                    else None
                ),
            }
        )

    ohlcv_metrics = _hit_metrics(ohlcv_pairs)
    pnl_metrics = _hit_metrics(pnl_pairs)
    counts = join_meta.get("counts") if isinstance(join_meta.get("counts"), dict) else {}

    out: dict[str, Any] = {
        "schema": "btrack_fills_prophecy_direction_hit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_active_write": False,
        "inputs": {
            "overlap_csv": _rel(args.overlap_csv),
            "join_meta_json": _rel(args.join_meta_json) if args.join_meta_json.is_file() else None,
            "btc_csv": _rel(args.btc_csv),
            "neutral_bps": float(args.neutral_bps),
            "pnl_neutral_usd": float(args.pnl_neutral_usd),
        },
        "corpus_headline_ko": join_meta.get("headline_ko"),
        "overlap_counts": {
            "n_overlap_days_join_meta": counts.get("n_overlap_days"),
            "n_rows_scored": len(detail_rows),
        },
        "ohlcv_leg": {
            **ohlcv_metrics,
            "note_ko": "예언 패널 eval_date 기준 전일→당일 종가 수익률; neutral_bps 밴드는 build_btrack_prophecy_score_from_ohlcv와 동일 규칙.",
        },
        "pnl_leg": {
            **pnl_metrics,
            "note_ko": "당일 실현손익 부호 대 예언 방향; 체결·포지션 혼합 코퍼스라 OHLCV 적중과 병기만.",
        },
        "delta": {
            "pnl_hit_rate_minus_ohlcv_hit_rate": (
                round((pnl_metrics["directional_hit_rate"] or 0) - (ohlcv_metrics["directional_hit_rate"] or 0), 6)
                if pnl_metrics["directional_hit_rate"] is not None
                and ohlcv_metrics["directional_hit_rate"] is not None
                else None
            ),
        },
        "rows": detail_rows,
        "warnings": warnings,
        "disclaimer_ko": (
            "n·기간·갭은 join meta와 함께 병기. 인과·실매매 승격 근거 아님. "
            "LOCKED_MODE·Track A 합선 없음."
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": _rel(args.out_json),
                "ohlcv_hit_rate": ohlcv_metrics.get("directional_hit_rate"),
                "pnl_hit_rate": pnl_metrics.get("directional_hit_rate"),
                "n_scored": len(detail_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
