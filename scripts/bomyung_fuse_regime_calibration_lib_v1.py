#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regime-stratified bomyung fuse calibration (B-track)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.build_btrack_prophecy_score_from_ohlcv import (
    _daily_return,
    _row_pair_for_eval_date,
)
from scripts.ijeoma_theory_market_fusion_holdout_lib_v1 import split_dates
from scripts.ijeoma_theory_per_date_fusion_holdout_lib_v1 import (
    DEFAULT_KOSPI,
    DEFAULT_PER_DATE,
    load_ohlc,
    load_per_date_rows,
    predict_per_date_arm,
)
from scripts.jema_os_kernel_v2_market_signal_lib_v1 import (
    GRID_BEST_KERNEL_V2_PARAMS,
    build_kernel_v2_market_signal,
    compute_bomyung_fuse_tripped,
    dominant_constitution,
)

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/final/artifacts/ijeoma_kernel_v2_mdd_safeguard_holdout_prereg_v1_latest.json"

REGIMES = ("calm", "watch", "stress", "crisis")
BASELINE_ARM = "P10_kernel_v2_grid_best"
FUSE_ARMS = ("P8_kernel_v2_bomyung_fuse", "P13_kernel_v2_bomyung_grid_best")


def load_prereg(path: Path = PREREG) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "ijeoma_kernel_v2_mdd_safeguard_holdout_prereg_v1":
        raise ValueError(f"unexpected prereg schema: {doc.get('schema')}")
    return doc


def _fuse_context(row: dict[str, Any]) -> dict[str, Any]:
    sig = build_kernel_v2_market_signal(row, params=GRID_BEST_KERNEL_V2_PARAMS)
    snap = row.get("market_sasang_lens_snapshot")
    snap = snap if isinstance(snap, dict) else {}
    softmax = snap.get("state_vector_sasang_softmax")
    softmax = softmax if isinstance(softmax, dict) else {}
    return {
        "tripped": bool(sig.get("bomyung_fuse_tripped")),
        "regime": str(row.get("regime_hypothesis") or "calm").lower(),
        "dominant_constitution": dominant_constitution(softmax),
        "direction_hint": str(sig.get("direction_hint") or "neutral"),
    }


def _regime_bucket_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_regime: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "tripped": 0})
    by_dom: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "tripped": 0})
    tripped_rows = 0
    for row in rows:
        ctx = _fuse_context(row)
        regime = ctx["regime"] if ctx["regime"] in REGIMES else "other"
        dom = ctx["dominant_constitution"]
        by_regime[regime]["n"] += 1
        by_dom[dom]["n"] += 1
        if ctx["tripped"]:
            tripped_rows += 1
            by_regime[regime]["tripped"] += 1
            by_dom[dom]["tripped"] += 1

    def _rate(block: dict[str, int]) -> float | None:
        n = block.get("n") or 0
        if n == 0:
            return None
        return round((block.get("tripped") or 0) / n, 6)

    regime_out = {
        r: {
            "n_rows": by_regime[r]["n"],
            "tripped_count": by_regime[r]["tripped"],
            "trip_rate": _rate(by_regime[r]),
        }
        for r in sorted(set(list(by_regime.keys()) + list(REGIMES)))
        if by_regime[r]["n"] > 0
    }
    dom_out = {
        d: {
            "n_rows": by_dom[d]["n"],
            "tripped_count": by_dom[d]["tripped"],
            "trip_rate": _rate(by_dom[d]),
        }
        for d in sorted(by_dom.keys())
    }
    n_total = len(rows)
    return {
        "n_rows": n_total,
        "tripped_count": tripped_rows,
        "trip_rate": round(tripped_rows / n_total, 6) if n_total else None,
        "by_regime": regime_out,
        "by_dominant_constitution": dom_out,
    }


def _divergence_stats(
    rows: list[dict[str, Any]],
    *,
    baseline_arm: str = BASELINE_ARM,
    fuse_arm: str = "P13_kernel_v2_bomyung_grid_best",
) -> dict[str, Any]:
    diverged = 0
    diverged_on_trip = 0
    trip_count = 0
    by_regime: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "diverged": 0, "tripped": 0}
    )
    for row in rows:
        ctx = _fuse_context(row)
        regime = ctx["regime"] if ctx["regime"] in REGIMES else "other"
        p10 = predict_per_date_arm(baseline_arm, row)
        pf = predict_per_date_arm(fuse_arm, row)
        by_regime[regime]["n"] += 1
        if ctx["tripped"]:
            trip_count += 1
            by_regime[regime]["tripped"] += 1
        if p10 != pf:
            diverged += 1
            by_regime[regime]["diverged"] += 1
            if ctx["tripped"]:
                diverged_on_trip += 1

    n = len(rows)
    return {
        "baseline_arm": baseline_arm,
        "fuse_arm": fuse_arm,
        "n_rows": n,
        "prediction_divergence_count": diverged,
        "prediction_divergence_rate": round(diverged / n, 6) if n else None,
        "fuse_trip_count": trip_count,
        "divergence_on_trip_count": diverged_on_trip,
        "divergence_explained_by_trip_rate": (
            round(diverged_on_trip / diverged, 6) if diverged else None
        ),
        "by_regime": {
            r: {
                "n_rows": by_regime[r]["n"],
                "diverged_count": by_regime[r]["diverged"],
                "tripped_count": by_regime[r]["tripped"],
                "divergence_rate": (
                    round(by_regime[r]["diverged"] / by_regime[r]["n"], 6)
                    if by_regime[r]["n"]
                    else None
                ),
            }
            for r in sorted(by_regime.keys())
        },
    }


def _tripped_day_pnl_proxy(
    rows: list[dict[str, Any]],
    ohlc: list[dict[str, Any]],
    *,
    arm: str,
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    tripped_rets: list[float] = []
    calm_rets: list[float] = []
    for row in rows:
        d = str(row.get("eval_date") or "")[:10]
        pair = _row_pair_for_eval_date(ohlc, d)
        if pair is None:
            continue
        ret = _daily_return(pair[0], pair[1])
        pred = predict_per_date_arm(arm, row)
        pos = 0.0 if pred == "neutral" else (1.0 if pred == "bull" else -1.0)
        strat = pos * ret
        if compute_bomyung_fuse_tripped(row):
            tripped_rets.append(strat)
        else:
            calm_rets.append(strat)

    def _summary(rets: list[float]) -> dict[str, Any]:
        if not rets:
            return {"n_days": 0, "mean_return": None, "worst_day": None}
        return {
            "n_days": len(rets),
            "mean_return": round(sum(rets) / len(rets), 6),
            "worst_day": round(min(rets), 6),
        }

    return {
        "arm": arm,
        "fuse_tripped_days": _summary(tripped_rets),
        "fuse_not_tripped_days": _summary(calm_rets),
    }


def evaluate_bomyung_fuse_regime_calibration(
    *,
    per_date_path: Path = DEFAULT_PER_DATE,
    kospi_csv: Path = DEFAULT_KOSPI,
    holdout_days: int = 72,
    fold_holdout_days: int = 72,
    n_folds: int = 3,
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    prereg = load_prereg()
    fuse_contract = prereg.get("fuse_contract_v1") or {}
    rows = load_per_date_rows(per_date_path)
    if not rows:
        raise FileNotFoundError(f"missing or empty per-date jsonl: {per_date_path}")

    ohlc = load_ohlc(kospi_csv)
    all_dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    train_dates, holdout_dates = split_dates(all_dates, holdout_days)
    holdout_set = set(holdout_dates)
    holdout_rows = [r for r in rows if str(r.get("eval_date") or "")[:10] in holdout_set]

    confirm_start = len(all_dates) - holdout_days
    wf_pool_end = confirm_start
    fold_summaries: list[dict[str, Any]] = []
    for fold_idx in range(n_folds):
        end_idx = wf_pool_end - fold_idx * fold_holdout_days
        start_idx = end_idx - fold_holdout_days
        if start_idx < fold_holdout_days:
            break
        fold_dates = set(all_dates[start_idx:end_idx])
        fold_rows = [r for r in rows if str(r.get("eval_date") or "")[:10] in fold_dates]
        div = _divergence_stats(fold_rows)
        fold_summaries.append(
            {
                "fold_id": f"WF{fold_idx + 1}",
                "holdout_date_from": all_dates[start_idx],
                "holdout_date_to": all_dates[end_idx - 1],
                "regime_trip_stats": _regime_bucket_stats(fold_rows),
                "p10_vs_p13_divergence": div,
            }
        )

    full_stats = _regime_bucket_stats(rows)
    holdout_stats = _regime_bucket_stats(holdout_rows)
    divergence = _divergence_stats(holdout_rows)
    pnl_p10 = _tripped_day_pnl_proxy(holdout_rows, ohlc, arm=BASELINE_ARM, neutral_bps=neutral_bps)
    pnl_p13 = _tripped_day_pnl_proxy(holdout_rows, ohlc, arm="P13_kernel_v2_bomyung_grid_best")

    crisis_trip = (holdout_stats.get("by_regime") or {}).get("crisis") or {}
    stress_trip = (holdout_stats.get("by_regime") or {}).get("stress") or {}
    calm_watch = (holdout_stats.get("by_regime") or {}).get("calm") or {}
    watch_trip = (holdout_stats.get("by_regime") or {}).get("watch") or {}

    contract_confirmed = bool(
        (crisis_trip.get("trip_rate") or 0) > (calm_watch.get("trip_rate") or 0)
        or (stress_trip.get("trip_rate") or 0) > (watch_trip.get("trip_rate") or 0)
        or (divergence.get("divergence_explained_by_trip_rate") or 0) >= 0.8
    )

    if contract_confirmed:
        verdict = (
            "fuse 계약 확인: crisis/stress trip_rate > calm/watch 또는 "
            "divergence가 trip으로 설명됨 (위기 전용 kill-switch · B-track)"
        )
    else:
        verdict = "fuse regime calibration — 계약 재검토 필요 (B-track)"

    try:
        per_date_rel = str(per_date_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        per_date_rel = str(per_date_path)

    return {
        "schema": "bomyung_fuse_regime_calibration_v1",
        "prereg_pointer": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "hypothesis_class": "HYPO",
        "fuse_contract_v1": fuse_contract,
        "per_date_jsonl": per_date_rel,
        "n_per_date_rows": len(rows),
        "full_sample": full_stats,
        "holdout_tail": holdout_stats,
        "holdout_p10_vs_p13_divergence": divergence,
        "holdout_pnl_proxy_by_fuse_state": {
            BASELINE_ARM: pnl_p10,
            "P13_kernel_v2_bomyung_grid_best": pnl_p13,
        },
        "walkforward_fold_summaries": fold_summaries,
        "contract_validation": {
            "mode": fuse_contract.get("mode", "crisis_conditional_kill_switch"),
            "contract_confirmed": contract_confirmed,
            "holdout_crisis_trip_rate": crisis_trip.get("trip_rate"),
            "holdout_calm_trip_rate": calm_watch.get("trip_rate"),
            "holdout_stress_trip_rate": stress_trip.get("trip_rate"),
            "holdout_watch_trip_rate": watch_trip.get("trip_rate"),
            "wf_fold_divergence_rates": [
                (f.get("p10_vs_p13_divergence") or {}).get("prediction_divergence_rate")
                for f in fold_summaries
            ],
        },
        "hypothesis_supported": contract_confirmed,
        "verdict_ko": verdict,
        "repro_command": "py scripts/run_bomyung_fuse_regime_calibration_v1.py",
    }
