#!/usr/bin/env python3
"""[HYPO] Holdout7 wrong_dir panel: prod ensemble vs Gemini per-date (no API; disk SSOT)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_causal_ohlc_features_v1 import actual_direction_at_eval, load_btc_ohlc_by_date
from scripts.btrack_wrong_dir_holdout_core_v1 import enrich_btc_row, holdout_dates_from_cf

DEFAULT_OUT = ROOT / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
DEFAULT_CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DEFAULT_PROD = ROOT / "reports/btrack_model_swap_work/per_date_baseline_30d.json"
DEFAULT_GEMINI = ROOT / "reports/btrack_model_swap_work/per_date_gemini_per_date_30d.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _btc_row_index(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed:
            out[ed] = r
    return out


def _price_lens_score(row: dict[str, Any]) -> float | None:
    lv = row.get("lens_values") if isinstance(row.get("lens_values"), dict) else {}
    price = lv.get("price") if isinstance(lv.get("price"), dict) else {}
    sc = price.get("score")
    return float(sc) if sc is not None else None


def _wrong_dir(pred: str, act: str) -> bool:
    p, a = pred.lower(), act.lower()
    return p in ("bull", "bear") and a in ("bull", "bear") and p != a


def build_holdout7_panel(
    *,
    holdout_dates: list[str],
    prod_by_date: dict[str, dict[str, Any]],
    gemini_by_date: dict[str, dict[str, Any]],
    actual_by_date: dict[str, str],
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    ohlc = load_btc_ohlc_by_date(BTC_CSV)
    closes = {d: v["close"] for d, v in ohlc.items()}
    holdout_set = set(holdout_dates)

    panel_rows: list[dict[str, Any]] = []
    prod_wrong = gemini_wrong = both_bull_bear_trap = 0

    for ed in holdout_dates:
        prod = prod_by_date.get(ed) or {}
        gem = gemini_by_date.get(ed) or {}
        act = actual_by_date.get(ed) or actual_direction_at_eval(closes, ed, neutral_bps=neutral_bps) or ""
        act = str(act).lower()

        prod_pred = str(prod.get("predicted_direction") or "").lower()
        gem_pred = str(gem.get("predicted_direction") or "").lower()

        prod_w = _wrong_dir(prod_pred, act)
        gem_w = _wrong_dir(gem_pred, act)
        prod_wrong += int(prod_w)
        gemini_wrong += int(gem_w)
        if act == "bear" and prod_pred == "bull" and gem_pred == "bull":
            both_bull_bear_trap += 1

        enriched = enrich_btc_row(
            dict(prod),
            actual_by_date=actual_by_date,
            holdout_set=holdout_set,
            ohlc=ohlc,
            closes=closes,
        )

        panel_rows.append(
            {
                "eval_date": ed,
                "actual_direction": act,
                "prod": {
                    "predicted_direction": prod_pred or None,
                    "preliminary_direction": str(prod.get("preliminary_direction") or prod_pred).lower() or None,
                    "confidence": prod.get("confidence"),
                    "price_lens_score": _price_lens_score(prod),
                    "is_wrong_direction": prod_w,
                },
                "gemini_per_date": {
                    "predicted_direction": gem_pred or None,
                    "confidence": gem.get("confidence"),
                    "engine": gem.get("engine"),
                    "hypothesis_path": gem.get("hypothesis_path"),
                    "is_wrong_direction": gem_w,
                },
                "same_wrong_dir_as_prod": prod_w and gem_w,
                "both_bull_on_bear_day": act == "bear" and prod_pred == "bull" and gem_pred == "bull",
                "causal_features": {
                    "overnight_return": enriched.get("overnight_return"),
                    "prior_range_position": enriched.get("prior_range_position"),
                    "last_daily_return": enriched.get("last_daily_return"),
                    "realized_vol_5d": enriched.get("realized_vol_5d"),
                    "vol_regime_high": enriched.get("vol_regime_high"),
                },
            }
        )

    n = len(holdout_dates)
    return {
        "schema": "btrack_holdout7_gemini_vs_prod_panel_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "holdout_7_dates": holdout_dates,
        "inputs": {
            "prod_per_date": str(DEFAULT_PROD),
            "gemini_per_date": str(DEFAULT_GEMINI),
            "counterfactual_matrix": str(DEFAULT_CF),
        },
        "summary": {
            "n_holdout_days": n,
            "prod_n_wrong_direction": prod_wrong,
            "gemini_n_wrong_direction": gemini_wrong,
            "both_bull_on_bear_day": both_bull_bear_trap,
            "gemini_avoids_prod_trap": gemini_wrong < prod_wrong,
            "structural_trap_hypothesis": (
                "If gemini_n_wrong_direction equals prod on holdout7, failure is shared "
                "price/bull bias not fixed by cloud LLM swap."
            ),
        },
        "rows": panel_rows,
        "operator_lines": [
            "- [MKM-HOLDOUT7-GEMINI] research_only; auto_promote=false.",
            f"- [MKM-HOLDOUT7-GEMINI] prod wrong_dir={prod_wrong}/{n} gemini={gemini_wrong}/{n} "
            f"both_bull_bear={both_bull_bear_trap}/{n}.",
            (
                "- [MKM-HOLDOUT7-GEMINI] gemini does NOT beat prod on holdout7 wrong_dir."
                if gemini_wrong >= prod_wrong
                else "- [MKM-HOLDOUT7-GEMINI] gemini fewer wrong_dir than prod on holdout7 (review)."
            ),
        ],
        "auto_promote": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--counterfactual", type=Path, default=DEFAULT_CF)
    ap.add_argument("--prod-per-date", type=Path, default=DEFAULT_PROD)
    ap.add_argument("--gemini-per-date", type=Path, default=DEFAULT_GEMINI)
    args = ap.parse_args()

    if not args.prod_per_date.is_file():
        print(f"Missing prod per-date: {args.prod_per_date}", file=sys.stderr)
        return 2
    if not args.gemini_per_date.is_file():
        print(f"Missing gemini per-date: {args.gemini_per_date}", file=sys.stderr)
        return 2

    holdout = holdout_dates_from_cf(args.counterfactual)
    prod_doc = _load(args.prod_per_date)
    gem_doc = _load(args.gemini_per_date)
    prod_by = _btc_row_index(prod_doc)
    gem_by = _btc_row_index(gem_doc)

    actual_by_date: dict[str, str] = {}
    if args.counterfactual.is_file():
        cf = _load(args.counterfactual)
        for row in cf.get("matrix_rows") or []:
            if isinstance(row, dict) and row.get("eval_date"):
                actual_by_date[str(row["eval_date"])[:10]] = str(row.get("actual_direction") or "").lower()

    report = build_holdout7_panel(
        holdout_dates=holdout,
        prod_by_date=prod_by,
        gemini_by_date=gem_by,
        actual_by_date=actual_by_date,
    )
    report["inputs"] = {
        "prod_per_date": str(args.prod_per_date.resolve()),
        "gemini_per_date": str(args.gemini_per_date.resolve()),
        "counterfactual_matrix": str(args.counterfactual.resolve()) if args.counterfactual.is_file() else None,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
