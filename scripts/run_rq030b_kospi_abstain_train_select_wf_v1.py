#!/usr/bin/env python3
"""[HYPO] RQ-030b — train-block abstain threshold select, test-only score (research_only).

Per blocked WF fold: sweep the RQ-030 pre-registered grid on TRAIN only, pick one cell
(max pooled HR with call_rate floor), apply fixed thresholds to TEST only.
Also scores fixed pre-registered cell abstain_c0.25_m0.00 (from RQ-030 hypothesis) on test
without per-fold re-tuning — for cherry-pick vs locked-threshold contrast.
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

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.build_btrack_prophecy_score_from_ohlcv import _last_n_intersection_trading_dates  # noqa: E402
from scripts.build_kospi_prophecy_wf_holdout_compare_v1 import (  # noqa: E402
    _actuals_for_dates,
    _blocked_folds,
    _hit_rate,
    _majority_label,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.run_rq030_kospi_per_date_abstain_wf_sweep_v1 import (  # noqa: E402
    CONFIDENCE_GRID,
    MARGIN_GRID,
    MIN_CALL_RATE_FOR_BEAT_CANDIDATE,
    _aggregate_folds,
    abstain_grid_id,
    score_abstain_pairs,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_KOSPI_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json"
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_RQ030 = ROOT / "reports/rq030_kospi_per_date_abstain_wf_sweep_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq030b_kospi_abstain_train_select_wf_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/rq030b_kospi_abstain_research_v1_latest.json"
SCHEMA = "rq030b_kospi_abstain_train_select_wf_v1"

# Pre-registered train-selection policy (same grid as RQ-030; selection rule frozen here).
TRAIN_MIN_CALL_RATE = 0.20
TRAIN_MIN_DIRECTIONAL_CALLS = 8
LOCKED_THRESHOLD = {"min_confidence": 0.25, "min_abs_weighted_margin": 0.0, "grid_id": "abstain_c0.25_m0.00"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _majority_pooled_from_wf(wf_compare: dict[str, Any] | None) -> float:
    majority_pooled = 0.632
    if not wf_compare:
        return majority_pooled
    for arm in (wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or []:
        if arm.get("arm_id") == "majority_from_train":
            return float(arm.get("pooled_test_directional_hit_rate") or majority_pooled)
    return majority_pooled


def select_best_grid_on_train(
    per_date_rows: list[dict[str, Any]],
    actuals: dict[str, str],
    train_dates: list[str],
    *,
    min_call_rate: float,
    min_directional_calls: int,
) -> dict[str, Any]:
    """Pick one grid cell using train dates only."""
    candidates: list[dict[str, Any]] = []
    for min_conf in CONFIDENCE_GRID:
        for min_margin in MARGIN_GRID:
            m = score_abstain_pairs(
                per_date_rows,
                actuals,
                train_dates,
                min_confidence=min_conf,
                min_abs_margin=min_margin,
            )
            n_calls = int(m.get("n_directional_calls") or 0)
            cr = m.get("call_rate") or 0.0
            hr = m.get("directional_hit_rate")
            if hr is None or n_calls < min_directional_calls or cr < min_call_rate:
                continue
            candidates.append(m)

    if not candidates:
        return {
            "grid_id": "fallback_per_date_full",
            "min_confidence": 0.0,
            "min_abs_weighted_margin": 0.0,
            "selection_status": "no_train_candidate_fallback_full",
            "train_directional_hit_rate": None,
            "train_call_rate": None,
            "train_n_directional_calls": 0,
        }

    best = max(
        candidates,
        key=lambda r: (
            r.get("directional_hit_rate") or -1.0,
            r.get("call_rate") or 0.0,
        ),
    )
    return {
        "grid_id": best["grid_id"],
        "min_confidence": best["min_confidence"],
        "min_abs_weighted_margin": best["min_abs_weighted_margin"],
        "selection_status": "train_grid_max_hr",
        "train_directional_hit_rate": best.get("directional_hit_rate"),
        "train_call_rate": best.get("call_rate"),
        "train_n_directional_calls": best.get("n_directional_calls"),
        "train_n_panel_days": best.get("n_panel_days"),
    }


def build_nested_document(
    *,
    args: argparse.Namespace,
    eval_dates: list[str],
    folds: list[tuple[list[str], list[str]]],
    actuals: dict[str, str],
    bundle: dict[str, Any],
    kospi_cfg: dict[str, Any],
    frozen_dir: str,
    majority_pooled: float,
    rq030_pointer: dict[str, Any] | None,
) -> dict[str, Any]:
    nested_test_folds: list[dict[str, Any]] = []
    locked_test_folds: list[dict[str, Any]] = []
    full_test_folds: list[dict[str, Any]] = []
    majority_test_folds: list[dict[str, Any]] = []
    fold_selections: list[dict[str, Any]] = []

    for fi, (train, test) in enumerate(folds):
        maj = _majority_label(actuals, train)
        train_rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=kospi_cfg,
            eval_dates=train,
            btc_csv=args.kospi_csv,
            instrument="kospi",
        )
        test_rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=kospi_cfg,
            eval_dates=test,
            btc_csv=args.kospi_csv,
            instrument="kospi",
        )

        selection = select_best_grid_on_train(
            train_rows,
            actuals,
            train,
            min_call_rate=TRAIN_MIN_CALL_RATE,
            min_directional_calls=TRAIN_MIN_DIRECTIONAL_CALLS,
        )

        if selection["grid_id"] == "fallback_per_date_full":
            nested_metrics = score_abstain_pairs(
                test_rows,
                actuals,
                test,
                min_confidence=0.0,
                min_abs_margin=0.0,
            )
        else:
            nested_metrics = score_abstain_pairs(
                test_rows,
                actuals,
                test,
                min_confidence=float(selection["min_confidence"]),
                min_abs_margin=float(selection["min_abs_weighted_margin"]),
            )

        locked_metrics = score_abstain_pairs(
            test_rows,
            actuals,
            test,
            min_confidence=LOCKED_THRESHOLD["min_confidence"],
            min_abs_margin=LOCKED_THRESHOLD["min_abs_weighted_margin"],
        )

        full_pairs: list[tuple[str, str]] = []
        maj_pairs: list[tuple[str, str]] = []
        row_map = {str(r.get("eval_date") or "")[:10]: r for r in test_rows}
        for ed in test:
            act = actuals.get(ed)
            if not act:
                continue
            row = row_map.get(ed)
            pred = str((row or {}).get("predicted_direction") or "neutral").strip().lower()
            full_pairs.append((pred, act))
            maj_pairs.append((maj, act))

        fold_common = {
            "fold": fi,
            "test_date_from": test[0],
            "test_date_to": test[-1],
            "train_date_from": train[0],
            "train_date_to": train[-1],
            "train_majority_label": maj,
        }

        nested_test_folds.append({**fold_common, **nested_metrics, "selected_on_train": selection})
        locked_test_folds.append({**fold_common, **locked_metrics})
        full_test_folds.append({**fold_common, **_hit_rate(full_pairs), "n_panel_days": len(full_pairs), "call_rate": 1.0})
        majority_test_folds.append({**fold_common, **_hit_rate(maj_pairs), "n_panel_days": len(maj_pairs), "call_rate": 1.0})
        fold_selections.append({"fold": fi, **selection})

    arms = {
        "nested_train_select_abstain": _aggregate_folds(nested_test_folds),
        "locked_preregistered_c0.25_m0.00": _aggregate_folds(locked_test_folds),
        "per_date_kospi_ensemble_full": _aggregate_folds(full_test_folds),
        "majority_from_train": _aggregate_folds(majority_test_folds),
    }

    def _vs_majority(pooled: Any) -> float | None:
        if pooled is None:
            return None
        return round((float(pooled) - majority_pooled) * 100, 2)

    arms_out = []
    for arm_id, agg in arms.items():
        pooled = agg.get("pooled_test_directional_hit_rate")
        arms_out.append(
            {
                "arm_id": arm_id,
                "protocol": "blocked_walkforward_train_select_test_score",
                "beats_majority_pooled": pooled is not None and pooled > majority_pooled,
                "vs_majority_pooled_pp": _vs_majority(pooled),
                **agg,
            }
        )

    nested_arm = next(a for a in arms_out if a["arm_id"] == "nested_train_select_abstain")
    locked_arm = next(a for a in arms_out if a["arm_id"] == "locked_preregistered_c0.25_m0.00")

    rq030_best = (rq030_pointer or {}).get("best_honest_beat_majority") or {}
    rq030_pooled = rq030_best.get("pooled_test_directional_hit_rate")

    def _fmt_pp(pooled: Any) -> str:
        delta = _vs_majority(pooled)
        if delta is None:
            return "n/a vs majority"
        return f"{delta:+.2f}pp vs majority"

    readout = [
        f"252d blocked WF nested: majority pooled {majority_pooled}.",
        (
            f"nested train-select test pooled {nested_arm.get('pooled_test_directional_hit_rate')} "
            f"call_rate {nested_arm.get('pooled_call_rate')} "
            f"({_fmt_pp(nested_arm.get('pooled_test_directional_hit_rate'))})."
        ),
        (
            f"locked c0.25_m0.00 (RQ-030 pre-reg) test pooled {locked_arm.get('pooled_test_directional_hit_rate')} "
            f"call_rate {locked_arm.get('pooled_call_rate')} "
            f"({_fmt_pp(locked_arm.get('pooled_test_directional_hit_rate'))})."
        ),
        (
            f"RQ-030 full-OOS grid best was {rq030_pooled} (cherry-pick contrast) — "
            "nested/locked are honest test protocols."
        ),
        "Track A·headline·ops score 변경 없음 — research_only [HYPO].",
    ]

    beats = [
        a
        for a in (nested_arm, locked_arm)
        if a.get("beats_majority_pooled")
        and (a.get("pooled_call_rate") or 0.0) >= MIN_CALL_RATE_FOR_BEAT_CANDIDATE
    ]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "rq_id": "RQ-030b",
        "purpose_ko": "train 블록에서 abstain threshold 1개 선택 → test만 채점 (RQ-030 cherry-pick 검증)",
        "window": {
            "eval_days": int(args.eval_days),
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_calendar_days": len(eval_dates),
            "neutral_bps": float(args.neutral_bps),
            "n_folds": int(args.n_folds),
            "frozen_today_hypothesis_direction": frozen_dir,
        },
        "train_selection_policy": {
            "grid": {
                "confidence_grid": list(CONFIDENCE_GRID),
                "margin_grid": list(MARGIN_GRID),
            },
            "min_call_rate_on_train": TRAIN_MIN_CALL_RATE,
            "min_directional_calls_on_train": TRAIN_MIN_DIRECTIONAL_CALLS,
            "objective": "max train pooled directional_hit_rate; tie-break call_rate",
            "fallback_if_no_candidate": "per_date_full (conf=0,margin=0)",
        },
        "locked_threshold_preregistered": LOCKED_THRESHOLD,
        "rq030_pointer": str(DEFAULT_RQ030.relative_to(ROOT)).replace("\\", "/"),
        "rq030_full_oos_best_pooled_hr": rq030_pooled,
        "wf_majority_baseline_pooled_hr": majority_pooled,
        "fold_train_selections": fold_selections,
        "arms": arms_out,
        "honest_beat_majority_arms": [
            {"arm_id": a["arm_id"], "pooled_test_directional_hit_rate": a.get("pooled_test_directional_hit_rate"), "pooled_call_rate": a.get("pooled_call_rate")}
            for a in beats
        ],
        "recommended_next_arm": None,
        "readout_ko": readout,
        "interpretation_ko": [
            "nested = fold마다 train에서 grid 1칸 선택 후 test 적용 — RQ-030 pooled grid sweep과 대비.",
            "locked c0.25 = RQ-030에서 제안한 단일 threshold를 test에만 적용 (전 OOS grid 재탐색 아님).",
            "train-select가 majority를 넘지 못하면 RQ-030 +1.7pp는 다중비교·test leakage 의심으로 격하.",
        ],
        "reproduce": (
            f"py scripts/run_rq030b_kospi_abstain_train_select_wf_v1.py "
            f"--eval-days {args.eval_days} --n-folds {args.n_folds} --neutral-bps {args.neutral_bps}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--kospi-ensemble-config", type=Path, default=DEFAULT_KOSPI_CFG)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--wf-compare-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--rq030-json", type=Path, default=DEFAULT_RQ030)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pointer-output", type=Path, default=DEFAULT_POINTER)
    args = ap.parse_args(argv)

    for p in (args.kospi_csv, args.btc_csv, args.bundle_json, args.kospi_ensemble_config, args.hypothesis_json):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    btc_rows = load_kospi_yf_rows(args.btc_csv)
    panel_dates = _last_n_intersection_trading_dates(kospi_rows, btc_rows, int(args.eval_days))
    actuals = _actuals_for_dates(
        kospi_rows,
        panel_dates,
        neutral_bps=float(args.neutral_bps),
        max_abs_ret=float(args.max_abs_daily_return),
    )
    eval_dates = sorted(d for d in panel_dates if d in actuals)
    folds = _blocked_folds(eval_dates, int(args.n_folds))
    if not folds:
        print("no wf folds", file=sys.stderr)
        return 2

    bundle = _load_json(args.bundle_json)
    kospi_cfg = _load_json(args.kospi_ensemble_config)
    hyp = _load_json(args.hypothesis_json)
    frozen_dir = str((hyp.get("prediction") or {}).get("direction") or "neutral").strip().lower()
    wf_compare = _load_json(args.wf_compare_json) if args.wf_compare_json.is_file() else None
    rq030_pointer = _load_json(args.rq030_json) if args.rq030_json.is_file() else None
    majority_pooled = _majority_pooled_from_wf(wf_compare)

    out = build_nested_document(
        args=args,
        eval_dates=eval_dates,
        folds=folds,
        actuals=actuals,
        bundle=bundle,
        kospi_cfg=kospi_cfg,
        frozen_dir=frozen_dir,
        majority_pooled=majority_pooled,
        rq030_pointer=rq030_pointer,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    nested = next(a for a in out["arms"] if a["arm_id"] == "nested_train_select_abstain")
    locked = next(a for a in out["arms"] if a["arm_id"] == "locked_preregistered_c0.25_m0.00")

    pointer = {
        "schema": "rq030b_kospi_abstain_research_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-030b",
        "evidence": str(args.output.relative_to(ROOT)).replace("\\", "/"),
        "rq030_evidence": str(DEFAULT_RQ030.relative_to(ROOT)).replace("\\", "/"),
        "wf_majority_baseline_pooled_hr": majority_pooled,
        "nested_train_select": {
            "pooled_test_directional_hit_rate": nested.get("pooled_test_directional_hit_rate"),
            "pooled_call_rate": nested.get("pooled_call_rate"),
            "vs_majority_pooled_pp": nested.get("vs_majority_pooled_pp"),
            "beats_majority_pooled": nested.get("beats_majority_pooled"),
        },
        "locked_preregistered_c0.25": {
            "pooled_test_directional_hit_rate": locked.get("pooled_test_directional_hit_rate"),
            "pooled_call_rate": locked.get("pooled_call_rate"),
            "vs_majority_pooled_pp": locked.get("vs_majority_pooled_pp"),
            "beats_majority_pooled": locked.get("beats_majority_pooled"),
        },
        "honest_beat_majority_arms": out.get("honest_beat_majority_arms"),
        "readout_ko": out.get("readout_ko"),
        "reproduce": out.get("reproduce"),
    }
    args.pointer_output.parent.mkdir(parents=True, exist_ok=True)
    args.pointer_output.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} nested_pooled={nested.get('pooled_test_directional_hit_rate')} "
        f"locked_pooled={locked.get('pooled_test_directional_hit_rate')} majority={majority_pooled}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
