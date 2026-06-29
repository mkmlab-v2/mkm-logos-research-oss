#!/usr/bin/env python3
"""[HYPO] RQ-027 Moirai-2 quantile band sweep on 252d blocked WF (research_only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_rq025_moirai2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _actual_direction,
    _blocked_folds,
    _load_closes,
    _load_moirai2_predictor,
    _moirai_probe,
)
from scripts.run_rq025_chronos2_kospi_daily_wf_shadow_v1 import _mom_pred  # noqa: E402

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq027_moirai_quantile_band_sweep_wf_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
SCHEMA = "rq027_moirai_quantile_band_sweep_wf_v1"

BAND_MODES = (
    "median_always",
    "same_side_beyond_neutral",
    "same_side_any",
    "narrow_band_1pct",
    "narrow_band_2pct",
    "narrow_band_3pct",
    "strict_triple_match",
)


def _env_bootstrap() -> None:
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")


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


def _band_pred(mode: str, c0: float, q10: float, q50: float, q90: float, neutral_bps: float) -> str | None:
    if c0 == 0.0:
        return None
    thr = neutral_bps / 10000.0
    r10 = (q10 - c0) / c0
    r50 = (q50 - c0) / c0
    r90 = (q90 - c0) / c0
    spread = (q90 - q10) / c0

    if mode == "median_always":
        d = _actual_direction(r50, neutral_bps)
        return d if d in ("bull", "bear") else None

    if mode == "strict_triple_match":
        if (r10 > 0 and r90 < 0) or (r10 < 0 and r90 > 0):
            return None
        d50 = _actual_direction(r50, neutral_bps)
        if d50 not in ("bull", "bear"):
            return None
        d10 = _actual_direction(r10, neutral_bps)
        d90 = _actual_direction(r90, neutral_bps)
        return d50 if d10 == d50 == d90 else None

    if mode == "same_side_beyond_neutral":
        if r10 > thr and r90 > thr:
            return "bull"
        if r10 < -thr and r90 < -thr:
            return "bear"
        return None

    if mode == "same_side_any":
        if q10 >= c0 and q90 >= c0:
            d = _actual_direction(r50, neutral_bps)
            return d if d in ("bull", "bear") else None
        if q10 <= c0 and q90 <= c0:
            d = _actual_direction(r50, neutral_bps)
            return d if d in ("bull", "bear") else None
        return None

    if mode == "narrow_band_1pct":
        cap = 0.01
    elif mode == "narrow_band_2pct":
        cap = 0.02
    elif mode == "narrow_band_3pct":
        cap = 0.03
    else:
        return None

    if spread <= cap:
        d = _actual_direction(r50, neutral_bps)
        return d if d in ("bull", "bear") else None
    return None


def _hit_pairs(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    hits = n = 0
    dist: Counter[str] = Counter()
    for pred, act in pairs:
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "n_scored_attempts": len(pairs),
        "coverage_rate": round(n / len(pairs), 4) if pairs else None,
        "price_hits": hits,
        "pred_distribution": dict(dist),
        "pred_bull_share": round(dist.get("bull", 0) / n, 4) if n else None,
    }


def _aggregate(folds: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in folds if f.get("directional_hit_rate") is not None]
    total_n = sum(int(f.get("n_evaluated") or 0) for f in folds)
    total_hits = sum(int(f.get("price_hits") or 0) for f in folds)
    total_attempts = sum(int(f.get("n_scored_attempts") or 0) for f in folds)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(total_hits / total_n, 6) if total_n else None,
        "pooled_coverage_rate": round(total_n / total_attempts, 4) if total_attempts else None,
        "fold_hit_rates": rates,
        "total_n_evaluated": total_n,
        "total_price_hits": total_hits,
        "n_folds_scored": len(rates),
        "folds": folds,
    }


def main(argv: list[str] | None = None) -> int:
    _env_bootstrap()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-moirai-inference", action="store_true")
    ap.add_argument("--moirai-model", default="Salesforce/moirai-2.0-R-small")
    ap.add_argument("--moirai-context", type=int, default=256)
    ap.add_argument("--moirai-batch-size", type=int, default=16)
    ap.add_argument("--moirai-device", default="cpu")
    args = ap.parse_args(argv)

    series = _load_closes(args.kospi_csv)
    if args.eval_days > 0:
        series = series[-args.eval_days :]
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    date_to_idx = {d: i for i, d in enumerate(dates)}
    folds = _blocked_folds(dates, args.n_folds)

    probe = _moirai_probe(run_inference=args.run_moirai_inference, model_id=args.moirai_model)
    predictor = None
    if args.run_moirai_inference and probe.get("status") == "dependency_ok":
        predictor, load_meta = _load_moirai2_predictor(
            args.moirai_model,
            context_length=args.moirai_context,
            prediction_length=1,
            batch_size=args.moirai_batch_size,
            device=args.moirai_device,
        )
        probe = {**probe, **load_meta}

    arm_fold_rows: dict[str, list[dict[str, Any]]] = {m: [] for m in BAND_MODES}
    arm_fold_rows["mom_20d_baseline"] = []

    import numpy as np
    import pandas as pd

    for fi, (_train, test) in enumerate(folds):
        if predictor is None:
            for arm_id in arm_fold_rows:
                arm_fold_rows[arm_id].append(
                    {
                        "fold": fi,
                        "test_dates": [test[0], test[-1]],
                        "directional_hit_rate": None,
                        "n_evaluated": 0,
                        "note": probe.get("status"),
                    }
                )
            continue

        entries: list[dict[str, Any]] = []
        meta: list[dict[str, Any]] = []
        for d in test:
            i = date_to_idx.get(d)
            if i is None or i < 1:
                continue
            c0, c1 = closes[i - 1], closes[i]
            if c0 == 0.0:
                continue
            ret = (c1 - c0) / c0
            if abs(ret) > 0.15:
                continue
            act = _actual_direction(ret, args.neutral_bps)
            ctx = closes[:i]
            if args.moirai_context > 0 and len(ctx) > args.moirai_context:
                ctx = ctx[-args.moirai_context :]
            if len(ctx) < 2:
                continue
            start_idx = max(0, i - len(ctx))
            entries.append(
                {
                    "target": np.asarray(ctx, dtype=np.float32),
                    "start": pd.Period(dates[start_idx], freq="D"),
                }
            )
            meta.append({"i": i, "date": d, "act": act, "c0": c0})

        forecasts: list[Any] = []
        for off in range(0, len(entries), args.moirai_batch_size):
            forecasts.extend(list(predictor.predict(entries[off : off + args.moirai_batch_size])))

        q_cache: list[tuple[float, float, float]] = []
        for j, row in enumerate(meta):
            fc = forecasts[j]
            q10 = float(fc.quantile(0.1)[0])
            q50 = float(fc.quantile(0.5)[0])
            q90 = float(fc.quantile(0.9)[0])
            q_cache.append((q10, q50, q90))

        for mode in BAND_MODES:
            pairs: list[tuple[str, str]] = []
            for j, row in enumerate(meta):
                q10, q50, q90 = q_cache[j]
                pred = _band_pred(mode, row["c0"], q10, q50, q90, args.neutral_bps)
                if pred is None:
                    continue
                pairs.append((pred, row["act"]))
            arm_fold_rows[mode].append({"fold": fi, "test_dates": [test[0], test[-1]], **_hit_pairs(pairs)})

        mom_pairs: list[tuple[str, str]] = []
        for row in meta:
            pred = _mom_pred(closes, row["i"], 20, args.neutral_bps)
            if pred in ("bull", "bear"):
                mom_pairs.append((pred, row["act"]))
        arm_fold_rows["mom_20d_baseline"].append(
            {"fold": fi, "test_dates": [test[0], test[-1]], **_hit_pairs(mom_pairs)}
        )

    arms_out = [
        {
            "arm_id": arm_id,
            "model": "moirai2_quantile_band" if arm_id in BAND_MODES else "classical_momentum_20d",
            "band_mode": arm_id if arm_id in BAND_MODES else None,
            "protocol": "blocked_walkforward_test_only",
            **_aggregate(arm_fold_rows[arm_id]),
        }
        for arm_id in arm_fold_rows
    ]

    wf = _load_json(DEFAULT_WF)
    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    scored = [a for a in arms_out if a.get("pooled_test_directional_hit_rate") is not None and a.get("total_n_evaluated", 0) > 0]
    best_hr = max(scored, key=lambda a: float(a["pooled_test_directional_hit_rate"])) if scored else None
    best_cov = max(
        [a for a in arms_out if a.get("pooled_coverage_rate")],
        key=lambda a: float(a["pooled_coverage_rate"]),
        default=None,
    )

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-027",
        "prior_rq": "RQ-026",
        "window": {"eval_days": args.eval_days, "date_from": dates[0], "date_to": dates[-1], "n_folds": args.n_folds},
        "moirai_probe": probe,
        "blocked_walkforward_test_only": {"arms": arms_out},
        "compare": {
            "wf_majority_pooled_hr": majority_hr,
            "best_hr_arm_id": best_hr.get("arm_id") if best_hr else None,
            "best_hr_pooled": best_hr.get("pooled_test_directional_hit_rate") if best_hr else None,
            "best_coverage_arm_id": best_cov.get("arm_id") if best_cov else None,
            "best_coverage_rate": best_cov.get("pooled_coverage_rate") if best_cov else None,
        },
        "readout_ko": [
            f"{a['arm_id']}: pooled_hr={a.get('pooled_test_directional_hit_rate')} "
            f"coverage={a.get('pooled_coverage_rate')} n={a.get('total_n_evaluated')}"
            for a in arms_out
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
