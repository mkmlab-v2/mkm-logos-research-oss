#!/usr/bin/env python3
"""Build a score JSON (predicted vs actual direction) for eval_prophecy_hit_rate_v1 --run-mode price.

Reads B-Track hypothesis JSON and OHLCV CSVs (YFinance-style; same loader as logos KOSPI shadow).
KOSPI SSOT path: research/market_data/kospi_daily_external_yf.csv
BTC: pass --btc-csv when hypothesis instrument is btc or multi (optional file).

Does not fetch live APIs. B-Track / [HYPO] only — not a live trading trigger.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

DEFAULT_HYPOTHESIS = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"

SCHEMA = "btrack_prophecy_score_v1"


def _rel_to_root(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_hypothesis(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _predicted_direction(h: dict[str, Any]) -> str | None:
    pred = h.get("prediction") or {}
    d = str(pred.get("direction") or "").strip().lower()
    if d in ("bull", "bear", "neutral"):
        return d
    if d == "abstain":
        return None
    return None


def _instrument(h: dict[str, Any]) -> str:
    pred = h.get("prediction") or {}
    return str(pred.get("instrument") or "multi").strip().lower()


def _daily_return(prev_row: dict[str, Any], cur_row: dict[str, Any]) -> float:
    pc = float(prev_row["close"])
    cc = float(cur_row["close"])
    if pc == 0:
        return 0.0
    return (cc - pc) / pc


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _row_pair_for_eval_date(rows: list[dict[str, Any]], eval_date: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    by_date = {r["date"]: r for r in rows}
    if eval_date not in by_date:
        return None
    dates = sorted(by_date.keys())
    idx = dates.index(eval_date)
    if idx == 0:
        return None
    prev_d = dates[idx - 1]
    return by_date[prev_d], by_date[eval_date]


def _default_eval_date(rows: list[dict[str, Any]]) -> str | None:
    """Latest complete bar date: last row with date strictly before UTC today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    past = [r["date"] for r in rows if r["date"] < today]
    if not past:
        return None
    return max(past)


def _past_sorted_unique_dates(rows: list[dict[str, Any]]) -> list[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return sorted({r["date"] for r in rows if r["date"] < today})


def _last_n_trading_dates(rows: list[dict[str, Any]], n: int) -> list[str]:
    if n < 1:
        return []
    past = _past_sorted_unique_dates(rows)
    if not past:
        return []
    return past[-n:] if len(past) >= n else past


def _build_rows(
    *,
    hypothesis: dict[str, Any],
    eval_date: str,
    neutral_bps: float,
    kospi_rows: list[dict[str, Any]],
    btc_rows: list[dict[str, Any]] | None,
    inst: str,
    predicted: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {"warnings": []}
    rows_out: list[dict[str, Any]] = []
    if predicted is None:
        meta["warnings"].append("hypothesis prediction.direction missing or abstain; no score rows.")
        return [], meta

    def one_leg(label: str, ohlc: list[dict[str, Any]]) -> None:
        pair = _row_pair_for_eval_date(ohlc, eval_date)
        if pair is None:
            meta["warnings"].append(f"{label}: no prev/cur row for eval_date={eval_date}")
            return
        prev_r, cur_r = pair
        ret = _daily_return(prev_r, cur_r)
        act = _actual_direction(ret, neutral_bps)
        rows_out.append(
            {
                "instrument": label,
                "eval_date": eval_date,
                "predicted_direction": predicted,
                "actual_direction": act,
                "daily_return": round(ret, 8),
                "prev_close": float(prev_r["close"]),
                "close": float(cur_r["close"]),
                "neutral_bps": neutral_bps,
            }
        )

    if inst == "kospi":
        one_leg("kospi", kospi_rows)
    elif inst == "btc":
        if not btc_rows:
            meta["warnings"].append("btc instrument but no --btc-csv or empty file.")
        else:
            one_leg("btc", btc_rows)
    elif inst == "multi":
        one_leg("kospi", kospi_rows)
        if btc_rows:
            one_leg("btc", btc_rows)
        else:
            meta["warnings"].append("instrument multi: btc leg skipped (no btc csv).")
    elif inst == "none":
        meta["warnings"].append("instrument none: no OHLCV leg (observation-only).")
    else:
        meta["warnings"].append(f"unknown instrument {inst!r}; no rows.")

    return rows_out, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Build btrack_prophecy_score JSON from hypothesis + OHLCV.")
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=None, help="Optional YFinance-style daily CSV for BTC.")
    ap.add_argument(
        "--eval-date",
        type=str,
        default="auto",
        help='Trading date YYYY-MM-DD for the bar used vs previous close, or "auto" (latest date before UTC today).',
    )
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=1,
        metavar="N",
        help="If N>1, emit one score row per leg per eval date for the last N past trading days "
        "(same hypothesis predicted_direction vs rolling actuals; see meta.frozen_prediction_note).",
    )
    ap.add_argument("--neutral-bps", type=float, default=5.0, help="Abs return below this (in bps) => neutral.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    hyp = _load_hypothesis(args.hypothesis_json)
    if not hyp:
        print(f"Missing or invalid hypothesis JSON: {args.hypothesis_json}", file=sys.stderr)
        return 2

    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 2

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    btc_rows = load_kospi_yf_rows(args.btc_csv) if args.btc_csv and args.btc_csv.is_file() else None

    inst = _instrument(hyp)
    predicted = _predicted_direction(hyp)

    n_batch = max(1, int(args.recent_trading_days))
    if n_batch > 1:
        dates_to_use = _last_n_trading_dates(kospi_rows, n_batch)
        if not dates_to_use:
            print("Could not resolve trading dates for --recent-trading-days (empty CSV or no past dates).", file=sys.stderr)
            return 2
        rows_out: list[dict[str, Any]] = []
        wmeta: dict[str, Any] = {"warnings": []}
        for ed in dates_to_use:
            chunk, wm = _build_rows(
                hypothesis=hyp,
                eval_date=ed,
                neutral_bps=float(args.neutral_bps),
                kospi_rows=kospi_rows,
                btc_rows=btc_rows,
                inst=inst,
                predicted=predicted,
            )
            rows_out.extend(chunk)
            wmeta["warnings"].extend(wm.get("warnings", []))
        eval_date = dates_to_use[-1]
        wmeta["batch_eval_dates"] = dates_to_use
        wmeta["frozen_prediction_note"] = (
            "Same hypothesis predicted_direction applied to each eval_date vs that day's realized return "
            f"({len(dates_to_use)} trading days)."
        )
    else:
        eval_date = args.eval_date.strip()
        if eval_date == "auto":
            eval_date = _default_eval_date(kospi_rows) or ""
        if not eval_date:
            print("Could not resolve eval-date (empty CSV or no past dates).", file=sys.stderr)
            return 2
        rows_out, wmeta = _build_rows(
            hypothesis=hyp,
            eval_date=eval_date,
            neutral_bps=float(args.neutral_bps),
            kospi_rows=kospi_rows,
            btc_rows=btc_rows,
            inst=inst,
            predicted=predicted,
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "eval_date": eval_date,
        "neutral_bps": float(args.neutral_bps),
        "hypothesis_path": _rel_to_root(args.hypothesis_json),
        "hypothesis_ts_utc": hyp.get("ts_utc"),
        "inputs": {
            "kospi_csv": _rel_to_root(args.kospi_csv),
            "btc_csv": str(args.btc_csv) if args.btc_csv else None,
            "recent_trading_days": n_batch,
        },
        "meta": wmeta,
        "rows": rows_out,
    }

    # Top-level aliases for single-row eval_prophecy_hit_rate convenience
    if len(rows_out) == 1:
        r0 = rows_out[0]
        payload["predicted_direction"] = r0.get("predicted_direction")
        payload["actual_direction"] = r0.get("actual_direction")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
