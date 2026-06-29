#!/usr/bin/env python3
"""[HYPO] RQ-025 Moirai-2 dual-leg intersection WF (180d / 2bps recommended-chain parity).

Blocked walk-forward on KOSPI+BTC calendar intersection; pools hits across legs.
Compares to Primary recommended chain (45%) and fabba sidecar shadow — no Track A merge.
"""

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

from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    load_dual_leg_intersection_window,
    load_instrument_closes_series,
    pool_arms_across_instruments,
)
from scripts.run_rq025_moirai2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _blocked_folds,
    _eval_arm,
    _eval_moirai2_arm,
    _load_moirai2_predictor,
    _moirai_probe,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json"
DEFAULT_PRIMARY = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"
DEFAULT_FABBA_DUAL = ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json"
DEFAULT_KOSPI_MOIRAI = ROOT / "reports/rq025_moirai2_kospi_daily_wf_shadow_v1_latest.json"
SCHEMA = "rq025_moirai2_dual_leg_wf_shadow_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _aggregate(fold_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in fold_metrics if f.get("directional_hit_rate") is not None]
    ns = [f["n_evaluated"] for f in fold_metrics if f.get("n_evaluated")]
    hits = sum(int(f.get("price_hits") or 0) for f in fold_metrics)
    total_n = sum(ns)
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    for f in fold_metrics:
        pd = f.get("pred_distribution") or {}
        for k in dist:
            dist[k] += int(pd.get(k) or 0)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(hits / total_n, 6) if total_n else None,
        "fold_hit_rates": rates,
        "total_n_evaluated": total_n,
        "total_price_hits": hits,
        "n_folds_scored": len(rates),
        "pred_distribution": dist,
    }


def _run_instrument_moirai_panel(
    *,
    instrument_id: str,
    dates: list[str],
    closes: list[float],
    eval_dates: list[str],
    n_folds: int,
    neutral_bps: float,
    predictor: Any | None,
    moirai_context_length: int,
    moirai_batch_size: int,
    moirai_max_eval_points: int,
) -> dict[str, Any]:
    date_to_idx = {d: i for i, d in enumerate(dates)}
    eval_set = [d for d in eval_dates if d in date_to_idx]
    folds = _blocked_folds(eval_set, n_folds)

    mom_fold_rows: dict[str, list[dict[str, Any]]] = {
        "mom_20d": [],
        "moirai2_median_quantile": [],
    }

    for fi, (_train, test) in enumerate(folds):
        mom_fold_rows["mom_20d"].append(
            {
                "fold": fi,
                "test_dates": [test[0], test[-1]],
                **_eval_arm(closes, date_to_idx, lookback=20, neutral_bps=neutral_bps, test_dates=test),
            }
        )
        if predictor is not None:
            mom_fold_rows["moirai2_median_quantile"].append(
                {
                    "fold": fi,
                    "test_dates": [test[0], test[-1]],
                    **_eval_moirai2_arm(
                        closes,
                        dates,
                        date_to_idx,
                        predictor,
                        neutral_bps=neutral_bps,
                        test_dates=test,
                        context_length=moirai_context_length,
                        batch_size=moirai_batch_size,
                        max_eval_points=moirai_max_eval_points,
                    ),
                }
            )
        else:
            mom_fold_rows["moirai2_median_quantile"].append(
                {
                    "fold": fi,
                    "test_dates": [test[0], test[-1]],
                    "directional_hit_rate": None,
                    "n_evaluated": 0,
                    "price_hits": 0,
                }
            )

    arms = []
    for arm_id in ("mom_20d", "moirai2_median_quantile"):
        agg = _aggregate(mom_fold_rows[arm_id])
        arms.append(
            {
                "arm_id": arm_id,
                "protocol": "blocked_walkforward_test_only",
                **agg,
                "folds": mom_fold_rows[arm_id],
            }
        )
    return {"instrument_id": instrument_id, "status": "ok", "arms": arms}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-moirai-inference", action="store_true")
    ap.add_argument("--moirai-model", default="Salesforce/moirai-2.0-R-small")
    ap.add_argument("--moirai-context-length", type=int, default=256)
    ap.add_argument("--moirai-prediction-length", type=int, default=1)
    ap.add_argument("--moirai-batch-size", type=int, default=16)
    ap.add_argument("--moirai-device", default="cpu")
    ap.add_argument("--moirai-max-eval-points", type=int, default=0)
    args = ap.parse_args(argv)

    window = load_dual_leg_intersection_window(
        args.kospi_csv,
        args.btc_csv,
        last_n_intersection=args.last_n_intersection,
    )
    if window.get("status") != "ok":
        print(f"dual-leg window failed: {window}", file=sys.stderr)
        return 2

    eval_dates = window["intersection_dates"]
    probe = _moirai_probe(run_inference=args.run_moirai_inference, model_id=args.moirai_model)
    predictor: Any | None = None
    if args.run_moirai_inference and probe.get("status") == "dependency_ok":
        predictor, load_meta = _load_moirai2_predictor(
            args.moirai_model,
            context_length=args.moirai_context_length,
            prediction_length=args.moirai_prediction_length,
            batch_size=args.moirai_batch_size,
            device=args.moirai_device,
        )
        probe = {**probe, **load_meta}

    per_inst = []
    for inst_id in ("kospi", "btc"):
        panel = window["panels"][inst_id]
        per_inst.append(
            _run_instrument_moirai_panel(
                instrument_id=inst_id,
                dates=panel["dates"],
                closes=panel["closes"],
                eval_dates=eval_dates,
                n_folds=args.n_folds,
                neutral_bps=args.neutral_bps,
                predictor=predictor,
                moirai_context_length=args.moirai_context_length,
                moirai_batch_size=args.moirai_batch_size,
                moirai_max_eval_points=args.moirai_max_eval_points,
            )
        )

    pooled = pool_arms_across_instruments(per_inst)
    moirai_pooled = next((a for a in pooled if a.get("arm_id") == "moirai2_median_quantile"), {})
    mom_pooled = next((a for a in pooled if a.get("arm_id") == "mom_20d"), {})

    primary = _load_json(DEFAULT_PRIMARY) or {}
    primary_hr = (primary.get("metrics") or {}).get("price_directional_hit_rate")
    fabba_dual = _load_json(DEFAULT_FABBA_DUAL) or {}
    fabba_ngram_hr = (fabba_dual.get("compare_primary_recommended_chain") or {}).get("sidecar_ngram_pooled_hr")
    kospi_moirai = _load_json(DEFAULT_KOSPI_MOIRAI) or {}
    kospi_moirai_5bps = (kospi_moirai.get("moirai2_median_quantile_summary") or {}).get(
        "pooled_test_directional_hit_rate"
    )

    moirai_hr = moirai_pooled.get("pooled_test_directional_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "track_a_mutated": False,
        "send_gate": "HOLD",
        "moirai_probe": probe,
        "protocol": {
            "panel": "dual_leg_kospi_btc_intersection",
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "eval_date_from": window["eval_date_from"],
            "eval_date_to": window["eval_date_to"],
            "moirai_model": args.moirai_model,
        },
        "per_instrument": per_inst,
        "dual_leg_pooled_arms": pooled,
        "compare": {
            "primary_recommended_chain_hr": primary_hr,
            "primary_n_evaluated": (primary.get("metrics") or {}).get("n_evaluated"),
            "fabba_ngram_dual_leg_hr": fabba_ngram_hr,
            "kospi_moirai_252d_5bps_hr": kospi_moirai_5bps,
            "moirai_dual_leg_pooled_hr": moirai_hr,
            "moirai_vs_primary_pp": round(float(moirai_hr) - float(primary_hr), 6)
            if moirai_hr is not None and primary_hr is not None
            else None,
            "moirai_vs_fabba_ngram_pp": round(float(moirai_hr) - float(fabba_ngram_hr), 6)
            if moirai_hr is not None and fabba_ngram_hr is not None
            else None,
            "mom_20d_dual_leg_pooled_hr": mom_pooled.get("pooled_test_directional_hit_rate"),
        },
        "interpretation_ko": [
            "dual-leg 180d/2bps = recommended eval chain 코호트 정렬 shadow",
            "moirai2 = median quantile 1-step close → direction; uni2ts optional",
            "Track A·Primary score·fabba sidecar 자동 merge 금지",
        ],
        "reproduce": (
            f"py scripts/run_rq025_moirai2_dual_leg_wf_shadow_v1.py "
            f"--last-n-intersection {args.last_n_intersection} --n-folds {args.n_folds} "
            f"--neutral-bps {args.neutral_bps} --run-moirai-inference"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} moirai={probe.get('status')} "
        f"pooled={moirai_hr} vs_primary={out['compare'].get('moirai_vs_primary_pp')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
