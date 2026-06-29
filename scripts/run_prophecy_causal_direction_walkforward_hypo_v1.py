#!/usr/bin/env python3
"""Blocked walk-forward probe for fixed causal direction rule (B-track, reports lane).

Compares in-sample full-panel uplift (threshold chosen on same panel) vs
out-of-sample test-block accuracy with **fixed** (low_thr, high_thr) — no per-fold
threshold search on the test block.

Does not modify ``btrack_prophecy_score_latest.json``.
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
DEFAULT_OUT = ROOT / "reports" / "prophecy_causal_direction_walkforward_hypo_v1_latest.json"
SCHEMA = "prophecy_causal_direction_walkforward_hypo_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        return fallback if fallback in VALID else "neutral"
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _preds_for_rows(
    rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    low: float,
    high: float,
) -> list[str]:
    preds: list[str] = []
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        old = str(r.get("predicted_direction") or "").strip().lower()
        mp = km if inst == "kospi" else bm
        preds.append(_pred_from_prior(mp.get(ed), low=low, high=high, fallback=old))
    return preds


def _metrics(rows: list[dict[str, Any]], preds: list[str]) -> dict[str, Any]:
    n = h = 0
    for r, p in zip(rows, preds):
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            h += 1
    return {
        "price_directional_hit_rate": round(h / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": h,
    }


def _blocked_folds(dates_sorted: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates_sorted)
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


def _best_pair_on_train(
    train_rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    grid: list[float],
    base_rate: float,
) -> tuple[float, float, dict[str, Any]]:
    pairs = [(lo, hi) for lo, hi in itertools.product(grid, grid) if lo < hi]
    best_lo, best_hi = 0.01, 0.02
    best_m: dict[str, Any] = {"price_directional_hit_rate": None, "n_evaluated": 0, "price_hits": 0}
    best_rate = -1.0
    for lo, hi in pairs:
        preds = _preds_for_rows(train_rows, km=km, bm=bm, low=lo, high=hi)
        m = _metrics(train_rows, preds)
        rate = float(m["price_directional_hit_rate"] or 0.0)
        if rate > best_rate:
            best_rate = rate
            best_lo, best_hi = lo, hi
            best_m = m
    return best_lo, best_hi, {
        "metrics": best_m,
        "delta_vs_baseline": round(best_rate - base_rate, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fixed causal direction blocked WF probe (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--low-thr", type=float, default=0.01)
    ap.add_argument("--high-thr", type=float, default=0.02)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument(
        "--threshold-grid",
        type=str,
        default="-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.00,0.01,0.02,0.03,0.04,0.05",
        help="Grid for per-fold train-only threshold pick (contrast lane).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.low_thr >= args.high_thr:
        raise SystemExit("--low-thr must be < --high-thr")

    doc = _load_json(args.score_json)
    rows = [r for r in doc.get("rows", []) if isinstance(r, dict)]
    if not rows:
        raise SystemExit("score rows[] empty")

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv) if args.btc_csv.is_file() else {}
    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]

    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows if str(r.get("eval_date") or "").strip()})
    n_folds = max(2, min(int(args.n_folds), len(dates)))
    fold_specs = _blocked_folds(dates, n_folds)

    base_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in rows]
    in_sample_baseline = _metrics(rows, base_preds)
    in_sample_fixed = _metrics(
        rows, _preds_for_rows(rows, km=km, bm=bm, low=args.low_thr, high=args.high_thr)
    )

    fixed_test_accs: list[float] = []
    base_test_accs: list[float] = []
    train_tuned_test_accs: list[float] = []
    fold_out: list[dict[str, Any]] = []

    base_rate_full = float(in_sample_baseline["price_directional_hit_rate"] or 0.0)

    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set, test_set = set(train_dates), set(test_dates)
        train = [r for r in rows if str(r.get("eval_date") or "")[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date") or "")[:10] in test_set]

        base_test_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in test]
        fixed_test_preds = _preds_for_rows(test, km=km, bm=bm, low=args.low_thr, high=args.high_thr)
        m_base = _metrics(test, base_test_preds)
        m_fixed = _metrics(test, fixed_test_preds)

        tr_lo, tr_hi, train_pick = _best_pair_on_train(
            train, km=km, bm=bm, grid=grid, base_rate=base_rate_full
        )
        tuned_test_preds = _preds_for_rows(test, km=km, bm=bm, low=tr_lo, high=tr_hi)
        m_tuned = _metrics(test, tuned_test_preds)

        b_acc = float(m_base["price_directional_hit_rate"] or 0.0)
        f_acc = float(m_fixed["price_directional_hit_rate"] or 0.0)
        t_acc = float(m_tuned["price_directional_hit_rate"] or 0.0)
        base_test_accs.append(b_acc)
        fixed_test_accs.append(f_acc)
        train_tuned_test_accs.append(t_acc)

        fold_out.append(
            {
                "fold_index": fi,
                "train_dates": train_dates,
                "test_dates": test_dates,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "baseline_test": m_base,
                "fixed_causal_test": {
                    **m_fixed,
                    "low_thr": args.low_thr,
                    "high_thr": args.high_thr,
                    "delta_vs_baseline_test": round(f_acc - b_acc, 6),
                },
                "train_tuned_then_test": {
                    "train_selected_low_thr": tr_lo,
                    "train_selected_high_thr": tr_hi,
                    "train_fit": train_pick,
                    "test_metrics": m_tuned,
                    "delta_vs_baseline_test": round(t_acc - b_acc, 6),
                },
            }
        )

    def _agg(accs: list[float]) -> dict[str, Any]:
        if not accs:
            return {"mean_test_accuracy": None, "stdev_test_accuracy": None}
        mean = sum(accs) / len(accs)
        var = sum((x - mean) ** 2 for x in accs) / len(accs)
        return {
            "mean_test_accuracy": round(mean, 6),
            "stdev_test_accuracy": round(math.sqrt(var), 6),
            "min_test_accuracy": round(min(accs), 6),
            "max_test_accuracy": round(max(accs), 6),
        }

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "production_score_unmodified": True,
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "fixed_low_thr": args.low_thr,
            "fixed_high_thr": args.high_thr,
            "n_folds": n_folds,
            "n_distinct_eval_dates": len(dates),
            "n_walkforward_folds": len(fold_specs),
        },
        "in_sample_full_panel": {
            "baseline": in_sample_baseline,
            "fixed_causal_rule": in_sample_fixed,
            "delta_hit_rate": round(
                float(in_sample_fixed["price_directional_hit_rate"] or 0.0)
                - float(in_sample_baseline["price_directional_hit_rate"] or 0.0),
                6,
            ),
            "note": "Threshold 0.01/0.02 chosen on same panel (in-sample); not OOS.",
        },
        "blocked_walkforward_test_only": {
            "fixed_causal_rule": _agg(fixed_test_accs),
            "baseline_panel_prediction": _agg(base_test_accs),
            "train_tuned_threshold_then_test": _agg(train_tuned_test_accs),
            "delta_fixed_minus_baseline_mean_test": round(
                (sum(fixed_test_accs) / len(fixed_test_accs) if fixed_test_accs else 0.0)
                - (sum(base_test_accs) / len(base_test_accs) if base_test_accs else 0.0),
                6,
            ),
            "note": "Fixed rule: no threshold search on test block. train_tuned lane fits thresholds on train only.",
        },
        "folds": fold_out,
        "verdict_ko": (
            "in_sample +5pp와 blocked WF mean_test가 분리되면 GATE_FAILED_HOLD 유지; "
            "Track A·live 자동 합선 없음."
        ),
        "track_wall": {"auto_bridge_to_a_track": False, "live_trading_trigger": False},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"in_sample_fixed={in_sample_fixed['price_directional_hit_rate']} "
        f"wf_fixed_mean={out['blocked_walkforward_test_only']['fixed_causal_rule']['mean_test_accuracy']} "
        f"wf_baseline_mean={out['blocked_walkforward_test_only']['baseline_panel_prediction']['mean_test_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
