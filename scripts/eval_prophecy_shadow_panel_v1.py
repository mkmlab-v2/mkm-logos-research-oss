# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.85, K:0.45, M:0.32}
# Balance: 91
# Purpose: Evaluate shadow prediction lanes on btrack prophecy score panel
# Keywords: prophecy, shadow, eval, panel, btrack
#!/usr/bin/env python3
"""Evaluate shadow prediction lanes on ``btrack_prophecy_score_v1`` rows.

Shadow lanes are B-track measurement only (not live routing, not A-track promotion).

Modes:
- ``instrument_combo_best``: KOSPI fixed mode + BTC causal thresholds from sweep artifact.
- ``per_date_lens_holdout_best``: self/cross prior-return sign combo from holdout artifact.
- ``walkforward_aggregate``: fold-level stability summary from walk-forward JSON (no row-level preds).
- ``both``: instrument + holdout row lanes only.
- ``all``: instrument + holdout + walk-forward aggregate lane.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_COMBO_SWEEP = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_sweep_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_holdout_v1_latest.json"
DEFAULT_WALKFORWARD = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_walkforward_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_shadow_panel_eval_v1_latest.json"
SCHEMA = "prophecy_shadow_panel_eval_v1"
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


def _pred_from_prior(pr: float | None, *, low: float, high: float, fallback: str) -> str:
    if pr is None:
        return fallback
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _sign(x: float | None, dz: float) -> int:
    if x is None:
        return 0
    if x >= dz:
        return 1
    if x <= -dz:
        return -1
    return 0


def _predict_holdout(
    row: dict[str, Any],
    *,
    params: dict[str, float],
    km: dict[str, float],
    bm: dict[str, float],
) -> str:
    dz_self = float(params["dz_self"])
    dz_cross = float(params["dz_cross"])
    w_self = float(params["w_self"])
    w_cross = float(params["w_cross"])
    k_bias = float(params["kospi_bull_bias"])
    up_thr = float(params["up_thr"])
    down_thr = float(params["down_thr"])
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


def _leg_metrics(rows: list[dict[str, Any]], preds: list[str], leg: str) -> dict[str, Any]:
    sub_r = [r for r in rows if str(r.get("instrument") or "").strip().lower() == leg]
    sub_p = [preds[i] for i, r in enumerate(rows) if str(r.get("instrument") or "").strip().lower() == leg]
    return _metrics(sub_r, sub_p)


def _always_bull_control(rows: list[dict[str, Any]]) -> float:
    return sum(1 for r in rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(rows) if rows else 0.0


def _instrument_combo_preds(
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate shadow prediction lanes on prophecy score panel.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--combo-sweep-json", type=Path, default=DEFAULT_COMBO_SWEEP)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WALKFORWARD)
    ap.add_argument(
        "--shadow-mode",
        choices=("instrument_combo_best", "per_date_lens_holdout_best", "walkforward_aggregate", "both", "all"),
        default="both",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    base_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in rows]
    base = _metrics(rows, base_preds)
    bull_ctrl = _always_bull_control(rows)

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv) if args.btc_csv.is_file() else {}

    lanes: list[dict[str, Any]] = []

    if args.shadow_mode in ("instrument_combo_best", "both", "all"):
        sweep = _load_json(args.combo_sweep_json) or {}
        best = sweep.get("best_candidate") if isinstance(sweep.get("best_candidate"), dict) else {}
        k_mode = str(best.get("kospi_mode") or "bull")
        btc = best.get("btc") if isinstance(best.get("btc"), dict) else {}
        b_lo = float(btc.get("low_thr", -0.03))
        b_hi = float(btc.get("high_thr", -0.02))
        preds = _instrument_combo_preds(rows, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        m_all = _metrics(rows, preds)
        lanes.append(
            {
                "lane_id": "instrument_combo_best_v1",
                "source_artifact": str(args.combo_sweep_json),
                "params": {"kospi_mode": k_mode, "btc": {"low_thr": b_lo, "high_thr": b_hi}},
                "metrics_all": m_all,
                "metrics_kospi_leg": _leg_metrics(rows, preds, "kospi"),
                "metrics_btc_leg": _leg_metrics(rows, preds, "btc"),
                "delta_vs_baseline": round(float(m_all["price_directional_hit_rate"] or 0.0) - float(base["price_directional_hit_rate"] or 0.0), 6),
                "delta_vs_always_bull_control": round(float(m_all["price_directional_hit_rate"] or 0.0) - bull_ctrl, 6),
            }
        )

    if args.shadow_mode in ("per_date_lens_holdout_best", "both", "all"):
        ho = _load_json(args.holdout_json) or {}
        bp = ho.get("best_params_from_train") if isinstance(ho.get("best_params_from_train"), dict) else {}
        preds = [_predict_holdout(r, params=bp, km=km, bm=bm) for r in rows]
        m_all = _metrics(rows, preds)
        lanes.append(
            {
                "lane_id": "per_date_lens_holdout_best_v1",
                "source_artifact": str(args.holdout_json),
                "params": bp,
                "metrics_all": m_all,
                "metrics_kospi_leg": _leg_metrics(rows, preds, "kospi"),
                "metrics_btc_leg": _leg_metrics(rows, preds, "btc"),
                "delta_vs_baseline": round(float(m_all["price_directional_hit_rate"] or 0.0) - float(base["price_directional_hit_rate"] or 0.0), 6),
                "delta_vs_always_bull_control": round(float(m_all["price_directional_hit_rate"] or 0.0) - bull_ctrl, 6),
                "holdout_test_summary": ho.get("test") if isinstance(ho.get("test"), dict) else None,
            }
        )

    if args.shadow_mode in ("walkforward_aggregate", "all"):
        wf = _load_json(args.walkforward_json) or {}
        agg = wf.get("aggregate") if isinstance(wf.get("aggregate"), dict) else {}
        if agg:
            folds = wf.get("folds")
            n_folds = len(folds) if isinstance(folds, list) else 0
            lanes.append(
                {
                    "lane_id": "per_date_combo_walkforward_aggregate_v1",
                    "lane_kind": "fold_aggregate",
                    "source_artifact": str(args.walkforward_json),
                    "metrics_all": None,
                    "walkforward_aggregate": agg,
                    "walkforward_fold_count": n_folds,
                    "walkforward_inputs": wf.get("inputs") if isinstance(wf.get("inputs"), dict) else {},
                }
            )

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "shadow_mode": args.shadow_mode,
            "combo_sweep_json": str(args.combo_sweep_json),
            "holdout_json": str(args.holdout_json),
            "walkforward_json": str(args.walkforward_json),
        },
        "baseline": {"lane_id": "current_panel_prediction", "metrics": base},
        "control": {"lane_id": "always_bull_control", "price_directional_hit_rate": round(bull_ctrl, 6)},
        "lanes": lanes,
        "note": "Shadow lanes are measurement-only; do not route live trades from this artifact alone.",
    }

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
