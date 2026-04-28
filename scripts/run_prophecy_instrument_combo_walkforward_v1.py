# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.86, K:0.44, M:0.32}
# Balance: 91
# Purpose: Blocked walk-forward for instrument-combo (KOSPI mode + BTC thresholds)
# Keywords: prophecy, walkforward, instrument, combo, btc
#!/usr/bin/env python3
"""Walk-forward for the instrument-combo family (same policy as ``run_prophecy_instrument_combo_sweep_v1``).

Each fold fits ``(kospi_mode, btc_low_thr, btc_high_thr)`` on the train date block only,
then scores the test block. Requires a **dual-leg** score panel (KOSPI + BTC rows per eval_date)
and a readable BTC daily CSV for prior returns.

Output aggregate keys match ``prophecy_per_date_combo_walkforward_v1`` so promotion gates can reuse them.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_walkforward_v1_latest.json"
SCHEMA = "prophecy_instrument_combo_walkforward_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _prior_map(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _pred_from_prior(pr: float | None, *, low: float, high: float, fallback: str) -> str:
    if pr is None:
        return fallback
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _metrics(rows: list[dict[str, Any]], preds: list[str]) -> dict[str, Any]:
    n = 0
    h = 0
    for r, p in zip(rows, preds):
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            h += 1
    return {"price_directional_hit_rate": round(h / n, 6) if n else None, "n_evaluated": n, "price_hits": h}


def _acc(rows: list[dict[str, Any]], preds: list[str]) -> tuple[float, int]:
    m = _metrics(rows, preds)
    rate = float(m["price_directional_hit_rate"] or 0.0)
    return rate, int(m.get("price_hits") or 0)


def _instrument_preds(
    rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    kospi_mode: str,
    b_lo: float,
    b_hi: float,
) -> list[str]:
    preds: list[str] = []
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        old = str(r.get("predicted_direction") or "").strip().lower()
        if inst == "kospi":
            if kospi_mode == "causal":
                p = _pred_from_prior(km.get(ed), low=-0.06, high=-0.05, fallback=old if old in VALID else "neutral")
            else:
                p = kospi_mode
        else:
            p = _pred_from_prior(bm.get(ed), low=b_lo, high=b_hi, fallback=old if old in VALID else "neutral")
        preds.append(p)
    return preds


def _threshold_pairs(grid: list[float]) -> list[tuple[float, float]]:
    return [(lo, hi) for lo, hi in itertools.product(grid, grid) if lo < hi]


def _best_combo_on_train(
    train_rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    kospi_modes: list[str],
    pairs: list[tuple[float, float]],
) -> tuple[str, float, float] | None:
    best_acc = -1.0
    best_combo: tuple[str, float, float] | None = None
    for k_mode, (b_lo, b_hi) in itertools.product(kospi_modes, pairs):
        preds = _instrument_preds(train_rows, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        a, _ = _acc(train_rows, preds)
        if a > best_acc:
            best_acc = a
            best_combo = (k_mode, b_lo, b_hi)
    return best_combo


def _blocked_walkforward_folds(dates_sorted: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates_sorted)
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates_sorted[idx : idx + sz])
        idx += sz
    folds: list[tuple[list[str], list[str]]] = []
    for f in range(1, n_folds):
        train: list[str] = []
        for b in range(f):
            train.extend(blocks[b])
        test = blocks[f]
        if train and test:
            folds.append((train, test))
    return folds


def _dual_leg_dates(rows: list[dict[str, Any]]) -> tuple[list[str], int]:
    by_date: dict[str, set[str]] = {}
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "").strip().lower()
        act = str(r.get("actual_direction") or "").strip().lower()
        if not ed or inst not in ("kospi", "btc") or act not in VALID:
            continue
        by_date.setdefault(ed, set()).add(inst)
    all_dates = sorted(by_date.keys())
    dual_dates = [d for d in all_dates if by_date[d] >= {"kospi", "btc"}]
    return dual_dates, len(all_dates)


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward for instrument-combo policy family (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--threshold-grid",
        type=str,
        default="-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.00,0.01,0.02,0.03,0.04,0.05",
    )
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.n_folds < 2:
        raise SystemExit("--n-folds must be >= 2")
    if not args.btc_csv.is_file():
        raise SystemExit(f"BTC CSV required for instrument-combo walk-forward: {args.btc_csv}")

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = sorted(
        [r for r in doc["rows"] if isinstance(r, dict)],
        key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))),
    )
    dates, all_dates_count = _dual_leg_dates(rows)
    if len(dates) < 2:
        raise SystemExit("need at least 2 distinct eval_dates with both kospi+btc legs")

    n_folds_requested = int(args.n_folds)
    n_folds_effective = max(2, min(n_folds_requested, len(dates)))
    n_folds_clamped = n_folds_effective != n_folds_requested

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv)

    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]
    pairs = _threshold_pairs(grid)
    kospi_modes = ["bull", "bear", "neutral", "causal"]

    fold_specs = _blocked_walkforward_folds(dates, n_folds_effective)
    fold_rows_out: list[dict[str, Any]] = []
    test_accs: list[float] = []
    beats_bull_flags: list[bool] = []

    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set = set(train_dates)
        test_set = set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        fitted = _best_combo_on_train(train, km=km, bm=bm, kospi_modes=kospi_modes, pairs=pairs)
        if fitted is None:
            raise SystemExit(f"fold {fi}: no combo candidate")
        k_mode, b_lo, b_hi = fitted
        preds_tr = _instrument_preds(train, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        preds_te = _instrument_preds(test, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        train_acc, train_hit = _acc(train, preds_tr)
        test_acc, test_hit = _acc(test, preds_te)
        bull_test = sum(1 for r in test if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test) if test else 0.0
        beats = test_acc > bull_test
        test_accs.append(test_acc)
        beats_bull_flags.append(beats)
        fold_rows_out.append(
            {
                "fold_index": fi,
                "train_dates": train_dates,
                "test_dates": test_dates,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "best_params_from_train": {
                    "kospi_mode": k_mode,
                    "btc": {"low_thr": b_lo, "high_thr": b_hi},
                },
                "train": {"accuracy": round(train_acc, 6), "hits": train_hit, "n": len(train)},
                "test": {
                    "accuracy": round(test_acc, 6),
                    "hits": test_hit,
                    "n": len(test),
                    "always_bull_control": round(bull_test, 6),
                },
                "test_beats_always_bull": beats,
            }
        )

    mean_test = sum(test_accs) / len(test_accs) if test_accs else 0.0
    var = sum((x - mean_test) ** 2 for x in test_accs) / len(test_accs) if test_accs else 0.0
    stdev_test = math.sqrt(var) if test_accs else 0.0

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "threshold_grid": grid,
            "n_folds": n_folds_effective,
            "n_folds_requested": n_folds_requested,
            "n_folds_effective": n_folds_effective,
            "n_folds_clamped": n_folds_clamped,
            "n_distinct_eval_dates": len(dates),
            "n_distinct_eval_dates_in_score": all_dates_count,
            "n_dropped_non_dual_leg_dates": max(0, all_dates_count - len(dates)),
            "n_walkforward_folds": len(fold_specs),
            "note": "Instrument-combo walk-forward; fit (kospi_mode, btc thresholds) on train blocks only. Non-dual-leg dates are dropped.",
        },
        "folds": fold_rows_out,
        "aggregate": {
            "mean_test_accuracy": round(mean_test, 6),
            "stdev_test_accuracy": round(stdev_test, 6),
            "min_test_accuracy": round(min(test_accs), 6) if test_accs else None,
            "max_test_accuracy": round(max(test_accs), 6) if test_accs else None,
            "fraction_test_beats_always_bull": round(sum(1 for x in beats_bull_flags if x) / len(beats_bull_flags), 6)
            if beats_bull_flags
            else None,
        },
        "note": "Same candidate family as prophecy_instrument_combo_sweep_v1; blocked chronological folds.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"folds={len(fold_rows_out)} mean_test_acc={out['aggregate']['mean_test_accuracy']} "
        f"stdev={out['aggregate']['stdev_test_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
