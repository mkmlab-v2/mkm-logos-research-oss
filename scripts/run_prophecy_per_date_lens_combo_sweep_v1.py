# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.9, K:0.46, M:0.31}
# Balance: 91
# Purpose: Per-date causal lens combo sweep on prophecy panel
# Keywords: prophecy, per-date, lens, combo, sweep, causal
#!/usr/bin/env python3
"""Per-date causal lens combo sweep (B-track research).

Builds row-level causal features from prior completed daily returns:
- self sign (same instrument)
- cross sign (other instrument on same eval_date)

Then sweeps linear-combo weights and score thresholds to pick direction.
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_lens_combo_sweep_v1_latest.json"
SCHEMA = "prophecy_per_date_lens_combo_sweep_v1"
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


def _sign(x: float | None, deadzone: float) -> int:
    if x is None:
        return 0
    if x >= deadzone:
        return 1
    if x <= -deadzone:
        return -1
    return 0


def _dir(score: float, up_thr: float, down_thr: float) -> str:
    if score >= up_thr:
        return "bull"
    if score <= down_thr:
        return "bear"
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-date causal lens combo sweep (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--deadzone-grid",
        type=str,
        default="0.00,0.01,0.02,0.03",
        help="Comma-separated deadzone fractions for prior-return sign.",
    )
    ap.add_argument(
        "--weight-grid",
        type=str,
        default="-1.0,-0.5,0.0,0.5,1.0,1.5",
        help="Comma-separated weights for self/cross signals.",
    )
    ap.add_argument(
        "--bias-grid",
        type=str,
        default="0.0,0.5,1.0",
        help="Comma-separated bullish bias applied only to kospi rows.",
    )
    ap.add_argument("--up-thr-grid", type=str, default="0.5,1.0,1.5")
    ap.add_argument("--down-thr-grid", type=str, default="-0.5,-1.0,-1.5")
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

    dz_grid = [float(x.strip()) for x in args.deadzone_grid.split(",") if x.strip()]
    w_grid = [float(x.strip()) for x in args.weight_grid.split(",") if x.strip()]
    b_grid = [float(x.strip()) for x in args.bias_grid.split(",") if x.strip()]
    up_grid = [float(x.strip()) for x in args.up_thr_grid.split(",") if x.strip()]
    dn_grid = [float(x.strip()) for x in args.down_thr_grid.split(",") if x.strip()]

    results: list[dict[str, Any]] = []
    for dz_self, dz_cross, w_self, w_cross, b_kospi, up_thr, down_thr in itertools.product(
        dz_grid, dz_grid, w_grid, w_grid, b_grid, up_grid, dn_grid
    ):
        if down_thr >= up_thr:
            continue
        preds: list[str] = []
        changed = 0
        missing = 0
        for r in rows:
            inst = str(r.get("instrument") or "").strip().lower()
            ed = str(r.get("eval_date") or "").strip()[:10]
            old = str(r.get("predicted_direction") or "").strip().lower()
            if inst == "kospi":
                self_ret, cross_ret = km.get(ed), bm.get(ed)
                bias = b_kospi
            else:
                self_ret, cross_ret = bm.get(ed), km.get(ed)
                bias = 0.0
            if self_ret is None:
                missing += 1
            if cross_ret is None:
                missing += 1
            s_self = _sign(self_ret, dz_self)
            s_cross = _sign(cross_ret, dz_cross)
            score = (w_self * s_self) + (w_cross * s_cross) + bias
            p = _dir(score, up_thr=up_thr, down_thr=down_thr)
            preds.append(p)
            if p != old:
                changed += 1
        m = _metrics(rows, preds)
        rate = float(m["price_directional_hit_rate"] or 0.0)
        results.append(
            {
                "params": {
                    "dz_self": dz_self,
                    "dz_cross": dz_cross,
                    "w_self": w_self,
                    "w_cross": w_cross,
                    "kospi_bull_bias": b_kospi,
                    "up_thr": up_thr,
                    "down_thr": down_thr,
                },
                "metrics": m,
                "delta_vs_baseline": round(rate - base_rate, 6),
                "delta_vs_always_bull_control": round(rate - bull_control, 6),
                "changed_rows": changed,
                "missing_prior_refs": missing,
            }
        )

    ranked = sorted(
        results,
        key=lambda x: (float(x["metrics"].get("price_directional_hit_rate") or -1.0), int(x.get("changed_rows", 0))),
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
            "deadzone_grid": dz_grid,
            "weight_grid": w_grid,
            "bias_grid": b_grid,
            "up_thr_grid": up_grid,
            "down_thr_grid": dn_grid,
            "total_candidates": len(results),
        },
        "baseline": {"lane_id": "current_panel_prediction", "metrics": base},
        "control": {"lane_id": "always_bull_control", "price_directional_hit_rate": round(bull_control, 6)},
        "best_candidate": best,
        "top_candidates": ranked[: max(1, int(args.top_k))],
        "note": "Per-date causal lens combo sweep with self/cross prior-return signs.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        print(
            f"BASE={base['price_directional_hit_rate']} BULL_CTRL={round(bull_control,6)} "
            f"BEST={best['metrics'].get('price_directional_hit_rate')} changed={best['changed_rows']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
