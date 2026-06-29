#!/usr/bin/env python3
"""[HYPO] RQ-030 KOSPI per-date ensemble abstain sweep on blocked WF OOS (research_only).

Pre-registered confidence × |weighted_score| margin grid on per-date KOSPI ensemble.
Reports coverage (call_rate) vs pooled directional hit rate on 252d blocked WF folds.
Does not mutate operational score JSON or Track A headlines.
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
from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _last_n_intersection_trading_dates,
    _row_pair_for_eval_date,
)
from scripts.build_kospi_prophecy_wf_holdout_compare_v1 import (  # noqa: E402
    _actuals_for_dates,
    _blocked_folds,
    _hit_rate,
    _majority_label,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_KOSPI_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json"
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq030_kospi_per_date_abstain_wf_sweep_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/rq030_kospi_abstain_research_v1_latest.json"
SCHEMA = "rq030_kospi_per_date_abstain_wf_sweep_v1"

# Pre-registered grid — not tuned on OOS test blocks.
CONFIDENCE_GRID: tuple[float, ...] = (0.0, 0.15, 0.18, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50)
MARGIN_GRID: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25)
MIN_CALL_RATE_FOR_BEAT_CANDIDATE = 0.25


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def abstain_grid_id(min_confidence: float, min_abs_margin: float) -> str:
    return f"abstain_c{min_confidence:.2f}_m{min_abs_margin:.2f}"


def apply_abstain_filter(
    row: dict[str, Any],
    *,
    min_confidence: float,
    min_abs_margin: float,
) -> str | None:
    """Return bull/bear direction if call; None if abstain."""
    direction = str(row.get("predicted_direction") or "neutral").strip().lower()
    if direction not in ("bull", "bear"):
        return None
    conf = _safe_float(row.get("confidence"))
    if conf < min_confidence:
        return None
    margin = abs(_safe_float(row.get("weighted_score")))
    if margin < min_abs_margin:
        return None
    return direction


def score_abstain_pairs(
    per_date_rows: list[dict[str, Any]],
    actuals: dict[str, str],
    test_dates: list[str],
    *,
    min_confidence: float,
    min_abs_margin: float,
) -> dict[str, Any]:
    row_map = {str(r.get("eval_date") or "")[:10]: r for r in per_date_rows}
    pairs: list[tuple[str, str]] = []
    n_panel = 0
    n_abstain = 0
    for ed in test_dates:
        act = actuals.get(ed)
        if act not in ("bull", "bear", "neutral"):
            continue
        n_panel += 1
        row = row_map.get(ed)
        if not row:
            n_abstain += 1
            continue
        pred = apply_abstain_filter(
            row,
            min_confidence=min_confidence,
            min_abs_margin=min_abs_margin,
        )
        if pred is None:
            n_abstain += 1
            continue
        pairs.append((pred, act))
    metrics = _hit_rate(pairs)
    n_calls = int(metrics.get("n_evaluated") or 0)
    call_rate = round(n_calls / n_panel, 6) if n_panel else None
    return {
        **metrics,
        "n_panel_days": n_panel,
        "n_abstain": n_abstain,
        "n_directional_calls": n_calls,
        "call_rate": call_rate,
        "min_confidence": min_confidence,
        "min_abs_weighted_margin": min_abs_margin,
        "grid_id": abstain_grid_id(min_confidence, min_abs_margin),
    }


def _aggregate_folds(folds: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in folds if f.get("directional_hit_rate") is not None]
    total_n = sum(int(f.get("n_evaluated") or 0) for f in folds)
    total_hits = sum(int(f.get("price_hits") or 0) for f in folds)
    total_panel = sum(int(f.get("n_panel_days") or 0) for f in folds)
    total_abstain = sum(int(f.get("n_abstain") or 0) for f in folds)
    pooled = round(total_hits / total_n, 6) if total_n else None
    call_rate = round(total_n / total_panel, 6) if total_panel else None
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": pooled,
        "pooled_call_rate": call_rate,
        "total_n_panel_days": total_panel,
        "total_n_abstain": total_abstain,
        "total_n_directional_calls": total_n,
        "total_price_hits": total_hits,
        "n_folds_scored": len(rates),
        "fold_hit_rates": rates,
        "folds": folds,
    }


def pick_best_honest(
    sweep_rows: list[dict[str, Any]],
    *,
    majority_pooled: float,
    min_call_rate: float,
) -> dict[str, Any] | None:
    candidates = [
        r
        for r in sweep_rows
        if (r.get("pooled_test_directional_hit_rate") or -1.0) > majority_pooled
        and (r.get("pooled_call_rate") or 0.0) >= min_call_rate
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda r: (
            r.get("pooled_test_directional_hit_rate") or -1.0,
            r.get("pooled_call_rate") or 0.0,
        ),
    )


def build_sweep_document(
    *,
    args: argparse.Namespace,
    eval_dates: list[str],
    folds: list[tuple[list[str], list[str]]],
    actuals: dict[str, str],
    bundle: dict[str, Any],
    kospi_cfg: dict[str, Any],
    frozen_dir: str,
    wf_compare: dict[str, Any] | None,
) -> dict[str, Any]:
    majority_pooled = 0.632
    if wf_compare:
        for arm in (wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or []:
            if arm.get("arm_id") == "majority_from_train":
                majority_pooled = float(arm.get("pooled_test_directional_hit_rate") or majority_pooled)
                break

    baseline_folds: dict[str, list[dict[str, Any]]] = {
        "per_date_kospi_ensemble_full": [],
        "majority_from_train": [],
    }
    sweep_folds: dict[str, list[dict[str, Any]]] = {
        abstain_grid_id(c, m): [] for c in CONFIDENCE_GRID for m in MARGIN_GRID
    }

    for fi, (train, test) in enumerate(folds):
        maj = _majority_label(actuals, train)
        per_date_rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=kospi_cfg,
            eval_dates=test,
            ohlc_csv=args.kospi_csv,
            instrument="kospi",
        )

        full_pairs: list[tuple[str, str]] = []
        maj_pairs: list[tuple[str, str]] = []
        for ed in test:
            act = actuals.get(ed)
            if not act:
                continue
            row_map = {str(r.get("eval_date") or "")[:10]: r for r in per_date_rows}
            row = row_map.get(ed)
            pred = str((row or {}).get("predicted_direction") or "neutral").strip().lower()
            full_pairs.append((pred, act))
            maj_pairs.append((maj, act))

        baseline_folds["per_date_kospi_ensemble_full"].append(
            {
                "fold": fi,
                "test_date_from": test[0],
                "test_date_to": test[-1],
                **_hit_rate(full_pairs),
                "n_panel_days": len(full_pairs),
                "n_abstain": 0,
                "call_rate": 1.0 if full_pairs else None,
            }
        )
        baseline_folds["majority_from_train"].append(
            {
                "fold": fi,
                "test_date_from": test[0],
                "test_date_to": test[-1],
                "train_majority_label": maj,
                **_hit_rate(maj_pairs),
                "n_panel_days": len(maj_pairs),
                "call_rate": 1.0 if maj_pairs else None,
            }
        )

        for min_conf in CONFIDENCE_GRID:
            for min_margin in MARGIN_GRID:
                gid = abstain_grid_id(min_conf, min_margin)
                fold_metrics = score_abstain_pairs(
                    per_date_rows,
                    actuals,
                    test,
                    min_confidence=min_conf,
                    min_abs_margin=min_margin,
                )
                sweep_folds[gid].append(
                    {
                        "fold": fi,
                        "test_date_from": test[0],
                        "test_date_to": test[-1],
                        **fold_metrics,
                    }
                )

    baselines_out = [
        {
            "arm_id": arm_id,
            "protocol": "blocked_walkforward_test_only",
            **_aggregate_folds(fold_list),
        }
        for arm_id, fold_list in baseline_folds.items()
    ]

    sweep_out: list[dict[str, Any]] = []
    for min_conf in CONFIDENCE_GRID:
        for min_margin in MARGIN_GRID:
            gid = abstain_grid_id(min_conf, min_margin)
            agg = _aggregate_folds(sweep_folds[gid])
            pooled = agg.get("pooled_test_directional_hit_rate")
            sweep_out.append(
                {
                    "grid_id": gid,
                    "min_confidence": min_conf,
                    "min_abs_weighted_margin": min_margin,
                    "beats_majority_pooled": (
                        pooled is not None and pooled > majority_pooled
                    ),
                    "vs_majority_pooled_pp": (
                        round((float(pooled) - majority_pooled) * 100, 2)
                        if pooled is not None
                        else None
                    ),
                    **agg,
                }
            )

    best_honest = pick_best_honest(
        sweep_out,
        majority_pooled=majority_pooled,
        min_call_rate=MIN_CALL_RATE_FOR_BEAT_CANDIDATE,
    )

    # Pareto frontier: no other point has both higher HR and higher call_rate
    pareto: list[dict[str, Any]] = []
    for row in sweep_out:
        hr = row.get("pooled_test_directional_hit_rate") or -1.0
        cr = row.get("pooled_call_rate") or 0.0
        dominated = False
        for other in sweep_out:
            if other is row:
                continue
            ohr = other.get("pooled_test_directional_hit_rate") or -1.0
            ocr = other.get("pooled_call_rate") or 0.0
            if ohr >= hr and ocr >= cr and (ohr > hr or ocr > cr):
                dominated = True
                break
        if not dominated and row.get("pooled_test_directional_hit_rate") is not None:
            pareto.append(
                {
                    "grid_id": row["grid_id"],
                    "pooled_test_directional_hit_rate": row.get("pooled_test_directional_hit_rate"),
                    "pooled_call_rate": row.get("pooled_call_rate"),
                    "vs_majority_pooled_pp": row.get("vs_majority_pooled_pp"),
                }
            )

    per_date_baseline = next(b for b in baselines_out if b["arm_id"] == "per_date_kospi_ensemble_full")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "rq_id": "RQ-030",
        "purpose_ko": "252d blocked WF에서 per-date KOSPI abstain 커버리지–HR 곡선; majority honest beat 여부",
        "window": {
            "eval_days": int(args.eval_days),
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_calendar_days": len(eval_dates),
            "neutral_bps": float(args.neutral_bps),
            "n_folds": int(args.n_folds),
            "frozen_today_hypothesis_direction": frozen_dir,
        },
        "pre_registered_grid": {
            "confidence_grid": list(CONFIDENCE_GRID),
            "margin_grid": list(MARGIN_GRID),
            "min_call_rate_for_beat_candidate": MIN_CALL_RATE_FOR_BEAT_CANDIDATE,
            "note_ko": "OOS test 블록에 그리드 고정 적용 — test로 threshold 재적합 없음",
        },
        "wf_majority_baseline_pooled_hr": majority_pooled,
        "wf_compare_pointer": str(DEFAULT_WF.relative_to(ROOT)).replace("\\", "/"),
        "baselines": baselines_out,
        "abstain_sweep": sweep_out,
        "pareto_frontier": sorted(
            pareto,
            key=lambda x: (x.get("pooled_call_rate") or 0.0),
        ),
        "best_honest_beat_majority": best_honest,
        "recommended_next_arm": None,
        "readout_ko": _readout_ko(
            majority_pooled=majority_pooled,
            per_date_pooled=per_date_baseline.get("pooled_test_directional_hit_rate"),
            best_honest=best_honest,
        ),
        "interpretation_ko": [
            "abstain으로 subset HR이 majority를 넘어도 call_rate·전체 커버리지와 함께 보고.",
            "Track A·headline·live·ops score JSON 자동 변경 없음.",
            "BTC는 패널 교집합 날짜용만 — 예측은 KOSPI per-date ensemble.",
        ],
        "reproduce": (
            f"py scripts/run_rq030_kospi_per_date_abstain_wf_sweep_v1.py "
            f"--eval-days {args.eval_days} --n-folds {args.n_folds} --neutral-bps {args.neutral_bps}"
        ),
    }


def _readout_ko(
    *,
    majority_pooled: float,
    per_date_pooled: Any,
    best_honest: dict[str, Any] | None,
) -> list[str]:
    lines = [
        f"252d blocked WF: per-date full pooled {per_date_pooled} vs majority {majority_pooled}.",
        f"abstain grid {len(CONFIDENCE_GRID)}×{len(MARGIN_GRID)} — pre-registered, OOS test only.",
    ]
    if best_honest:
        lines.append(
            f"best honest beat (call_rate≥{MIN_CALL_RATE_FOR_BEAT_CANDIDATE}): "
            f"{best_honest.get('grid_id')} pooled {best_honest.get('pooled_test_directional_hit_rate')} "
            f"call_rate {best_honest.get('pooled_call_rate')} "
            f"({best_honest.get('vs_majority_pooled_pp'):+.2f}pp vs majority)."
        )
    else:
        lines.append(
            f"no grid cell beats majority {majority_pooled} with call_rate≥{MIN_CALL_RATE_FOR_BEAT_CANDIDATE}."
        )
    lines.append("승격·Track A 합선 없음 — research_only [HYPO].")
    return lines


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
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pointer-output", type=Path, default=DEFAULT_POINTER)
    args = ap.parse_args(argv)

    required = (
        args.kospi_csv,
        args.btc_csv,
        args.bundle_json,
        args.kospi_ensemble_config,
        args.hypothesis_json,
    )
    for p in required:
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    btc_rows = load_kospi_yf_rows(args.btc_csv)
    panel_dates = _last_n_intersection_trading_dates(kospi_rows, btc_rows, int(args.eval_days))
    if len(panel_dates) < 20:
        print("insufficient panel dates", file=sys.stderr)
        return 2

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
    if frozen_dir not in ("bull", "bear", "neutral"):
        frozen_dir = "neutral"

    wf_compare = _load_json(args.wf_compare_json) if args.wf_compare_json.is_file() else None

    out = build_sweep_document(
        args=args,
        eval_dates=eval_dates,
        folds=folds,
        actuals=actuals,
        bundle=bundle,
        kospi_cfg=kospi_cfg,
        frozen_dir=frozen_dir,
        wf_compare=wf_compare,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pointer = {
        "schema": "rq030_kospi_abstain_research_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-030",
        "evidence": str(args.output.relative_to(ROOT)).replace("\\", "/"),
        "wf_majority_baseline_pooled_hr": out.get("wf_majority_baseline_pooled_hr"),
        "per_date_full_pooled_hr": next(
            b.get("pooled_test_directional_hit_rate")
            for b in out.get("baselines") or []
            if b.get("arm_id") == "per_date_kospi_ensemble_full"
        ),
        "best_honest_beat_majority": out.get("best_honest_beat_majority"),
        "recommended_next_arm": out.get("recommended_next_arm"),
        "readout_ko": out.get("readout_ko"),
        "reproduce": out.get("reproduce"),
    }
    args.pointer_output.parent.mkdir(parents=True, exist_ok=True)
    args.pointer_output.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best = out.get("best_honest_beat_majority")
    print(
        f"WROTE: {args.output.resolve()} majority={out.get('wf_majority_baseline_pooled_hr')} "
        f"best_honest={best.get('grid_id') if best else None} "
        f"pooled={best.get('pooled_test_directional_hit_rate') if best else None}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
