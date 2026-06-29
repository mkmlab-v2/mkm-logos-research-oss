#!/usr/bin/env python3
"""[HYPO] RQ-025 flow/FRED covariate direction arms on blocked WF (classical shadow)."""

from __future__ import annotations

import argparse
import csv
import json
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
DEFAULT_OUT = ROOT / "reports/rq025_kospi_flow_fred_covariate_wf_shadow_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_TIMESFM = ROOT / "reports/rq025_timesfm25_kospi_daily_wf_shadow_v1_latest.json"
SCHEMA = "rq025_kospi_flow_fred_covariate_wf_shadow_v1"


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
            for col in ("foreign_net_buy", "institution_net_buy", "program_net_buy"):
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


def _sign_direction(value: float, neutral_bps: float) -> str:
    if value > 0:
        return "bull"
    if value < 0:
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


def _pred_flow_foreign_lag1(
    dates: list[str],
    date_to_idx: dict[str, int],
    flow: dict[str, dict[str, float]],
    idx: int,
    neutral_bps: float,
) -> str | None:
    if idx < 1:
        return None
    lag_date = dates[idx - 1]
    row = flow.get(lag_date)
    if not row:
        return None
    return _sign_direction(float(row.get("foreign_net_buy") or 0.0), neutral_bps)


def _pred_flow_institution_lag1(
    dates: list[str],
    flow: dict[str, dict[str, float]],
    idx: int,
    neutral_bps: float,
) -> str | None:
    if idx < 1:
        return None
    lag_date = dates[idx - 1]
    row = flow.get(lag_date)
    if not row:
        return None
    return _sign_direction(float(row.get("institution_net_buy") or 0.0), neutral_bps)


def _pred_macro_gradient_lag1(
    dates: list[str],
    wide: dict[str, dict[str, Any]],
    idx: int,
    neutral_bps: float,
) -> str | None:
    if idx < 1:
        return None
    lag_date = dates[idx - 1]
    row = wide.get(lag_date) or {}
    macro = row.get("macro") if isinstance(row.get("macro"), dict) else {}
    try:
        grad = float(macro.get("gradient"))
    except (TypeError, ValueError):
        return None
    return _sign_direction(grad, neutral_bps)


def _vote_direction(votes: list[str | None]) -> str | None:
    bulls = sum(1 for v in votes if v == "bull")
    bears = sum(1 for v in votes if v == "bear")
    if bulls > bears:
        return "bull"
    if bears > bulls:
        return "bear"
    return None


def _eval_arm(
    *,
    arm_id: str,
    dates: list[str],
    closes: list[float],
    date_to_idx: dict[str, int],
    flow: dict[str, dict[str, float]],
    wide: dict[str, dict[str, Any]],
    neutral_bps: float,
    test_dates: list[str],
) -> dict[str, Any]:
    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    missing_flow = 0
    missing_macro = 0

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

        if arm_id == "flow_foreign_lag1_sign":
            pred = _pred_flow_foreign_lag1(dates, date_to_idx, flow, i, neutral_bps)
            if pred is None:
                missing_flow += 1
                continue
        elif arm_id == "flow_foreign_institution_lag1_vote":
            pred = _vote_direction(
                [
                    _pred_flow_foreign_lag1(dates, date_to_idx, flow, i, neutral_bps),
                    _pred_flow_institution_lag1(dates, flow, i, neutral_bps),
                ]
            )
            if pred is None:
                missing_flow += 1
                continue
        elif arm_id == "macro_lambda_gradient_lag1_sign":
            pred = _pred_macro_gradient_lag1(dates, wide, i, neutral_bps)
            if pred is None:
                missing_macro += 1
                continue
        elif arm_id == "flow_macro_lag1_vote":
            pred = _vote_direction(
                [
                    _pred_flow_foreign_lag1(dates, date_to_idx, flow, i, neutral_bps),
                    _pred_macro_gradient_lag1(dates, wide, i, neutral_bps),
                ]
            )
            if pred is None:
                missing_flow += 1
                missing_macro += 1
                continue
        else:
            continue

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
        "missing_flow_skips": missing_flow,
        "missing_macro_skips": missing_macro,
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


def _xreg_dependency_probe() -> dict[str, Any]:
    try:
        from timesfm.utils import xreg_lib  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked_missing_xreg_deps",
            "error": str(exc),
            "install_hint": "pip install -e 'vendor/timesfm[xreg]' (requires jax; Windows CPU may need jax[cpu])",
            "note_ko": "TimesFM forecast_with_covariates는 본 classical arm과 별도; jax 미설치 시 deferred",
        }
    return {"status": "xreg_deps_ok"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
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

    arm_ids = [
        "flow_foreign_lag1_sign",
        "flow_foreign_institution_lag1_vote",
        "macro_lambda_gradient_lag1_sign",
        "flow_macro_lag1_vote",
    ]
    arm_fold_rows: dict[str, list[dict[str, Any]]] = {aid: [] for aid in arm_ids}

    for fi, (_train, test) in enumerate(folds):
        for arm_id in arm_ids:
            m = _eval_arm(
                arm_id=arm_id,
                dates=dates,
                closes=closes,
                date_to_idx=date_to_idx,
                flow=flow,
                wide=wide,
                neutral_bps=args.neutral_bps,
                test_dates=test,
            )
            arm_fold_rows[arm_id].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})

    arms_out: list[dict[str, Any]] = []
    for arm_id in arm_ids:
        protocol = "lag1_causal_covariate_sign"
        if "macro" in arm_id:
            protocol = "lag1_macro_gradient_sign"
        if "vote" in arm_id:
            protocol = "lag1_covariate_majority_vote"
        arms_out.append(
            {
                "arm_id": arm_id,
                "model": "classical_flow_fred_covariate",
                "protocol": protocol,
                "causal_lag_days": 1,
                **_aggregate(arm_fold_rows[arm_id]),
                "folds": arm_fold_rows[arm_id],
            }
        )

    wf = _load_json(DEFAULT_WF)
    timesfm = _load_json(DEFAULT_TIMESFM)
    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    timesfm_hr = ((timesfm or {}).get("timesfm25_zero_shot_summary") or {}).get(
        "pooled_test_directional_hit_rate"
    )
    best_arm = max(arms_out, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))

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
            "flow_csv": str(args.flow_csv.relative_to(ROOT)).replace("\\", "/"),
            "wide_join_json": str(args.wide_join_json.relative_to(ROOT)).replace("\\", "/"),
            "flow_dates_available": len(flow),
            "wide_dates_available": len(wide),
        },
        "blocked_walkforward_test_only": {"arms": arms_out},
        "best_covariate_arm": {
            "arm_id": best_arm["arm_id"],
            "pooled_test_directional_hit_rate": best_arm.get("pooled_test_directional_hit_rate"),
            "mean_test_directional_hit_rate": best_arm.get("mean_test_directional_hit_rate"),
        },
        "compare_pointers": {
            "wf_majority_pooled_hr": majority_hr,
            "timesfm25_zero_shot_pooled_hr": timesfm_hr,
        },
        "timesfm_xreg_probe": _xreg_dependency_probe(),
        "interpretation_ko": [
            "공변량 arm = 전일 flow/macro sign·vote → 당일 방향; blocked WF OOS only.",
            f"best classical covariate pooled={best_arm.get('pooled_test_directional_hit_rate')} ({best_arm['arm_id']}).",
            f"WF majority pooled={majority_hr}; timesfm25 zero-shot pooled={timesfm_hr}.",
            "TimesFM XReg(forecast_with_covariates)는 jax[xreg] 별도 — 본 산출은 classical shadow.",
            "Track A·headline·live 자동 교체 없음.",
        ],
        "reproduce": (
            f"py scripts/run_rq025_kospi_flow_fred_covariate_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --neutral-bps {args.neutral_bps:g}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best={best_arm['arm_id']} "
        f"pooled={best_arm.get('pooled_test_directional_hit_rate')} xreg={out['timesfm_xreg_probe'].get('status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
