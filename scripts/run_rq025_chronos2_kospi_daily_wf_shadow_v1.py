#!/usr/bin/env python3
"""[HYPO] RQ-025 Chronos-2 KOSPI daily walk-forward shadow (B-track, research_only).

Blocked chronological WF on KOSPI daily direction. When ``amazon/chronos-2`` is not
installed locally, records classical momentum baselines only and marks chronos2 arm
``skipped_missing_dependency`` — no Track A / headline mutation.
"""

from __future__ import annotations

import argparse
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
DEFAULT_OUT = ROOT / "reports/rq025_chronos2_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_DUAL_LANE = ROOT / "reports/kospi_prophecy_operational_dual_lane_v1_latest.json"
DEFAULT_CHRONOS_COMPARE = ROOT / "reports/chronos_kospi_holdout2026_vs_frozen_compare_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
SCHEMA = "rq025_chronos2_kospi_daily_wf_shadow_v1"
VALID = {"bull", "bear", "neutral"}


def _chronos_env_bootstrap() -> None:
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
    dates: list[str],
    date_to_idx: dict[str, int],
    closes: list[float],
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


def _chronos2_probe(*, run_inference: bool, model_id: str, device: str) -> dict[str, Any]:
    _chronos_env_bootstrap()
    try:
        import importlib.util

        ok = bool(importlib.util.find_spec("chronos"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped_error", "error": str(exc)}
    if not ok:
        return {
            "status": "skipped_missing_dependency",
            "install_hint": "pip install chronos-forecasting (GPU optional); model amazon/chronos-2",
        }
    if not run_inference:
        return {
            "status": "skipped_by_flag",
            "install_hint": "pass --run-chronos-inference to score chronos2_zero_shot arm",
        }
    return {"status": "dependency_ok", "model_id": model_id, "device": device}


def _load_chronos2_pipeline(model_id: str, device: str) -> tuple[Any | None, dict[str, Any]]:
    _chronos_env_bootstrap()
    try:
        from chronos import Chronos2Pipeline
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_import_error", "error": str(exc)}
    try:
        pipeline = Chronos2Pipeline.from_pretrained(model_id, device_map=device)
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_load_error", "error": str(exc), "model_id": model_id}
    return pipeline, {"status": "loaded", "model_id": model_id, "device": device}


def _chronos2_median_next_close(pipeline: Any, context_values: list[float], *, context_length: int) -> float | None:
    import torch

    ctx_vals = context_values
    if context_length > 0 and len(ctx_vals) > context_length:
        ctx_vals = ctx_vals[-context_length:]
    if len(ctx_vals) < 2:
        return None
    ctx = torch.tensor(ctx_vals, dtype=torch.float32)
    out = pipeline.predict([ctx], prediction_length=1, context_length=context_length or None)
    pred = out[0]
    if pred.ndim == 3:
        # (n_variates, n_quantiles, horizon)
        med_idx = pred.shape[1] // 2
        return float(pred[0, med_idx, 0].item())
    if pred.ndim == 2:
        med_idx = pred.shape[0] // 2
        return float(pred[med_idx, 0].item())
    return None


def _eval_chronos2_arm(
    closes: list[float],
    date_to_idx: dict[str, int],
    pipeline: Any,
    *,
    neutral_bps: float,
    test_dates: list[str],
    context_length: int,
    max_eval_points: int,
) -> dict[str, Any]:
    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    scored = 0
    for d in test_dates:
        if max_eval_points > 0 and scored >= max_eval_points:
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
        pred_close = _chronos2_median_next_close(pipeline, closes[:i], context_length=context_length)
        if pred_close is None:
            continue
        pred = _actual_direction((pred_close - c0) / c0, neutral_bps)
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        scored += 1
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--eval-days", type=int, default=252, help="Trailing calendar rows for WF pool")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-chronos-inference", action="store_true", help="Load amazon/chronos-2 and score zero-shot arm")
    ap.add_argument("--chronos-model", default="amazon/chronos-2")
    ap.add_argument("--chronos-device", default="cpu")
    ap.add_argument("--chronos-context-length", type=int, default=256)
    ap.add_argument(
        "--chronos-max-eval-points",
        type=int,
        default=0,
        help="Cap scored test points per fold (0 = all)",
    )
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
    mom_arms = [
        ("mom_1d", 1),
        ("mom_5d", 5),
        ("mom_20d", 20),
    ]
    arm_fold_rows: dict[str, list[dict[str, Any]]] = {aid: [] for aid, _ in mom_arms}
    arm_fold_rows["chronos2_zero_shot"] = []

    for fi, (_train, test) in enumerate(folds):
        for arm_id, lb in mom_arms:
            m = _eval_arm(
                dates,
                date_to_idx,
                closes,
                lookback=lb,
                neutral_bps=args.neutral_bps,
                test_dates=test,
            )
            arm_fold_rows[arm_id].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})

    chronos_probe = _chronos2_probe(
        run_inference=args.run_chronos_inference,
        model_id=args.chronos_model,
        device=args.chronos_device,
    )
    chronos_pipeline: Any | None = None
    chronos_load_meta: dict[str, Any] = {}
    if args.run_chronos_inference and chronos_probe.get("status") == "dependency_ok":
        chronos_pipeline, chronos_load_meta = _load_chronos2_pipeline(args.chronos_model, args.chronos_device)
        chronos_probe = {**chronos_probe, **chronos_load_meta}

    if chronos_pipeline is not None:
        for fi, (_train, test) in enumerate(folds):
            m = _eval_chronos2_arm(
                closes,
                date_to_idx,
                chronos_pipeline,
                neutral_bps=args.neutral_bps,
                test_dates=test,
                context_length=args.chronos_context_length,
                max_eval_points=args.chronos_max_eval_points,
            )
            arm_fold_rows["chronos2_zero_shot"].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})
    elif args.run_chronos_inference:
        for fi, (_train, test) in enumerate(folds):
            arm_fold_rows["chronos2_zero_shot"].append(
                {
                    "fold": fi,
                    "test_dates": [test[0], test[-1]],
                    "directional_hit_rate": None,
                    "n_evaluated": 0,
                    "note": chronos_probe.get("status"),
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

    arms_out.append(
        {
            "arm_id": "chronos2_zero_shot",
            "model": args.chronos_model,
            "protocol": "blocked_walkforward_test_only",
            "chronos_probe": chronos_probe,
            "context_length": args.chronos_context_length,
            **(_aggregate(arm_fold_rows["chronos2_zero_shot"]) if arm_fold_rows["chronos2_zero_shot"] else {}),
            "folds": arm_fold_rows["chronos2_zero_shot"],
        }
    )

    wf_compare = _load_json(DEFAULT_WF_COMPARE)
    dual = _load_json(DEFAULT_DUAL_LANE)
    chronos_legacy = _load_json(DEFAULT_CHRONOS_COMPARE)
    operational_refs = {}
    if dual:
        operational_refs = {
            "frozen_bear_30d": (dual.get("lanes") or {}).get("frozen_bear_panel", {}).get("price_directional_hit_rate"),
            "per_date_causal_30d": (dual.get("lanes") or {}).get("per_date_kospi_causal", {}).get("price_directional_hit_rate"),
            "pointer": str(DEFAULT_DUAL_LANE.relative_to(ROOT)).replace("\\", "/"),
        }

    best_mom = max(
        (a for a in arms_out if a["arm_id"].startswith("mom_")),
        key=lambda a: (a.get("mean_test_directional_hit_rate") or -1.0),
    )
    chronos_arm = next((a for a in arms_out if a["arm_id"] == "chronos2_zero_shot"), None)

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
        },
        "chronos2_zero_shot_summary": {
            "status": chronos_probe.get("status"),
            "mean_test_directional_hit_rate": (chronos_arm or {}).get("mean_test_directional_hit_rate"),
            "pooled_test_directional_hit_rate": (chronos_arm or {}).get("pooled_test_directional_hit_rate"),
        },
        "wf_holdout_compare_pointer": str(DEFAULT_WF_COMPARE.relative_to(ROOT)).replace("\\", "/")
        if wf_compare
        else None,
        "wf_holdout_best_pooled_arm": (wf_compare or {}).get("best_pooled_arm"),
        "operational_lane_compare_30d": operational_refs,
        "legacy_chronos_monthly_poc_pointer": str(DEFAULT_CHRONOS_COMPARE.relative_to(ROOT)).replace("\\", "/")
        if chronos_legacy
        else None,
        "interpretation_ko": [
            "mom_* arms = blocked WF OOS test blocks only (252d pool default).",
            "operational 30d frozen/per-date는 in-sample·다른 프로토콜 — 직접 우열 단정 금지.",
            "chronos2 arm = median quantile 1-step close → direction; context_length 기본 256.",
            "Windows: TRANSFORMERS_NO_TF=1 권장(numpy/tf 충돌 회피). Track A·headline 자동 교체 없음.",
        ],
        "reproduce": (
            f"py scripts/run_rq025_chronos2_kospi_daily_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --run-chronos-inference --chronos-model {args.chronos_model}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best_mom={best_mom['arm_id']} "
        f"mean={best_mom.get('mean_test_directional_hit_rate')} chronos2={chronos_probe.get('status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
