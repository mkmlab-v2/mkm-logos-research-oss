#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MDD / tail-risk safeguard eval for kernel v2 arms (B-track)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_btrack_prophecy_score_from_ohlcv import (
    _daily_return,
    _row_pair_for_eval_date,
)
from scripts.ijeoma_theory_per_date_fusion_holdout_lib_v1 import (
    DEFAULT_KOSPI,
    DEFAULT_PER_DATE,
    build_predictions,
    load_ohlc,
    load_per_date_rows,
)
from scripts.ijeoma_theory_market_fusion_holdout_lib_v1 import split_dates

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/final/artifacts/ijeoma_kernel_v2_mdd_safeguard_holdout_prereg_v1_latest.json"


def load_prereg(path: Path = PREREG) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "ijeoma_kernel_v2_mdd_safeguard_holdout_prereg_v1":
        raise ValueError(f"unexpected prereg schema: {doc.get('schema')}")
    return doc


def _position_from_pred(pred: str, *, position_mode: str = "long_short_proxy") -> float:
    p = str(pred or "neutral").lower()
    if p == "bull":
        return 1.0
    if p == "bear":
        return -1.0 if position_mode == "long_short_proxy" else 0.0
    return 0.0


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def kospi_direction_proxy_metrics(
    pred_by_date: dict[str, str],
    ohlc: list[dict[str, Any]],
    eval_dates: list[str],
    neutral_bps: float = 5.0,
    *,
    position_mode: str = "long_short_proxy",
) -> dict[str, Any]:
    equity = 1.0
    equity_curve = [equity]
    strategy_returns: list[float] = []
    n_active = 0
    n_dates = 0

    for d in eval_dates:
        pred = pred_by_date.get(d)
        if pred is None:
            continue
        pair = _row_pair_for_eval_date(ohlc, d)
        if pair is None:
            continue
        ret = _daily_return(pair[0], pair[1])
        pos = _position_from_pred(pred, position_mode=position_mode)
        n_dates += 1
        if pos != 0.0:
            n_active += 1
        strat_ret = pos * ret
        strategy_returns.append(strat_ret)
        equity *= 1.0 + strat_ret
        equity_curve.append(equity)

    max_dd = _max_drawdown(equity_curve)
    cum_ret = equity - 1.0
    worst_day = min(strategy_returns) if strategy_returns else 0.0
    vol = 0.0
    if len(strategy_returns) > 1:
        mean_r = sum(strategy_returns) / len(strategy_returns)
        var = sum((r - mean_r) ** 2 for r in strategy_returns) / (len(strategy_returns) - 1)
        vol = var**0.5

    return {
        "max_drawdown": round(max_dd, 6),
        "cumulative_return": round(cum_ret, 6),
        "n_dates": n_dates,
        "n_active_days": n_active,
        "worst_day_return": round(worst_day, 6),
        "daily_return_volatility": round(vol, 6),
        "final_equity": round(equity, 6),
    }


def _mdd_reduction_ratio(baseline_mdd: float, arm_mdd: float) -> float:
    if baseline_mdd > 0:
        return (baseline_mdd - arm_mdd) / baseline_mdd
    return 0.0 if arm_mdd <= baseline_mdd else -1.0


def _comparison_block(
    *,
    baseline_arm: str,
    baseline_ho: dict[str, Any],
    arm_ho: dict[str, Any],
    mdd_threshold: float,
    cum_floor: float,
    min_active: int,
) -> dict[str, Any]:
    baseline_mdd = float(baseline_ho.get("max_drawdown") or 0.0)
    baseline_cum = float(baseline_ho.get("cumulative_return") or 0.0)
    arm_mdd = float(arm_ho.get("max_drawdown") or 0.0)
    arm_cum = float(arm_ho.get("cumulative_return") or 0.0)
    n_active = int(arm_ho.get("n_active_days") or 0)
    mdd_reduction = _mdd_reduction_ratio(baseline_mdd, arm_mdd)
    cum_delta = arm_cum - baseline_cum
    return {
        "baseline_arm": baseline_arm,
        "holdout_max_drawdown": arm_mdd,
        "holdout_cumulative_return": arm_cum,
        "delta_cumulative_return_vs_baseline": round(cum_delta, 6),
        "max_drawdown_reduction_ratio_vs_baseline": round(mdd_reduction, 6),
        "n_active_days": n_active,
        "mdd_threshold_met": bool(mdd_reduction >= mdd_threshold and n_active >= min_active),
        "cum_return_floor_met": bool(cum_delta >= cum_floor),
    }


def evaluate_mdd_safeguard_holdout(
    *,
    per_date_path: Path = DEFAULT_PER_DATE,
    kospi_csv: Path = DEFAULT_KOSPI,
    holdout_days: int = 72,
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    prereg = load_prereg()
    proto = prereg.get("holdout_protocol") or {}
    position_mode = str(proto.get("position_mode") or "long_short_proxy")
    arm_ids = list(prereg.get("arms") or [])
    baseline_arm = str(prereg.get("compare_baseline_arm") or "P10_kernel_v2_grid_best")
    challenger_arms = list(prereg.get("challenger_arms") or [])
    crit = prereg.get("success_criteria") or {}
    primary_challenger = str(
        crit.get("primary_challenger_arm") or "P13_kernel_v2_bomyung_grid_best"
    )
    mdd_strict_gte = float(
        crit.get("holdout_max_drawdown_reduction_vs_p10_strict_gte")
        or crit.get("holdout_max_drawdown_reduction_vs_p10_gte")
        or 0.30
    )
    mdd_exploratory_gte = float(
        crit.get("holdout_max_drawdown_reduction_vs_p10_exploratory_gte") or 0.20
    )
    cum_floor = float(crit.get("holdout_cumulative_return_floor_vs_p10") or -0.05)
    min_active = int(crit.get("min_active_days") or 20)

    rows = load_per_date_rows(per_date_path)
    if not rows:
        raise FileNotFoundError(f"missing or empty per-date jsonl: {per_date_path}")

    ohlc = load_ohlc(kospi_csv)
    all_dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    train_dates, holdout_dates = split_dates(all_dates, holdout_days)
    preds = build_predictions(rows, arm_ids)

    per_arm: dict[str, Any] = {}
    for arm in arm_ids:
        tr = kospi_direction_proxy_metrics(
            preds[arm],
            ohlc,
            train_dates,
            neutral_bps,
            position_mode=position_mode,
        )
        ho = kospi_direction_proxy_metrics(
            preds[arm],
            ohlc,
            holdout_dates,
            neutral_bps,
            position_mode=position_mode,
        )
        per_arm[arm] = {"train": tr, "holdout": ho}

    baseline_ho = (per_arm.get(baseline_arm) or {}).get("holdout") or {}
    baseline_mdd = float(baseline_ho.get("max_drawdown") or 0.0)
    baseline_cum = float(baseline_ho.get("cumulative_return") or 0.0)

    comparisons: dict[str, Any] = {}
    for arm in challenger_arms:
        ho = (per_arm.get(arm) or {}).get("holdout") or {}
        strict_cmp = _comparison_block(
            baseline_arm=baseline_arm,
            baseline_ho=baseline_ho,
            arm_ho=ho,
            mdd_threshold=mdd_strict_gte,
            cum_floor=cum_floor,
            min_active=min_active,
        )
        exploratory_cmp = _comparison_block(
            baseline_arm=baseline_arm,
            baseline_ho=baseline_ho,
            arm_ho=ho,
            mdd_threshold=mdd_exploratory_gte,
            cum_floor=cum_floor,
            min_active=min_active,
        )
        comparisons[arm] = {
            **strict_cmp,
            "mdd_strict_met": strict_cmp["mdd_threshold_met"],
            "mdd_exploratory_met": exploratory_cmp["mdd_threshold_met"],
        }

    primary_cmp = comparisons.get(primary_challenger) or {}
    hypothesis_supported = bool(
        primary_cmp.get("mdd_strict_met") and primary_cmp.get("cum_return_floor_met")
    )
    exploratory_supported = bool(
        primary_cmp.get("mdd_exploratory_met") and primary_cmp.get("cum_return_floor_met")
    )

    if hypothesis_supported:
        verdict = (
            f"MDD safeguard strict 통과: {primary_challenger} MDD↓"
            f"{primary_cmp.get('max_drawdown_reduction_ratio_vs_baseline', 0):.1%} vs {baseline_arm} "
            f"(B-track · 승격 아님)"
        )
    elif exploratory_supported:
        verdict = (
            f"MDD safeguard exploratory 통과·strict 미달: {primary_challenger} MDD↓"
            f"{primary_cmp.get('max_drawdown_reduction_ratio_vs_baseline', 0):.1%} "
            f"(WF 확인 권장 · B-track)"
        )
    else:
        verdict = (
            f"MDD safeguard 미달: {primary_challenger} MDD reduction="
            f"{primary_cmp.get('max_drawdown_reduction_ratio_vs_baseline')} "
            f"cumΔ={primary_cmp.get('delta_cumulative_return_vs_baseline')} (B-track)"
        )

    try:
        per_date_rel = str(per_date_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        per_date_rel = str(per_date_path)

    return {
        "schema": "ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1",
        "prereg_pointer": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "hypothesis_class": "HYPO",
        "per_date_jsonl": per_date_rel,
        "n_per_date_rows": len(rows),
        "holdout_protocol": {
            "holdout_days": holdout_days,
            "train_n_dates": len(train_dates),
            "holdout_n_dates": len(holdout_dates),
            "neutral_bps": neutral_bps,
            "position_mode": position_mode,
        },
        "per_arm": per_arm,
        "mdd_comparisons_vs_baseline": comparisons,
        "aggregation": {
            "baseline_arm": baseline_arm,
            "primary_challenger_arm": primary_challenger,
            "baseline_holdout_max_drawdown": baseline_mdd,
            "baseline_holdout_cumulative_return": baseline_cum,
            "required_mdd_reduction_strict": mdd_strict_gte,
            "required_mdd_reduction_exploratory": mdd_exploratory_gte,
            "required_cum_return_floor_vs_baseline": cum_floor,
            "primary_mdd_reduction_ratio": primary_cmp.get("max_drawdown_reduction_ratio_vs_baseline"),
            "primary_cum_delta_vs_baseline": primary_cmp.get("delta_cumulative_return_vs_baseline"),
            "primary_mdd_strict_met": primary_cmp.get("mdd_strict_met"),
            "primary_mdd_exploratory_met": primary_cmp.get("mdd_exploratory_met"),
            "primary_cum_return_floor_met": primary_cmp.get("cum_return_floor_met"),
            "exploratory_supported": exploratory_supported,
        },
        "hypothesis_supported": hypothesis_supported,
        "exploratory_supported": exploratory_supported,
        "verdict_ko": verdict,
        "repro_command": "py scripts/run_ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1.py",
    }


def evaluate_mdd_safeguard_walkforward(
    *,
    per_date_path: Path = DEFAULT_PER_DATE,
    kospi_csv: Path = DEFAULT_KOSPI,
    fold_holdout_days: int = 72,
    n_folds: int = 3,
    confirmatory_holdout_days: int = 72,
    neutral_bps: float = 5.0,
    baseline_arm: str = "P10_kernel_v2_grid_best",
    challenger_arm: str = "P13_kernel_v2_bomyung_grid_best",
    secondary_arm: str = "P8_kernel_v2_bomyung_fuse",
) -> dict[str, Any]:
    prereg = load_prereg()
    proto = prereg.get("holdout_protocol") or {}
    position_mode = str(proto.get("position_mode") or "long_short_proxy")
    crit = prereg.get("success_criteria") or {}
    wf_mdd_gte = float(crit.get("walkforward_mdd_reduction_vs_p10_gte") or 0.15)
    wf_min_folds = int(crit.get("walkforward_min_folds_non_negative_mdd_improvement") or 2)
    confirm_mdd_gte = float(crit.get("confirmatory_mdd_reduction_vs_p10_gte") or 0.20)
    cum_floor = float(crit.get("holdout_cumulative_return_floor_vs_p10") or -0.05)
    min_active = int(crit.get("min_active_days") or 20)

    arm_ids = list(prereg.get("arms") or [])
    arms = (baseline_arm, secondary_arm, challenger_arm)
    for arm in arms:
        if arm not in arm_ids:
            raise ValueError(f"arm not in prereg: {arm}")

    rows = load_per_date_rows(per_date_path)
    if not rows:
        raise FileNotFoundError(f"missing or empty per-date jsonl: {per_date_path}")

    ohlc = load_ohlc(kospi_csv)
    all_dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    if len(all_dates) < confirmatory_holdout_days + fold_holdout_days * n_folds:
        raise ValueError(
            f"insufficient dates for walk-forward: have {len(all_dates)}, "
            f"need {confirmatory_holdout_days + fold_holdout_days * n_folds}"
        )

    confirm_start = len(all_dates) - confirmatory_holdout_days
    confirm_dates = all_dates[confirm_start:]
    wf_pool_end = confirm_start
    preds = build_predictions(rows, arm_ids)

    def _mdd_block(dates: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for arm in arms:
            out[arm] = kospi_direction_proxy_metrics(
                preds[arm],
                ohlc,
                dates,
                neutral_bps,
                position_mode=position_mode,
            )
        return out

    fold_results: list[dict[str, Any]] = []
    wf_improvements: list[float] = []
    for fold_idx in range(n_folds):
        end_idx = wf_pool_end - fold_idx * fold_holdout_days
        start_idx = end_idx - fold_holdout_days
        if start_idx < fold_holdout_days:
            break
        holdout_dates = all_dates[start_idx:end_idx]
        per_arm_mdd = _mdd_block(holdout_dates)
        p10_mdd = float((per_arm_mdd.get(baseline_arm) or {}).get("max_drawdown") or 0.0)
        fold_row: dict[str, Any] = {
            "fold_id": f"WF{fold_idx + 1}",
            "holdout_date_from": holdout_dates[0],
            "holdout_date_to": holdout_dates[-1],
            "holdout_n_dates": len(holdout_dates),
            "per_arm": {},
        }
        for arm in arms:
            ho = per_arm_mdd[arm]
            mdd_reduction = _mdd_reduction_ratio(
                p10_mdd, float(ho.get("max_drawdown") or 0.0)
            )
            arm_block = {"holdout": ho, "mdd_reduction_vs_p10": round(mdd_reduction, 6)}
            if arm != baseline_arm:
                arm_block["mdd_improvement_met"] = bool(mdd_reduction >= wf_mdd_gte)
            fold_row["per_arm"][arm] = arm_block
            if arm == challenger_arm:
                wf_improvements.append(mdd_reduction)
        fold_results.append(fold_row)

    confirm_per_arm = _mdd_block(confirm_dates)
    p10_confirm = confirm_per_arm.get(baseline_arm) or {}
    p10_confirm_mdd = float(p10_confirm.get("max_drawdown") or 0.0)
    p10_confirm_cum = float(p10_confirm.get("cumulative_return") or 0.0)
    confirm_enriched: dict[str, Any] = {}
    for arm in arms:
        ho = confirm_per_arm[arm]
        mdd_reduction = _mdd_reduction_ratio(
            p10_confirm_mdd, float(ho.get("max_drawdown") or 0.0)
        )
        cum_delta = float(ho.get("cumulative_return") or 0.0) - p10_confirm_cum
        confirm_enriched[arm] = {
            "holdout": ho,
            "mdd_reduction_vs_p10": round(mdd_reduction, 6),
            "delta_cumulative_return_vs_p10": round(cum_delta, 6),
            "in_sample_params_risk": arm == baseline_arm,
        }
        if arm == challenger_arm:
            ch_mdd_reduction = mdd_reduction
            ch_cum_delta = cum_delta
            ch_n_active = int(ho.get("n_active_days") or 0)

    wf_non_negative = sum(1 for d in wf_improvements if d >= wf_mdd_gte)
    wf_mean_reduction = sum(wf_improvements) / len(wf_improvements) if wf_improvements else None
    walkforward_pass = bool(len(wf_improvements) >= n_folds and wf_non_negative >= wf_min_folds)
    confirmatory_pass = bool(
        ch_mdd_reduction >= confirm_mdd_gte
        and ch_cum_delta >= cum_floor
        and ch_n_active >= min_active
    )
    hypothesis_supported = bool(walkforward_pass and confirmatory_pass)
    exploratory_supported = bool(
        wf_non_negative >= wf_min_folds
        and ch_mdd_reduction >= confirm_mdd_gte
        and ch_cum_delta >= cum_floor
    )

    if hypothesis_supported:
        verdict = (
            f"MDD WF+confirm 통과: {challenger_arm} WF {wf_non_negative}/{len(wf_improvements)} "
            f"folds MDD↓≥{wf_mdd_gte:.0%}, confirm MDD↓={ch_mdd_reduction:.1%} (B-track · 승격 아님)"
        )
    elif exploratory_supported and not walkforward_pass:
        verdict = (
            f"MDD confirm exploratory·WF 미달: {challenger_arm} WF folds={wf_non_negative} "
            f"mean_reduction={wf_mean_reduction} (B-track)"
        )
    elif walkforward_pass and not confirmatory_pass:
        verdict = (
            f"MDD WF 통과·confirm 미달: {challenger_arm} confirm MDD↓={ch_mdd_reduction:.1%} "
            f"cumΔ={ch_cum_delta:.4f} (B-track)"
        )
    else:
        verdict = f"{challenger_arm} MDD walk-forward+confirm 실증 미달 — 계약 유지 (B-track)"

    try:
        per_date_rel = str(per_date_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        per_date_rel = str(per_date_path)

    return {
        "schema": "ijeoma_kernel_v2_mdd_safeguard_walkforward_eval_v1",
        "prereg_pointer": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "hypothesis_class": "HYPO",
        "per_date_jsonl": per_date_rel,
        "n_per_date_rows": len(rows),
        "protocol": {
            "fold_holdout_days": fold_holdout_days,
            "n_folds": n_folds,
            "confirmatory_holdout_days": confirmatory_holdout_days,
            "neutral_bps": neutral_bps,
            "position_mode": position_mode,
            "arms": list(arms),
            "note_ko": "P10 frozen baseline; P8/P13 fuse kill-switch only — direction flip 금지",
        },
        "walkforward_folds": fold_results,
        "confirmatory_tail": {
            "date_from": confirm_dates[0],
            "date_to": confirm_dates[-1],
            "n_dates": len(confirm_dates),
            "per_arm": confirm_enriched,
        },
        "aggregation": {
            "baseline_arm": baseline_arm,
            "challenger_arm": challenger_arm,
            "p13_wf_mean_mdd_reduction_vs_p10": (
                round(wf_mean_reduction, 6) if wf_mean_reduction is not None else None
            ),
            "p13_wf_folds_mdd_improvement_met": wf_non_negative,
            "p13_wf_n_folds": len(wf_improvements),
            "walkforward_pass": walkforward_pass,
            "confirmatory_pass": confirmatory_pass,
            "p13_confirm_mdd_reduction_vs_p10": round(ch_mdd_reduction, 6),
            "p13_confirm_cum_delta_vs_p10": round(ch_cum_delta, 6),
            "required_wf_mdd_reduction": wf_mdd_gte,
            "required_confirm_mdd_reduction": confirm_mdd_gte,
            "exploratory_supported": exploratory_supported,
        },
        "hypothesis_supported": hypothesis_supported,
        "exploratory_supported": exploratory_supported,
        "verdict_ko": verdict,
        "repro_command": "py scripts/run_ijeoma_kernel_v2_mdd_safeguard_walkforward_eval_v1.py",
    }
