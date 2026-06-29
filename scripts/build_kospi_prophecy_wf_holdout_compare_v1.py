#!/usr/bin/env python3
"""[HYPO] Blocked walk-forward OOS compare — per-date KOSPI ensemble vs straw-man baselines."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _actual_direction,
    _last_n_intersection_trading_dates,
    _row_pair_for_eval_date,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_KOSPI_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json"
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_FAIR = ROOT / "reports/kospi_prophecy_fair_ablation_compare_v1_latest.json"
SCHEMA = "kospi_prophecy_wf_holdout_compare_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def _actuals_for_dates(
    kospi_rows: list[dict[str, Any]],
    dates: list[str],
    *,
    neutral_bps: float,
    max_abs_ret: float,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for ed in dates:
        pair = _row_pair_for_eval_date(kospi_rows, ed)
        if pair is None:
            continue
        prev_r, cur_r = pair
        try:
            ret = (float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"])
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if abs(ret) > max_abs_ret:
            continue
        out[ed] = _actual_direction(ret, neutral_bps)
    return out


def _hit_rate(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    hits = n = 0
    pred_dist: Counter[str] = Counter()
    for pred, act in pairs:
        if pred not in ("bull", "bear", "neutral") or act not in ("bull", "bear", "neutral"):
            continue
        n += 1
        pred_dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dict(pred_dist),
    }


def _majority_label(actuals: dict[str, str], train_dates: list[str]) -> str:
    c: Counter[str] = Counter()
    for d in train_dates:
        a = actuals.get(d)
        if a in ("bull", "bear", "neutral"):
            c[a] += 1
    if not c:
        return "neutral"
    return c.most_common(1)[0][0]


def _mom_pred(
    kospi_rows: list[dict[str, Any]],
    eval_date: str,
    *,
    lookback: int,
    neutral_bps: float,
) -> str:
    by_date = {str(r["date"])[:10]: r for r in kospi_rows}
    dates = sorted(by_date.keys())
    if eval_date not in dates:
        return "neutral"
    idx = dates.index(eval_date)
    if idx < lookback:
        return "neutral"
    try:
        c0 = float(by_date[dates[idx - lookback]]["close"])
        c1 = float(by_date[dates[idx - 1]]["close"])
    except (TypeError, ValueError, KeyError):
        return "neutral"
    if c0 == 0.0:
        return "neutral"
    return _actual_direction((c1 - c0) / c0, neutral_bps)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    for p in (args.kospi_csv, args.btc_csv, DEFAULT_BUNDLE, DEFAULT_KOSPI_CFG, DEFAULT_HYP):
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

    bundle = _load(DEFAULT_BUNDLE)
    kospi_cfg = _load(DEFAULT_KOSPI_CFG)
    hyp = _load(DEFAULT_HYP)
    frozen_dir = str((hyp.get("prediction") or {}).get("direction") or "neutral").strip().lower()
    if frozen_dir not in ("bull", "bear", "neutral"):
        frozen_dir = "neutral"

    arm_ids = [
        "per_date_kospi_ensemble",
        "majority_from_train",
        "mom_20d",
        "mom_5d",
        "frozen_today_hypothesis",
    ]
    fold_rows: dict[str, list[dict[str, Any]]] = {a: [] for a in arm_ids}

    for fi, (train, test) in enumerate(folds):
        maj = _majority_label(actuals, train)
        per_date_rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=kospi_cfg,
            eval_dates=test,
            ohlc_csv=args.kospi_csv,
            instrument="kospi",
        )
        per_date_map = {str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "neutral") for r in per_date_rows}

        arm_pairs: dict[str, list[tuple[str, str]]] = {a: [] for a in arm_ids}
        for ed in test:
            act = actuals.get(ed)
            if not act:
                continue
            arm_pairs["per_date_kospi_ensemble"].append((per_date_map.get(ed, "neutral"), act))
            arm_pairs["majority_from_train"].append((maj, act))
            arm_pairs["mom_20d"].append((_mom_pred(kospi_rows, ed, lookback=20, neutral_bps=float(args.neutral_bps)), act))
            arm_pairs["mom_5d"].append((_mom_pred(kospi_rows, ed, lookback=5, neutral_bps=float(args.neutral_bps)), act))
            arm_pairs["frozen_today_hypothesis"].append((frozen_dir, act))

        for arm_id in arm_ids:
            m = _hit_rate(arm_pairs[arm_id])
            fold_rows[arm_id].append(
                {
                    "fold": fi,
                    "test_date_from": test[0],
                    "test_date_to": test[-1],
                    "train_majority_label": maj if arm_id == "majority_from_train" else None,
                    **m,
                }
            )

    def _aggregate(folds_list: list[dict[str, Any]]) -> dict[str, Any]:
        rates = [f["directional_hit_rate"] for f in folds_list if f.get("directional_hit_rate") is not None]
        total_n = sum(int(f.get("n_evaluated") or 0) for f in folds_list)
        total_hits = sum(int(f.get("price_hits") or 0) for f in folds_list)
        pooled = round(total_hits / total_n, 6) if total_n else None
        return {
            "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
            "pooled_test_directional_hit_rate": pooled,
            "fold_hit_rates": rates,
            "total_n_evaluated": total_n,
            "total_price_hits": total_hits,
            "n_folds_scored": len(rates),
            "folds": folds_list,
        }

    arms_out = [{"arm_id": aid, "protocol": "blocked_walkforward_test_only", **_aggregate(fold_rows[aid])} for aid in arm_ids]

    fair = _load(DEFAULT_FAIR) if DEFAULT_FAIR.is_file() else {}
    in_sample = (fair.get("primary_compare_same_bps") or {}) if fair else {}

    best = max(arms_out, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "window": {
            "eval_days": int(args.eval_days),
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_calendar_days": len(eval_dates),
            "neutral_bps": float(args.neutral_bps),
            "n_folds": int(args.n_folds),
            "frozen_today_hypothesis_direction": frozen_dir,
        },
        "blocked_walkforward_test_only": {"arms": arms_out},
        "best_pooled_arm": {
            "arm_id": best["arm_id"],
            "pooled_test_directional_hit_rate": best.get("pooled_test_directional_hit_rate"),
            "mean_test_directional_hit_rate": best.get("mean_test_directional_hit_rate"),
        },
        "in_sample_same_bps_pointer": str(DEFAULT_FAIR.relative_to(ROOT)).replace("\\", "/") if fair else None,
        "in_sample_panel_compare": {
            "per_date_causal": (in_sample.get("per_date_causal_kospi") or {}).get("price_directional_hit_rate"),
            "frozen_operational": (in_sample.get("frozen_operational_panel") or {}).get("price_directional_hit_rate"),
            "always_majority_bull": (fair.get("straw_man_baselines_same_panel") or {})
            .get("always_majority_class", {})
            .get("hit_rate"),
            "note": "in-sample 30d panel — not OOS; see delta interpretation",
        },
        "interpretation_ko": [
            "test block만 채점; per-date ensemble은 test 날짜에만 compute_per_date_direction_rows (가격 인과).",
            "majority_from_train = train 블록 actual 최빈값 → test 고정 (진짜 OOS majority baseline).",
            "in-sample 63.3% > majority 66.7% paradox는 OOS pooled로 재검증 필요 — 본 JSON이 그 답.",
            "Track A·headline·live 자동 교체 없음.",
        ],
        "reproduce": (
            f"py scripts/build_kospi_prophecy_wf_holdout_compare_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --neutral-bps {args.neutral_bps}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} best={best['arm_id']} "
        f"pooled={best.get('pooled_test_directional_hit_rate')} per_date_pooled="
        f"{next(a for a in arms_out if a['arm_id']=='per_date_kospi_ensemble').get('pooled_test_directional_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
