#!/usr/bin/env python3
"""[HYPO] RQ-028 KOSPI lens-minimal blocked WF on 252d (research_only).

Extends 30d lens ablation to blocked walk-forward OOS: sasang+myeongni vs lens3 vs
mom_20d vs train-majority on session panel intersect.
"""

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

from scripts.run_kospi_lens_ablation_backtest_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_PANEL_252,
    DEFAULT_SASANG_JSONL,
    ablation_arm_catalog,
)
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    KOSPI_CSV,
    _load_closes,
    _load_panel,
    _predict_v2,
    _read_json,
    _score_series,
)
from scripts.run_rq025_chronos2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _actual_direction,
    _blocked_folds,
    _mom_pred,
)
from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses  # noqa: E402
from scripts.kospi_lens_per_date_static_v1 import load_lens_jsonl_by_day, static_lenses_for_eval_date  # noqa: E402

DEFAULT_OUT = ROOT / "reports/rq028_kospi_lens_minimal_wf_shadow_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
SCHEMA = "rq028_kospi_lens_minimal_wf_shadow_v1"
ARM_IDS = ("sasang_myeongni_only", "lens3_runtime", "three_lens_runtime", "mom_20d", "majority_from_train")


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


def _majority_label(train_dates: list[str], closes: dict[str, float], neutral_bps: float) -> str:
    c: Counter[str] = Counter()
    sorted_d = sorted(closes.keys())
    for d in train_dates:
        if d not in closes:
            continue
        idx = sorted_d.index(d)
        if idx < 1:
            continue
        c0, c1 = closes[sorted_d[idx - 1]], closes[d]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        c[_actual_direction(ret, neutral_bps)] += 1
    return c.most_common(1)[0][0] if c else "neutral"


def _directional_hit(preds: dict[str, str], closes: dict[str, float], dates: list[str], neutral_bps: float) -> dict[str, Any]:
    hits = n = 0
    dist: Counter[str] = Counter()
    sorted_d = sorted(closes.keys())
    for d in dates:
        if d not in preds or d not in closes:
            continue
        idx = sorted_d.index(d)
        if idx < 1:
            continue
        c0, c1 = closes[sorted_d[idx - 1]], closes[d]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        pred = preds[d]
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dict(dist),
        "pred_bull_share": round(dist.get("bull", 0) / n, 4) if n else None,
    }


def _aggregate(folds: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in folds if f.get("directional_hit_rate") is not None]
    total_n = sum(int(f.get("n_evaluated") or 0) for f in folds)
    total_hits = sum(int(f.get("price_hits") or 0) for f in folds)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(total_hits / total_n, 6) if total_n else None,
        "fold_hit_rates": rates,
        "total_n_evaluated": total_n,
        "total_price_hits": total_hits,
        "n_folds_scored": len(rates),
        "folds": folds,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL_252)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.panel_csv.is_file() or not args.kospi_csv.is_file():
        print("missing panel or kospi csv", file=sys.stderr)
        return 2

    rules = _read_json(EVOLUTION_RULES)
    panel = _load_panel(args.panel_csv)
    closes = _load_closes(args.kospi_csv)
    neutral_bps = float(args.neutral_bps)
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})
    baseline_lenses = load_static_lenses()

    my_by_day, sa_by_day, lens_meta = load_lens_jsonl_by_day(args.myeongni_jsonl, args.sasang_jsonl)
    arms_catalog = ablation_arm_catalog(rules)
    lens_arms = {k: arms_catalog[k] for k in ("sasang_myeongni_only", "lens3_runtime", "three_lens_runtime")}

    eval_dates = sorted(d for d in panel if d in closes)
    if args.eval_days > 0 and len(eval_dates) > args.eval_days:
        eval_dates = eval_dates[-args.eval_days :]
    folds = _blocked_folds(eval_dates, args.n_folds)
    if not folds:
        print("no folds", file=sys.stderr)
        return 2

    arm_fold_rows: dict[str, list[dict[str, Any]]] = {a: [] for a in ARM_IDS}
    ensemble_cache: dict[str, Any] = {}

    for fi, (train, test) in enumerate(folds):
        maj = _majority_label(train, closes, neutral_bps)
        test_preds: dict[str, dict[str, str]] = {a: {} for a in ARM_IDS}

        if not ensemble_cache:
            ensemble_cache = load_ensemble_kospi_per_date(eval_dates)

        for dk in test:
            if dk not in panel:
                continue
            day_lenses = static_lenses_for_eval_date(
                dk, sasang_by_day=sa_by_day, myeongni_by_day=my_by_day, baseline=baseline_lenses
            )
            for arm_id, spec in lens_arms.items():
                pred, _meta = _predict_v2(
                    dk,
                    panel_row=panel[dk],
                    closes=closes,
                    static_lenses=day_lenses,
                    ensemble_row=ensemble_cache.get(dk),
                    weights=spec["weights"],
                    blend_policy=blend_policy,
                    neutral_band=neutral_band,
                    four_ai_mode=str(spec["four_ai_mode"]),
                    coord_policy=coord_policy,
                )
                test_preds[arm_id][dk] = pred

            sorted_d = sorted(closes.keys())
            if dk in sorted_d:
                idx = sorted_d.index(dk)
                if idx >= 20:
                    closes_list = [closes[d] for d in sorted_d[: idx + 1]]
                    dti = {d: i for i, d in enumerate(sorted_d[: idx + 1])}
                    test_preds["mom_20d"][dk] = _mom_pred(closes_list, idx, 20, neutral_bps)
            test_preds["majority_from_train"][dk] = maj

        for arm_id in ARM_IDS:
            m = _directional_hit(test_preds[arm_id], closes, test, neutral_bps)
            arm_fold_rows[arm_id].append({"fold": fi, "test_dates": [test[0], test[-1]], **m})

    arms_out = [
        {
            "arm_id": arm_id,
            "protocol": "blocked_walkforward_test_only",
            "lens_source": "per_date_jsonl_myeongni_sasang",
            **_aggregate(arm_fold_rows[arm_id]),
        }
        for arm_id in ARM_IDS
    ]

    wf = _load_json(DEFAULT_WF)
    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    sasang_arm = next((a for a in arms_out if a["arm_id"] == "sasang_myeongni_only"), {})
    lens3_arm = next((a for a in arms_out if a["arm_id"] == "lens3_runtime"), {})

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-028",
        "prior_rq": "RQ-027",
        "window": {
            "eval_days": len(eval_dates),
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_folds": args.n_folds,
        },
        "lens_jsonl_meta": lens_meta,
        "blocked_walkforward_test_only": {"arms": arms_out},
        "compare": {
            "wf_majority_pooled_hr": majority_hr,
            "sasang_myeongni_pooled_hr": sasang_arm.get("pooled_test_directional_hit_rate"),
            "lens3_pooled_hr": lens3_arm.get("pooled_test_directional_hit_rate"),
            "sasang_vs_lens3_pp": (
                round(float(sasang_arm["pooled_test_directional_hit_rate"]) - float(lens3_arm["pooled_test_directional_hit_rate"]), 4)
                if sasang_arm.get("pooled_test_directional_hit_rate") is not None
                and lens3_arm.get("pooled_test_directional_hit_rate") is not None
                else None
            ),
        },
        "caveat_ko": "30d in-sample 우세 ≠ OOS alpha; macro/logos/field still snapshot; Track A 합선 금지.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
