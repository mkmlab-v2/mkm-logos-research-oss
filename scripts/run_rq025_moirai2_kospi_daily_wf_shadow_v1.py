#!/usr/bin/env python3
"""[HYPO] RQ-025 Moirai-2 quantile KOSPI daily walk-forward shadow (B-track, research_only).

Blocked chronological WF on KOSPI daily direction. Uses Moirai 2.0 median quantile
(1-step close) when ``uni2ts`` is installed; otherwise records momentum baselines only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq025_moirai2_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_CHRONOS2 = ROOT / "reports/rq025_chronos2_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_TIMESFM = ROOT / "reports/rq025_timesfm25_kospi_daily_wf_shadow_v1_latest.json"
SCHEMA = "rq025_moirai2_kospi_daily_wf_shadow_v1"


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


def _load_closes(csv_path: Path) -> list[tuple[str, float]]:
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: list[tuple[str, float]] = []
    for r in rows:
        try:
            out.append((str(r["date"])[:10], float(r["close"])))
        except (TypeError, ValueError, KeyError):
            continue
    return out


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _mom_pred(closes: list[float], idx: int, lookback: int, neutral_bps: float) -> str:
    if idx < lookback:
        return "neutral"
    c0 = closes[idx - lookback]
    c1 = closes[idx - 1]
    if c0 == 0.0:
        return "neutral"
    return _actual_direction((c1 - c0) / c0, neutral_bps)


def _blocked_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates)
    if n_folds < 2 or n < n_folds:
        return []
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates[idx : idx + sz])
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


def _eval_arm(
    closes: list[float],
    date_to_idx: dict[str, int],
    *,
    lookback: int,
    neutral_bps: float,
    test_dates: list[str],
) -> dict[str, Any]:
    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    for d in test_dates:
        i = date_to_idx.get(d)
        if i is None or i < 1:
            continue
        c0 = closes[i - 1]
        c1 = closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        pred = _mom_pred(closes, i, lookback, neutral_bps)
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] = dist.get(pred, 0) + 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dist,
    }


def _moirai_probe(*, run_inference: bool, model_id: str) -> dict[str, Any]:
    _env_bootstrap()
    if not run_inference:
        return {
            "status": "skipped_by_flag",
            "install_hint": "pass --run-moirai-inference",
        }
    try:
        ok = bool(importlib.util.find_spec("uni2ts"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped_error", "error": str(exc)}
    if not ok:
        return {
            "status": "skipped_missing_dependency",
            "install_hint": "pip install uni2ts==2.0.0 (torch/torchvision version alignment may be required on Windows)",
            "model_id": model_id,
        }
    try:
        from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "skipped_import_error",
            "error": str(exc),
            "install_hint": "torch/torchvision mismatch: try torchvision==0.19.1 for torch 2.4.x",
        }
    return {"status": "dependency_ok", "model_id": model_id}


def _load_moirai2_predictor(
    model_id: str,
    *,
    context_length: int,
    prediction_length: int,
    batch_size: int,
    device: str,
) -> tuple[Any | None, dict[str, Any]]:
    _env_bootstrap()
    try:
        import pandas as pd  # noqa: F401
        from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_import_error", "error": str(exc)}
    try:
        module = Moirai2Module.from_pretrained(model_id)
        model = Moirai2Forecast(
            module=module,
            prediction_length=prediction_length,
            context_length=context_length,
            target_dim=1,
            feat_dynamic_real_dim=0,
            past_feat_dynamic_real_dim=0,
        )
        predictor = model.create_predictor(batch_size=batch_size, device=device)
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_load_error", "error": str(exc), "model_id": model_id}
    return predictor, {
        "status": "loaded",
        "model_id": model_id,
        "context_length": context_length,
        "prediction_length": prediction_length,
        "quantile_levels": getattr(module, "quantile_levels", None),
        "device": device,
    }


def _eval_moirai2_arm(
    closes: list[float],
    dates: list[str],
    date_to_idx: dict[str, int],
    predictor: Any,
    *,
    neutral_bps: float,
    test_dates: list[str],
    context_length: int,
    batch_size: int,
    max_eval_points: int,
) -> dict[str, Any]:
    import numpy as np
    import pandas as pd

    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    entries: list[dict[str, Any]] = []
    meta: list[tuple[int, str]] = []

    for d in test_dates:
        if max_eval_points > 0 and len(entries) >= max_eval_points:
            break
        i = date_to_idx.get(d)
        if i is None or i < 1:
            continue
        c0 = closes[i - 1]
        c1 = closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        ctx = closes[:i]
        if context_length > 0 and len(ctx) > context_length:
            ctx = ctx[-context_length:]
        if len(ctx) < 2:
            continue
        start_idx = max(0, i - len(ctx))
        entries.append(
            {
                "target": np.asarray(ctx, dtype=np.float32),
                "start": pd.Period(dates[start_idx], freq="D"),
            }
        )
        meta.append((i, act))

    if not entries:
        return {
            "directional_hit_rate": None,
            "n_evaluated": 0,
            "price_hits": 0,
            "pred_distribution": dist,
        }

    forecasts: list[Any] = []
    for off in range(0, len(entries), batch_size):
        chunk = entries[off : off + batch_size]
        forecasts.extend(list(predictor.predict(chunk)))

    for j, (i, act) in enumerate(meta):
        c0 = closes[i - 1]
        fc = forecasts[j]
        med_arr = fc.quantile(0.5)
        pred_close = float(med_arr[0] if len(med_arr) else med_arr)
        pred = _actual_direction((pred_close - c0) / c0, neutral_bps)
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] = dist.get(pred, 0) + 1
        if pred == act:
            hits += 1

    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dist,
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
    ap.add_argument("--moirai-context-length", type=int, default=256)
    ap.add_argument("--moirai-prediction-length", type=int, default=1)
    ap.add_argument("--moirai-batch-size", type=int, default=16)
    ap.add_argument("--moirai-device", default="cpu")
    ap.add_argument("--moirai-max-eval-points", type=int, default=0)
    args = ap.parse_args(argv)

    if not args.kospi_csv.is_file():
        print(f"missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 2

    series = _load_closes(args.kospi_csv)
    if len(series) < 30:
        print("insufficient kospi rows", file=sys.stderr)
        return 2

    if args.eval_days > 0:
        series = series[-args.eval_days :]
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    date_to_idx = {d: i for i, d in enumerate(dates)}
    folds = _blocked_folds(dates, args.n_folds)

    mom_arms = [("mom_1d", 1), ("mom_5d", 5), ("mom_20d", 20)]
    arm_fold_rows: dict[str, list[dict[str, Any]]] = {aid: [] for aid, _ in mom_arms}
    arm_fold_rows["moirai2_median_quantile"] = []

    for fi, (_train, test) in enumerate(folds):
        for arm_id, lb in mom_arms:
            m = _eval_arm(
                closes,
                date_to_idx,
                lookback=lb,
                neutral_bps=args.neutral_bps,
                test_dates=test,
            )
            arm_fold_rows[arm_id].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})

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

    if predictor is not None:
        for fi, (_train, test) in enumerate(folds):
            m = _eval_moirai2_arm(
                closes,
                dates,
                date_to_idx,
                predictor,
                neutral_bps=args.neutral_bps,
                test_dates=test,
                context_length=args.moirai_context_length,
                batch_size=args.moirai_batch_size,
                max_eval_points=args.moirai_max_eval_points,
            )
            arm_fold_rows["moirai2_median_quantile"].append(
                {"fold": fi, "test_dates": [test[0], test[-1]], **m}
            )
    elif args.run_moirai_inference:
        for fi, (_train, test) in enumerate(folds):
            arm_fold_rows["moirai2_median_quantile"].append(
                {
                    "fold": fi,
                    "test_dates": [test[0], test[-1]],
                    "directional_hit_rate": None,
                    "n_evaluated": 0,
                    "note": probe.get("status"),
                }
            )

    def _aggregate(fold_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        rates = [f["directional_hit_rate"] for f in fold_metrics if f.get("directional_hit_rate") is not None]
        ns = [f["n_evaluated"] for f in fold_metrics if f.get("n_evaluated")]
        hits = sum(int(f.get("price_hits") or 0) for f in fold_metrics)
        total_n = sum(ns)
        return {
            "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
            "pooled_test_directional_hit_rate": round(hits / total_n, 6) if total_n else None,
            "fold_hit_rates": rates,
            "total_n_evaluated": total_n,
            "total_price_hits": hits,
            "n_folds_scored": len(rates),
        }

    arms_out: list[dict[str, Any]] = []
    for arm_id, lb in mom_arms:
        agg = _aggregate(arm_fold_rows[arm_id])
        arms_out.append(
            {
                "arm_id": arm_id,
                "model": f"classical_momentum_{lb}d",
                "protocol": "blocked_walkforward_test_only",
                "lookback_days": lb,
                **agg,
                "folds": arm_fold_rows[arm_id],
            }
        )

    moirai_agg = _aggregate(arm_fold_rows["moirai2_median_quantile"])
    arms_out.append(
        {
            "arm_id": "moirai2_median_quantile",
            "model": args.moirai_model,
            "protocol": "blocked_walkforward_test_only",
            "moirai_probe": probe,
            "quantile_used": 0.5,
            "context_length": args.moirai_context_length,
            **moirai_agg,
            "folds": arm_fold_rows["moirai2_median_quantile"],
        }
    )

    wf_compare = _load_json(DEFAULT_WF_COMPARE)
    chronos2 = _load_json(DEFAULT_CHRONOS2)
    timesfm = _load_json(DEFAULT_TIMESFM)
    wf_majority = None
    if wf_compare:
        wf_majority = (wf_compare.get("blocked_walkforward_test_only") or {}).get("best_pooled_hr")
        if wf_majority is None:
            arms = (wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or []
            maj = next((a for a in arms if a.get("arm_id") == "majority_from_train"), None)
            if maj:
                wf_majority = maj.get("pooled_test_directional_hit_rate")

    best_mom = max(
        (a for a in arms_out if a["arm_id"].startswith("mom_")),
        key=lambda a: (a.get("mean_test_directional_hit_rate") or -1.0),
    )
    moirai_arm = next((a for a in arms_out if a["arm_id"] == "moirai2_median_quantile"), {})
    moirai_pooled = moirai_arm.get("pooled_test_directional_hit_rate")
    moirai_dist = {}
    for f in arm_fold_rows["moirai2_median_quantile"]:
        pdist = f.get("pred_distribution") or {}
        for k, v in pdist.items():
            moirai_dist[k] = moirai_dist.get(k, 0) + int(v or 0)
    pred_total = sum(moirai_dist.values()) or 1
    bull_share = round(moirai_dist.get("bull", 0) / pred_total, 4)

    chronos_pooled = None
    if chronos2:
        arms = (chronos2.get("blocked_walkforward_test_only") or {}).get("arms") or []
        c2 = next((a for a in arms if a.get("arm_id") == "chronos2_zero_shot"), None)
        chronos_pooled = (c2 or {}).get("pooled_test_directional_hit_rate")
    timesfm_pooled = None
    if timesfm:
        arms = (timesfm.get("blocked_walkforward_test_only") or {}).get("arms") or []
        tf = next((a for a in arms if a.get("arm_id") == "timesfm25_zero_shot"), None)
        timesfm_pooled = (tf or {}).get("pooled_test_directional_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "track_a_mutated": False,
        "window": {
            "eval_days": args.eval_days,
            "date_from": dates[0],
            "date_to": dates[-1],
            "n_calendar_days": len(dates),
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
        },
        "blocked_walkforward_test_only": {"arms": arms_out},
        "best_momentum_baseline": {
            "arm_id": best_mom["arm_id"],
            "mean_test_directional_hit_rate": best_mom.get("mean_test_directional_hit_rate"),
            "pooled_test_directional_hit_rate": best_mom.get("pooled_test_directional_hit_rate"),
        },
        "moirai2_median_quantile_summary": {
            "status": probe.get("status"),
            "mean_test_directional_hit_rate": moirai_arm.get("mean_test_directional_hit_rate"),
            "pooled_test_directional_hit_rate": moirai_pooled,
            "pred_distribution_pooled": moirai_dist,
            "pred_bull_share": bull_share,
            "pred_mostly_bull": bull_share >= 0.9,
            "vs_wf_majority_pooled_pp": round((moirai_pooled - wf_majority) * 100, 2)
            if moirai_pooled is not None and wf_majority is not None
            else None,
            "vs_chronos2_pooled_pp": round((moirai_pooled - chronos_pooled) * 100, 2)
            if moirai_pooled is not None and chronos_pooled is not None
            else None,
            "vs_timesfm25_pooled_pp": round((moirai_pooled - timesfm_pooled) * 100, 2)
            if moirai_pooled is not None and timesfm_pooled is not None
            else None,
        },
        "wf_holdout_compare_pointer": str(DEFAULT_WF_COMPARE.relative_to(ROOT)).replace("\\", "/")
        if wf_compare
        else None,
        "wf_majority_pooled_hr": wf_majority,
        "chronos2_pointer": str(DEFAULT_CHRONOS2.relative_to(ROOT)).replace("\\", "/") if chronos2 else None,
        "timesfm25_pointer": str(DEFAULT_TIMESFM.relative_to(ROOT)).replace("\\", "/") if timesfm else None,
        "interpretation_ko": [
            "moirai2 arm = median quantile (0.5) 1-step close → direction; context_length 기본 256.",
            "blocked WF OOS only — Track A·headline·live 자동 교체 없음.",
            "wf_majority(63.2%) 초과 + pred 90%+ bull 이면 classical flow / timesfm+xreg 가짜 1등과 동일 경계.",
            "Windows: pip install uni2ts==2.0.0; torch/torchvision 정렬 필요 시 torchvision==0.19.1 (torch 2.4.x).",
        ],
        "reproduce": (
            f"py scripts/run_rq025_moirai2_kospi_daily_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --run-moirai-inference --moirai-model {args.moirai_model}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best_mom={best_mom['arm_id']} "
        f"moirai2={probe.get('status')} pooled={moirai_pooled}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
