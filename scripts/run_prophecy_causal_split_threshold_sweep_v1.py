# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.88, K:0.45, M:0.3}
# Balance: 91
# Purpose: Causal split-threshold sweep by instrument (KOSPI/BTC)
# Keywords: prophecy, causal, threshold, sweep, kospi, btc
#!/usr/bin/env python3
"""Causal split-threshold sweep (instrument-specific thresholds).

Per row:
  use KOSPI thresholds for instrument=kospi
  use BTC thresholds for instrument=btc
  if prior_return <= low: bear
  elif prior_return >= high: bull
  else: neutral

No eval-day lookahead (prior completed daily return only).
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_split_threshold_sweep_v1_latest.json"
SCHEMA = "prophecy_causal_split_threshold_sweep_v1"
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


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    if len(rows) < 3:
        return out
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


def _preds(
    rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    k_lo: float,
    k_hi: float,
    b_lo: float,
    b_hi: float,
) -> tuple[list[str], int, int]:
    out: list[str] = []
    changed = 0
    missing = 0
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        old = str(r.get("predicted_direction") or "").strip().lower()
        if inst == "kospi":
            pr = km.get(ed)
            lo, hi = k_lo, k_hi
        else:
            pr = bm.get(ed)
            lo, hi = b_lo, b_hi
        if pr is None:
            p = old if old in VALID else "neutral"
            missing += 1
        elif pr <= lo:
            p = "bear"
        elif pr >= hi:
            p = "bull"
        else:
            p = "neutral"
        out.append(p)
        if p != old:
            changed += 1
    return out, changed, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Causal split-threshold sweep by instrument (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--threshold-grid",
        type=str,
        default="-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.00,0.01,0.02,0.03,0.04,0.05",
    )
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    base_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in rows]
    base = _metrics(rows, base_preds)
    base_rate = float(base["price_directional_hit_rate"] or 0.0)
    bull_control = sum(1 for r in rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(rows)

    km = _prior_completed_daily_return_by_eval_date(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}

    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]
    pairs = [(lo, hi) for lo, hi in itertools.product(grid, grid) if lo < hi]

    results: list[dict[str, Any]] = []
    for (k_lo, k_hi), (b_lo, b_hi) in itertools.product(pairs, pairs):
        preds, changed, missing = _preds(rows, km=km, bm=bm, k_lo=k_lo, k_hi=k_hi, b_lo=b_lo, b_hi=b_hi)
        m = _metrics(rows, preds)
        rate = float(m["price_directional_hit_rate"] or 0.0)
        results.append(
            {
                "kospi": {"low_thr": k_lo, "high_thr": k_hi},
                "btc": {"low_thr": b_lo, "high_thr": b_hi},
                "metrics": m,
                "delta_vs_baseline": round(rate - base_rate, 6),
                "delta_vs_always_bull_control": round(rate - bull_control, 6),
                "changed_rows": changed,
                "missing_prior_rows": missing,
            }
        )

    ranked = sorted(
        results,
        key=lambda x: (
            float(x["metrics"].get("price_directional_hit_rate") or -1.0),
            int(x.get("changed_rows", 0)),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "threshold_grid": grid,
            "candidate_pairs_per_instrument": len(pairs),
            "total_candidates": len(results),
        },
        "baseline": {"lane_id": "current_panel_prediction", "metrics": base},
        "control": {"lane_id": "always_bull_control", "price_directional_hit_rate": round(bull_control, 6)},
        "best_candidate": best,
        "top_candidates": ranked[: max(1, int(args.top_k))],
        "note": "Instrument-specific causal threshold sweep; no same-day lookahead.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        print(
            f"BASE={base['price_directional_hit_rate']} "
            f"BULL_CTRL={round(bull_control,6)} "
            f"BEST={best['metrics'].get('price_directional_hit_rate')} "
            f"chg={best['changed_rows']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
