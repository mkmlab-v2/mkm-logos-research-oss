#!/usr/bin/env python3
"""[HYPO] RQ-025 TimesFM 2.5 XReg + flow/FRED covariates on blocked WF OOS."""

from __future__ import annotations

import argparse
import csv
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
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_WIDE = ROOT / "reports/rq025_flow_fred_wide_join_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_timesfm25_kospi_xreg_wf_shadow_v1_latest.json"
DEFAULT_MODE_AB = ROOT / "reports/rq025_timesfm25_xreg_mode_ab_compare_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_ZERO = ROOT / "reports/rq025_timesfm25_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_FLOW_CLASSICAL = ROOT / "reports/rq025_kospi_flow_fred_covariate_wf_shadow_v1_latest.json"
SCHEMA = "rq025_timesfm25_kospi_xreg_wf_shadow_v1"


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


def _load_flow_csv(path: Path) -> dict[str, dict[str, float]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, float] = {}
            for col in ("foreign_net_buy", "institution_net_buy"):
                try:
                    entry[col] = float(row.get(col) or 0.0)
                except (TypeError, ValueError):
                    entry[col] = 0.0
            out[dk] = entry
    return out


def _load_wide_join(path: Path) -> dict[str, dict[str, Any]]:
    doc = _load_json(path)
    if not doc:
        return {}
    rows = doc.get("rows_hybrid_kospi_252d") or []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        dk = str(row.get("eval_date") or "")[:10]
        if len(dk) != 10:
            continue
        out[dk] = row
    return out


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


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


def _flow_val(flow: dict[str, dict[str, float]], date: str, col: str) -> float | None:
    row = flow.get(date)
    if not row:
        return None
    try:
        return float(row.get(col) or 0.0)
    except (TypeError, ValueError):
        return None


def _macro_gradient(wide: dict[str, dict[str, Any]], date: str) -> float | None:
    macro = (wide.get(date) or {}).get("macro")
    if not isinstance(macro, dict):
        return None
    try:
        return float(macro.get("gradient"))
    except (TypeError, ValueError):
        return None


def _build_dynamic_covariates(
    dates: list[str],
    *,
    ctx_start: int,
    i: int,
    flow: dict[str, dict[str, float]],
    wide: dict[str, dict[str, Any]],
    cov_cols: tuple[str, ...],
) -> dict[str, list[float]] | None:
    ctx_dates = dates[ctx_start:i]
    if len(ctx_dates) < 2:
        return None
    lag_date = dates[i - 1]
    out: dict[str, list[float]] = {}
    for col in cov_cols:
        if col in ("foreign_net_buy", "institution_net_buy"):
            vals: list[float] = []
            for d in ctx_dates:
                v = _flow_val(flow, d, col)
                if v is None:
                    return None
                vals.append(v)
            hv = _flow_val(flow, lag_date, col)
            if hv is None:
                return None
            vals.append(hv)
            out[col] = vals
        elif col == "macro_gradient":
            vals = []
            for d in ctx_dates:
                g = _macro_gradient(wide, d)
                if g is None:
                    return None
                vals.append(g)
            hg = _macro_gradient(wide, lag_date)
            if hg is None:
                return None
            vals.append(hg)
            out[col] = vals
        else:
            return None
    return out


def _xreg_probe(*, run_inference: bool) -> dict[str, Any]:
    _env_bootstrap()
    if not run_inference:
        return {"status": "skipped_by_flag", "install_hint": "pass --run-xreg-inference"}
    try:
        ok = bool(importlib.util.find_spec("timesfm"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped_error", "error": str(exc)}
    if not ok:
        return {"status": "skipped_missing_timesfm"}
    try:
        from timesfm.utils import xreg_lib  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return {"status": "blocked_missing_xreg_deps", "error": str(exc)}
    return {"status": "xreg_deps_ok"}


def _load_timesfm_xreg_model(
    model_id: str, *, max_context: int, max_horizon: int
) -> tuple[Any | None, dict[str, Any]]:
    _env_bootstrap()
    try:
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
                return_backcast=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return None, {"status": "skipped_load_error", "error": str(exc), "model_id": model_id}
    return model, {"status": "loaded", "model_id": model_id, "return_backcast": True}


def _eval_xreg_arm(
    closes: list[float],
    dates: list[str],
    date_to_idx: dict[str, int],
    flow: dict[str, dict[str, float]],
    wide: dict[str, dict[str, Any]],
    model: Any,
    *,
    arm_id: str,
    cov_cols: tuple[str, ...],
    neutral_bps: float,
    test_dates: list[str],
    max_context: int,
    max_eval_points: int,
    xreg_mode: str,
) -> dict[str, Any]:
    import numpy as np

    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    skipped_missing_cov = 0
    inputs_batch: list[Any] = []
    cov_batch: dict[str, list[list[float]]] = {c: [] for c in cov_cols}
    meta: list[tuple[int, str]] = []

    for d in test_dates:
        if max_eval_points > 0 and len(meta) >= max_eval_points:
            break
        i = date_to_idx.get(d)
        if i is None or i < 2:
            continue
        c0 = closes[i - 1]
        c1 = closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        ctx_start = max(0, i - max_context)
        cov = _build_dynamic_covariates(
            dates,
            ctx_start=ctx_start,
            i=i,
            flow=flow,
            wide=wide,
            cov_cols=cov_cols,
        )
        if cov is None:
            skipped_missing_cov += 1
            continue
        ctx = closes[ctx_start:i]
        inputs_batch.append(np.asarray(ctx, dtype=np.float64))
        for c in cov_cols:
            cov_batch[c].append(cov[c])
        meta.append((i, act))

    if not meta:
        return {
            "directional_hit_rate": None,
            "n_evaluated": 0,
            "price_hits": 0,
            "pred_distribution": dist,
            "skipped_missing_covariates": skipped_missing_cov,
        }

    chunk_size = 32
    point_all: list[Any] = []
    for start in range(0, len(inputs_batch), chunk_size):
        end = start + chunk_size
        chunk_inputs = inputs_batch[start:end]
        chunk_cov = {k: v[start:end] for k, v in cov_batch.items()}
        try:
            point_out, _quant = model.forecast_with_covariates(
                inputs=chunk_inputs,
                dynamic_numerical_covariates=chunk_cov,
                xreg_mode=xreg_mode,
                normalize_xreg_target_per_input=True,
                ridge=0.0,
                force_on_cpu=True,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "directional_hit_rate": None,
                "n_evaluated": 0,
                "price_hits": 0,
                "pred_distribution": dist,
                "error": str(exc),
                "arm_id": arm_id,
            }
        point_all.extend(point_out)

    for j, (i, act) in enumerate(meta):
        c0 = closes[i - 1]
        pred_arr = point_all[j]
        pred_close = float(np.asarray(pred_arr).reshape(-1)[0])
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
        "skipped_missing_covariates": skipped_missing_cov,
        "covariate_cols": list(cov_cols),
        "xreg_mode": xreg_mode,
    }


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


def _aggregate_pred_dist(folds: list[dict[str, Any]]) -> dict[str, int]:
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    for f in folds:
        pd = f.get("pred_distribution") or {}
        for k in ("bull", "bear", "neutral"):
            dist[k] = dist.get(k, 0) + int(pd.get(k) or 0)
    return dist


def main(argv: list[str] | None = None) -> int:
    _env_bootstrap()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-xreg-inference", action="store_true")
    ap.add_argument("--timesfm-model", default="google/timesfm-2.5-200m-pytorch")
    ap.add_argument("--timesfm-max-context", type=int, default=256)
    ap.add_argument("--timesfm-max-horizon", type=int, default=4)
    ap.add_argument("--timesfm-max-eval-points", type=int, default=0)
    ap.add_argument(
        "--xreg-mode",
        default="xreg + timesfm",
        choices=["xreg + timesfm", "timesfm + xreg"],
    )
    ap.add_argument(
        "--run-both-xreg-modes",
        action="store_true",
        help="Run both xreg modes in one pass (model load once); ignores single --xreg-mode.",
    )
    ap.add_argument("--mode-ab-output", type=Path, default=DEFAULT_MODE_AB)
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
    flow = _load_flow_csv(args.flow_csv)
    wide = _load_wide_join(args.wide_join_json)
    folds = _blocked_folds(dates, args.n_folds)

    xreg_arms: list[tuple[str, tuple[str, ...]]] = [
        ("timesfm25_xreg_flow_foreign", ("foreign_net_buy",)),
        ("timesfm25_xreg_flow_fred", ("foreign_net_buy", "macro_gradient")),
    ]
    xreg_modes = ["xreg + timesfm", "timesfm + xreg"] if args.run_both_xreg_modes else [args.xreg_mode]
    arm_fold_rows: dict[tuple[str, str], list[dict[str, Any]]] = {
        (aid, mode): [] for aid, _ in xreg_arms for mode in xreg_modes
    }

    probe = _xreg_probe(run_inference=args.run_xreg_inference)
    model: Any | None = None
    if args.run_xreg_inference and probe.get("status") == "xreg_deps_ok":
        model, load_meta = _load_timesfm_xreg_model(
            args.timesfm_model,
            max_context=args.timesfm_max_context,
            max_horizon=args.timesfm_max_horizon,
        )
        probe = {**probe, **load_meta}

    if model is not None:
        for fi, (_train, test) in enumerate(folds):
            for xreg_mode in xreg_modes:
                for arm_id, cov_cols in xreg_arms:
                    m = _eval_xreg_arm(
                        closes,
                        dates,
                        date_to_idx,
                        flow,
                        wide,
                        model,
                        arm_id=arm_id,
                        cov_cols=cov_cols,
                        neutral_bps=args.neutral_bps,
                        test_dates=test,
                        max_context=args.timesfm_max_context,
                        max_eval_points=args.timesfm_max_eval_points,
                        xreg_mode=xreg_mode,
                    )
                    arm_fold_rows[(arm_id, xreg_mode)].append(
                        {"fold": fi, "test_dates": [test[0], test[-1]], **m}
                    )
    elif args.run_xreg_inference:
        for fi, (_train, test) in enumerate(folds):
            for xreg_mode in xreg_modes:
                for arm_id, _ in xreg_arms:
                    arm_fold_rows[(arm_id, xreg_mode)].append(
                        {
                            "fold": fi,
                            "test_dates": [test[0], test[-1]],
                            "directional_hit_rate": None,
                            "n_evaluated": 0,
                            "note": probe.get("status"),
                        }
                    )

    arms_out: list[dict[str, Any]] = []
    for xreg_mode in xreg_modes:
        for arm_id, cov_cols in xreg_arms:
            folds_for_arm = arm_fold_rows[(arm_id, xreg_mode)]
            arms_out.append(
                {
                    "arm_id": arm_id,
                    "model": args.timesfm_model,
                    "protocol": "blocked_walkforward_test_only_xreg",
                    "covariate_cols": list(cov_cols),
                    "xreg_mode": xreg_mode,
                    "causal_horizon_covariate": "lag1_flow_or_macro",
                    "timesfm_probe": probe if xreg_mode == xreg_modes[0] else None,
                    **_aggregate(folds_for_arm),
                    "folds": folds_for_arm,
                }
            )

    wf = _load_json(DEFAULT_WF)
    zero = _load_json(DEFAULT_ZERO)
    flow_class = _load_json(DEFAULT_FLOW_CLASSICAL)
    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    zero_hr = ((zero or {}).get("timesfm25_zero_shot_summary") or {}).get("pooled_test_directional_hit_rate")
    flow_fake_hr = ((flow_class or {}).get("best_covariate_arm") or {}).get("pooled_test_directional_hit_rate")
    best_xreg = max(arms_out, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))

    mode_ab_summary: dict[str, Any] | None = None
    if len(xreg_modes) > 1:
        by_mode: dict[str, list[dict[str, Any]]] = {}
        for arm in arms_out:
            by_mode.setdefault(str(arm.get("xreg_mode")), []).append(arm)
        mode_ab_summary = {}
        for mode, mode_arms in by_mode.items():
            best_mode_arm = max(mode_arms, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))
            mode_ab_summary[mode] = {
                "best_arm_id": best_mode_arm["arm_id"],
                "pooled_test_directional_hit_rate": best_mode_arm.get("pooled_test_directional_hit_rate"),
                "mean_test_directional_hit_rate": best_mode_arm.get("mean_test_directional_hit_rate"),
            }
        default_mode = "xreg + timesfm"
        alt_mode = "timesfm + xreg"
        d_pooled = mode_ab_summary.get(alt_mode, {}).get("pooled_test_directional_hit_rate")
        b_pooled = mode_ab_summary.get(default_mode, {}).get("pooled_test_directional_hit_rate")
        if d_pooled is not None and b_pooled is not None:
            mode_ab_summary["delta_pp_alt_minus_default"] = round((d_pooled - b_pooled) * 100, 2)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "track_a_mutated": False,
        "window": {
            "eval_days": args.eval_days,
            "date_from": dates[0],
            "date_to": dates[-1],
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
        },
        "blocked_walkforward_test_only": {"arms": arms_out},
        "xreg_modes_run": xreg_modes,
        "mode_ab_summary": mode_ab_summary,
        "best_xreg_arm": {
            "arm_id": best_xreg["arm_id"],
            "pooled_test_directional_hit_rate": best_xreg.get("pooled_test_directional_hit_rate"),
            "mean_test_directional_hit_rate": best_xreg.get("mean_test_directional_hit_rate"),
        },
        "compare_pointers": {
            "wf_majority_pooled_hr": majority_hr,
            "timesfm25_zero_shot_pooled_hr": zero_hr,
            "flow_foreign_lag1_classical_pooled_hr": flow_fake_hr,
            "flow_classical_caveat": "100% bull straw-man; not promotion evidence",
        },
        "interpretation_ko": [
            "XReg arm = TimesFM 2.5 + dynamic flow/FRED covariates; horizon covariate lag1.",
            f"best xreg pooled={best_xreg.get('pooled_test_directional_hit_rate')} ({best_xreg['arm_id']}).",
            f"vs zero-shot={zero_hr}; vs WF majority={majority_hr}.",
            "flow classical 65.1% straw-man과 별개 — XReg는 close 잔차 회귀+TimesFM.",
            "Track A·headline·live 자동 교체 없음.",
        ],
        "reproduce": (
            f"py scripts/run_rq025_timesfm25_kospi_xreg_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --run-xreg-inference"
            + (" --run-both-xreg-modes" if args.run_both_xreg_modes else f' --xreg-mode "{args.xreg_mode}"')
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if mode_ab_summary is not None:
        ab_out = {
            "schema": "rq025_timesfm25_xreg_mode_ab_compare_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "rq_id": "RQ-025",
            "pointer": str(args.output.relative_to(ROOT)).replace("\\", "/"),
            "compare_pointers": out["compare_pointers"],
            "mode_ab_summary": mode_ab_summary,
            "arms_by_mode": {
                mode: [
                    {
                        "arm_id": a["arm_id"],
                        "pooled_test_directional_hit_rate": a.get("pooled_test_directional_hit_rate"),
                        "mean_test_directional_hit_rate": a.get("mean_test_directional_hit_rate"),
                        "pred_distribution_pooled": _aggregate_pred_dist(a.get("folds") or []),
                    }
                    for a in arms_out
                    if a.get("xreg_mode") == mode
                ]
                for mode in xreg_modes
            },
            "interpretation_ko": [
                "XReg mode A/B: xreg+timesfm(기본) vs timesfm+xreg(잔차 회귀 순서).",
                f"delta_pp_alt_minus_default={mode_ab_summary.get('delta_pp_alt_minus_default')}pp.",
                "WF majority·zero-shot 대비는 compare_pointers 참조.",
                "Track A·headline·live 자동 교체 없음.",
            ],
            "reproduce": out["reproduce"],
        }
        args.mode_ab_output.parent.mkdir(parents=True, exist_ok=True)
        args.mode_ab_output.write_text(json.dumps(ab_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best={best_xreg['arm_id']} "
        f"pooled={best_xreg.get('pooled_test_directional_hit_rate')} status={probe.get('status')}"
        + (f" mode_ab={args.mode_ab_output.name}" if mode_ab_summary else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
