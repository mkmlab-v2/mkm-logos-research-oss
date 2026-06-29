#!/usr/bin/env python3
"""[HYPO] RQ-025 TimesFM 2.5 KOSPI daily walk-forward shadow (B-track, research_only)."""

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
DEFAULT_OUT = ROOT / "reports/rq025_timesfm25_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_CHRONOS2 = ROOT / "reports/rq025_chronos2_kospi_daily_wf_shadow_v1_latest.json"
SCHEMA = "rq025_timesfm25_kospi_daily_wf_shadow_v1"


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


def _timesfm_probe(*, run_inference: bool, model_id: str) -> dict[str, Any]:
    _env_bootstrap()
    if not run_inference:
        return {
            "status": "skipped_by_flag",
            "install_hint": "pass --run-timesfm-inference",
        }
    try:
        ok = bool(importlib.util.find_spec("timesfm"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped_error", "error": str(exc)}
    if not ok:
        return {
            "status": "skipped_missing_dependency",
            "install_hint": "pip install -e vendor/timesfm[torch] (see vendor/timesfm README)",
            "model_id": model_id,
        }
    return {"status": "dependency_ok", "model_id": model_id}


def _load_timesfm_model(model_id: str, *, max_context: int, max_horizon: int) -> tuple[Any | None, dict[str, Any]]:
    _env_bootstrap()
    try:
        import numpy as np  # noqa: F401
        import timesfm
        import torch
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_import_error", "error": str(exc)}
    try:
        torch.set_float32_matmul_precision("high")
        model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(model_id)
        model.compile(
            timesfm.ForecastConfig(
                max_context=max_context,
                max_horizon=max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_load_error", "error": str(exc), "model_id": model_id}
    return model, {"status": "loaded", "model_id": model_id, "max_context": max_context}


def _eval_timesfm_arm(
    closes: list[float],
    date_to_idx: dict[str, int],
    model: Any,
    *,
    neutral_bps: float,
    test_dates: list[str],
    max_context: int,
    max_eval_points: int,
) -> dict[str, Any]:
    import numpy as np

    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    contexts: list[Any] = []
    meta: list[tuple[int, str, str]] = []

    for d in test_dates:
        if max_eval_points > 0 and len(contexts) >= max_eval_points:
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
        if max_context > 0 and len(ctx) > max_context:
            ctx = ctx[-max_context:]
        if len(ctx) < 2:
            continue
        contexts.append(np.asarray(ctx, dtype=np.float64))
        meta.append((i, act, d))

    if not contexts:
        return {
            "directional_hit_rate": None,
            "n_evaluated": 0,
            "price_hits": 0,
            "pred_distribution": dist,
        }

    point_forecast, _quant = model.forecast(horizon=1, inputs=contexts)
    for j, (i, act, _d) in enumerate(meta):
        c0 = closes[i - 1]
        pred_close = float(point_forecast[j, 0])
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
    ap.add_argument("--run-timesfm-inference", action="store_true")
    ap.add_argument("--timesfm-model", default="google/timesfm-2.5-200m-pytorch")
    ap.add_argument("--timesfm-max-context", type=int, default=256)
    ap.add_argument("--timesfm-max-horizon", type=int, default=4)
    ap.add_argument("--timesfm-max-eval-points", type=int, default=0)
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
    arm_fold_rows["timesfm25_zero_shot"] = []

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

    probe = _timesfm_probe(run_inference=args.run_timesfm_inference, model_id=args.timesfm_model)
    model: Any | None = None
    if args.run_timesfm_inference and probe.get("status") == "dependency_ok":
        model, load_meta = _load_timesfm_model(
            args.timesfm_model,
            max_context=args.timesfm_max_context,
            max_horizon=args.timesfm_max_horizon,
        )
        probe = {**probe, **load_meta}

    if model is not None:
        for fi, (_train, test) in enumerate(folds):
            m = _eval_timesfm_arm(
                closes,
                date_to_idx,
                model,
                neutral_bps=args.neutral_bps,
                test_dates=test,
                max_context=args.timesfm_max_context,
                max_eval_points=args.timesfm_max_eval_points,
            )
            arm_fold_rows["timesfm25_zero_shot"].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})
    elif args.run_timesfm_inference:
        for fi, (_train, test) in enumerate(folds):
            arm_fold_rows["timesfm25_zero_shot"].append(
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
        arms_out.append(
            {
                "arm_id": arm_id,
                "model": f"classical_momentum_{lb}d",
                "protocol": "blocked_walkforward_test_only",
                "lookback_days": lb,
                **_aggregate(arm_fold_rows[arm_id]),
                "folds": arm_fold_rows[arm_id],
            }
        )

    arms_out.append(
        {
            "arm_id": "timesfm25_zero_shot",
            "model": args.timesfm_model,
            "protocol": "blocked_walkforward_test_only",
            "timesfm_probe": probe,
            "max_context": args.timesfm_max_context,
            **_aggregate(arm_fold_rows["timesfm25_zero_shot"]),
            "folds": arm_fold_rows["timesfm25_zero_shot"],
        }
    )

    wf_compare = _load_json(DEFAULT_WF_COMPARE)
    c2 = _load_json(DEFAULT_CHRONOS2)
    best_mom = max(
        (a for a in arms_out if a["arm_id"].startswith("mom_")),
        key=lambda a: (a.get("mean_test_directional_hit_rate") or -1.0),
    )
    tfm_arm = next((a for a in arms_out if a["arm_id"] == "timesfm25_zero_shot"), None)

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
        "timesfm25_zero_shot_summary": {
            "status": probe.get("status"),
            "mean_test_directional_hit_rate": (tfm_arm or {}).get("mean_test_directional_hit_rate"),
            "pooled_test_directional_hit_rate": (tfm_arm or {}).get("pooled_test_directional_hit_rate"),
        },
        "chronos2_shadow_pointer": str(DEFAULT_CHRONOS2.relative_to(ROOT)).replace("\\", "/"),
        "chronos2_pooled_for_compare": ((c2 or {}).get("chronos2_zero_shot_summary") or {}).get(
            "pooled_test_directional_hit_rate"
        ),
        "wf_holdout_compare_pointer": str(DEFAULT_WF_COMPARE.relative_to(ROOT)).replace("\\", "/"),
        "wf_holdout_best_pooled_arm": (wf_compare or {}).get("best_pooled_arm"),
        "interpretation_ko": [
            "timesfm25 arm = point forecast 1-step close → direction; max_context 기본 256.",
            "install: pip install -e vendor/timesfm[torch] (git clone vendor/timesfm).",
            "beat target = WF majority pooled 63.2%; chronos2 pooled 52.7%.",
            "Track A·headline·live 자동 교체 없음.",
        ],
        "reproduce": (
            f"py scripts/run_rq025_timesfm25_kospi_daily_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --run-timesfm-inference --timesfm-model {args.timesfm_model}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best_mom={best_mom['arm_id']} "
        f"timesfm_pooled={(tfm_arm or {}).get('pooled_test_directional_hit_rate')} "
        f"status={probe.get('status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
