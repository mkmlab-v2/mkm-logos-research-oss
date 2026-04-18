# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.86, K:0.42, M:0.3}
# Balance: 91
# Purpose: Holdout validation for per-date lens combo sweep
# Keywords: prophecy, holdout, validation, per-date, combo
#!/usr/bin/env python3
"""Holdout validation for per-date causal lens combo rule.

Split by eval_date chronology (first half dates train, second half test), fit params on train,
report train/test accuracy vs always-bull control.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_holdout_v1_latest.json"
SCHEMA = "prophecy_per_date_combo_holdout_v1"


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
        if c2:
            out[ed] = (c1 - c2) / c2
    return out


def _sign(x: float | None, dz: float) -> int:
    if x is None:
        return 0
    if x >= dz:
        return 1
    if x <= -dz:
        return -1
    return 0


def _predict(row: dict[str, Any], params: tuple[float, float, float, float, float, float, float], km: dict[str, float], bm: dict[str, float]) -> str:
    dz_self, dz_cross, w_self, w_cross, k_bias, up_thr, down_thr = params
    inst = str(row.get("instrument") or "").strip().lower()
    ed = str(row.get("eval_date") or "").strip()[:10]
    if inst == "kospi":
        self_r, cross_r, bias = km.get(ed), bm.get(ed), k_bias
    else:
        self_r, cross_r, bias = bm.get(ed), km.get(ed), 0.0
    score = (w_self * _sign(self_r, dz_self)) + (w_cross * _sign(cross_r, dz_cross)) + bias
    if score >= up_thr:
        return "bull"
    if score <= down_thr:
        return "bear"
    return "neutral"


def _acc(rows: list[dict[str, Any]], params: tuple[float, float, float, float, float, float, float], km: dict[str, float], bm: dict[str, float]) -> tuple[float, int]:
    h = 0
    for r in rows:
        if _predict(r, params, km, bm) == str(r.get("actual_direction") or "").strip().lower():
            h += 1
    return (h / len(rows)) if rows else 0.0, h


def main() -> int:
    ap = argparse.ArgumentParser(description="Holdout validation for per-date lens combo sweep.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = sorted([r for r in doc["rows"] if isinstance(r, dict)], key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))))
    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    half = max(1, len(dates) // 2)
    train_dates = set(dates[:half])
    test_dates = set(dates[half:])
    train = [r for r in rows if str(r.get("eval_date"))[:10] in train_dates]
    test = [r for r in rows if str(r.get("eval_date"))[:10] in test_dates]

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv) if args.btc_csv.is_file() else {}

    dz_vals = [0.0, 0.01, 0.02, 0.03]
    w_vals = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    b_vals = [0.0, 0.5, 1.0]
    up_vals = [0.5, 1.0, 1.5]
    dn_vals = [-0.5, -1.0, -1.5]

    best: tuple[float, tuple[float, float, float, float, float, float, float] | None] = (-1.0, None)
    for p in itertools.product(dz_vals, dz_vals, w_vals, w_vals, b_vals, up_vals, dn_vals):
        if p[6] >= p[5]:
            continue
        a, _ = _acc(train, p, km, bm)
        if a > best[0]:
            best = (a, p)
    if best[1] is None:
        raise SystemExit("no candidate")

    train_acc, train_hit = _acc(train, best[1], km, bm)
    test_acc, test_hit = _acc(test, best[1], km, bm)
    bull_train = sum(1 for r in train if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(train) if train else 0.0
    bull_test = sum(1 for r in test if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test) if test else 0.0

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "split_dates_total": len(dates),
            "train_dates": sorted(train_dates),
            "test_dates": sorted(test_dates),
        },
        "best_params_from_train": {
            "dz_self": best[1][0],
            "dz_cross": best[1][1],
            "w_self": best[1][2],
            "w_cross": best[1][3],
            "kospi_bull_bias": best[1][4],
            "up_thr": best[1][5],
            "down_thr": best[1][6],
        },
        "train": {"accuracy": round(train_acc, 6), "hits": train_hit, "n": len(train), "always_bull_control": round(bull_train, 6)},
        "test": {"accuracy": round(test_acc, 6), "hits": test_hit, "n": len(test), "always_bull_control": round(bull_test, 6)},
        "test_beats_always_bull": test_acc > bull_test,
        "note": "Holdout fit-on-train/evaluate-on-test for per-date causal combo.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"TRAIN={round(train_acc,6)} TEST={round(test_acc,6)} TEST_BULL={round(bull_test,6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
