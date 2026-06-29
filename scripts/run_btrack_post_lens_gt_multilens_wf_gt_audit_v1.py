#!/usr/bin/env python3
"""[HYPO] Post lens-gt: blocked WF replay + prod strict gt beat-bull audit for per_date multilens."""

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

from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _last_n_intersection_trading_dates,
)
from scripts.build_kospi_prophecy_wf_holdout_compare_v1 import (  # noqa: E402
    _actuals_for_dates,
    _blocked_folds,
    _hit_rate,
    _majority_label,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
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
)
from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses  # noqa: E402
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MACRO_BACKFILL_JSONL,
    load_lens_jsonl_by_day,
    load_macro_gate_by_day,
    static_lenses_for_eval_date,
)

DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_post_lens_gt_multilens_wf_gt_audit_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_PROD_LENS_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
SCHEMA = "btrack_post_lens_gt_multilens_wf_gt_audit_v1"

ARM_IDS = (
    "lens3_4ai_overlay",
    "lens3_runtime",
    "sasang_myeongni_only",
    "myeongni_single_lens",
    "always_bull",
    "majority_from_train",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _fold_gt_audit(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    hits = n = bull_n = 0
    for pred, act in pairs:
        if act not in ("bull", "bear", "neutral") or pred not in ("bull", "bear", "neutral"):
            continue
        n += 1
        if act == "bull":
            bull_n += 1
        if pred == act:
            hits += 1
    acc = (hits / n) if n else 0.0
    bull_control = (bull_n / n) if n else 0.0
    margin = round(acc - bull_control, 6)
    return {
        "n_scored": n,
        "test_accuracy": round(acc, 6),
        "always_bull_control": round(bull_control, 6),
        "margin_vs_always_bull": margin,
        "test_beats_always_bull_gt": margin > 0.0,
        "test_meets_or_beats_always_bull_gte": margin >= 0.0,
        "exact_tie_with_always_bull": margin == 0.0,
    }


def _aggregate_gt(folds: list[dict[str, Any]]) -> dict[str, Any]:
    gt_flags = [bool(f.get("test_beats_always_bull_gt")) for f in folds if f.get("n_scored")]
    gte_flags = [bool(f.get("test_meets_or_beats_always_bull_gte")) for f in folds if f.get("n_scored")]
    margins = [float(f["margin_vs_always_bull"]) for f in folds if f.get("margin_vs_always_bull") is not None]
    accs = [float(f["test_accuracy"]) for f in folds if f.get("test_accuracy") is not None]
    return {
        "mean_test_accuracy": round(sum(accs) / len(accs), 6) if accs else None,
        "fraction_test_beats_always_bull_gt": round(sum(1 for x in gt_flags if x) / len(gt_flags), 6)
        if gt_flags
        else None,
        "fraction_test_meets_or_beats_always_bull_gte": round(sum(1 for x in gte_flags if x) / len(gte_flags), 6)
        if gte_flags
        else None,
        "n_folds_gt_pass": sum(1 for m in margins if m > 0.0),
        "n_folds_exact_tie": sum(1 for m in margins if m == 0.0),
        "fold_margins_vs_always_bull": margins,
        "n_folds_scored": len(gt_flags),
    }


def _aggregate_directional(folds: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in folds if f.get("directional_hit_rate") is not None]
    total_n = sum(int(f.get("n_evaluated") or 0) for f in folds)
    total_hits = sum(int(f.get("price_hits") or 0) for f in folds)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(total_hits / total_n, 6) if total_n else None,
        "total_n_evaluated": total_n,
        "total_price_hits": total_hits,
        "n_folds_scored": len(rates),
        "fold_hit_rates": rates,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL_252)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument(
        "--include-macro-per-date",
        action="store_true",
        help="Use macro research backfill JSONL as-of for per_date multilens arms.",
    )
    ap.add_argument("--macro-jsonl", type=Path, default=DEFAULT_MACRO_BACKFILL_JSONL)
    ap.add_argument("--wf-compare-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--prod-lens-wf-json", type=Path, default=DEFAULT_PROD_LENS_WF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    for p in (args.panel_csv, args.kospi_csv, args.btc_csv, args.myeongni_jsonl, args.sasang_jsonl):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    if args.include_macro_per_date and not args.macro_jsonl.is_file():
        print(f"missing macro jsonl: {args.macro_jsonl}", file=sys.stderr)
        return 2
    if args.include_macro_per_date and args.output == DEFAULT_OUT:
        args.output = ROOT / "reports/btrack_post_lens_gt_multilens_wf_gt_audit_macro_v1_latest.json"

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    btc_rows = load_kospi_yf_rows(args.btc_csv)
    panel = _load_panel(args.panel_csv)
    closes = _load_closes(args.kospi_csv)
    rules = _read_json(EVOLUTION_RULES)
    neutral_bps = float(args.neutral_bps)
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})

    wf_dates = _last_n_intersection_trading_dates(kospi_rows, btc_rows, int(args.eval_days))
    actuals = _actuals_for_dates(
        kospi_rows,
        wf_dates,
        neutral_bps=neutral_bps,
        max_abs_ret=float(args.max_abs_daily_return),
    )
    eval_dates = sorted(d for d in wf_dates if d in actuals and d in panel and d in closes)
    folds = _blocked_folds(eval_dates, int(args.n_folds))
    if not folds:
        print("no wf folds", file=sys.stderr)
        return 2

    my_by_day, sa_by_day, lens_meta = load_lens_jsonl_by_day(args.myeongni_jsonl, args.sasang_jsonl)
    macro_gate_by_day: dict[str, dict[str, Any]] | None = None
    if args.include_macro_per_date:
        macro_gate_by_day = load_macro_gate_by_day(args.macro_jsonl)
        if lens_meta is not None:
            lens_meta = dict(lens_meta)
            lens_meta["macro_jsonl"] = str(args.macro_jsonl)
            lens_meta["macro_gate_days"] = len(macro_gate_by_day)
    baseline_lenses = load_static_lenses()
    catalog = ablation_arm_catalog(rules)
    lens_arms = {k: catalog[k] for k in catalog if k in ("lens3_4ai_overlay", "lens3_runtime", "sasang_myeongni_only", "myeongni_single_lens")}
    ensemble_cache = load_ensemble_kospi_per_date(eval_dates)

    gt_fold_rows: dict[str, list[dict[str, Any]]] = {a: [] for a in ARM_IDS}
    dir_fold_rows: dict[str, list[dict[str, Any]]] = {a: [] for a in ARM_IDS}

    for fi, (train, test) in enumerate(folds):
        train_actuals = {d: actuals[d] for d in train if d in actuals}
        maj = _majority_label(train_actuals, train)
        test_preds: dict[str, dict[str, str]] = {a: {} for a in ARM_IDS}

        for dk in test:
            if dk not in panel:
                continue
            day_lenses = static_lenses_for_eval_date(
                dk,
                sasang_by_day=sa_by_day,
                myeongni_by_day=my_by_day,
                baseline=baseline_lenses,
                macro_gate_by_day=macro_gate_by_day,
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
            test_preds["always_bull"][dk] = "bull"
            test_preds["majority_from_train"][dk] = maj

        for arm_id in ARM_IDS:
            pairs: list[tuple[str, str]] = []
            dir_pairs: list[tuple[str, str]] = []
            for dk in test:
                act = actuals.get(dk)
                pred = test_preds[arm_id].get(dk)
                if not act or not pred:
                    continue
                pairs.append((pred, act))
                if act == "neutral" or pred == "neutral":
                    continue
                dir_pairs.append((pred, act))
            gt = _fold_gt_audit(pairs)
            directional = _hit_rate(dir_pairs)
            gt_fold_rows[arm_id].append(
                {
                    "fold": fi,
                    "test_date_from": test[0],
                    "test_date_to": test[-1],
                    "train_majority_label": maj if arm_id == "majority_from_train" else None,
                    **gt,
                }
            )
            dir_fold_rows[arm_id].append(
                {
                    "fold": fi,
                    "test_date_from": test[0],
                    "test_date_to": test[-1],
                    **directional,
                }
            )

    arms_out: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        gt_agg = _aggregate_gt(gt_fold_rows[arm_id])
        dir_agg = _aggregate_directional(dir_fold_rows[arm_id])
        arms_out.append(
            {
                "arm_id": arm_id,
                "protocol": "blocked_walkforward_test_only_per_date_multilens",
                "lens_source": "per_date_jsonl_myeongni_sasang",
                "gt_audit_metric": "prod_strict_gt_accuracy_minus_always_bull_control",
                **gt_agg,
                **dir_agg,
                "gt_folds": gt_fold_rows[arm_id],
                "directional_folds": dir_fold_rows[arm_id],
            }
        )

    best_gt = max(
        (a for a in arms_out if a.get("fraction_test_beats_always_bull_gt") is not None),
        key=lambda a: float(a["fraction_test_beats_always_bull_gt"]),
        default={},
    )
    prod_lens = _load_json(args.prod_lens_wf_json)
    prod_gt_frac = ((prod_lens.get("aggregate") or {}).get("fraction_test_beats_always_bull") if prod_lens else None)
    wf_compare = _load_json(args.wf_compare_json)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "metric_wall_ko": (
            "blocked WF gt audit uses same fold geometry as kospi_prophecy_wf_holdout_compare; "
            "multilens fixed weights (no combo grid). Does not replace prod lens combo gt blocker."
        ),
        "window": {
            "eval_days": len(eval_dates),
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_folds": args.n_folds,
            "neutral_bps": neutral_bps,
            "n_panel_intersection": len(eval_dates),
        },
        "lens_jsonl_meta": lens_meta,
        "include_macro_per_date": bool(args.include_macro_per_date),
        "compare_pointers": {
            "prod_lens_combo_gt_fraction": prod_gt_frac,
            "wf_compare_per_date_ensemble_pooled": next(
                (
                    a.get("pooled_test_directional_hit_rate")
                    for a in ((wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or [])
                    if isinstance(a, dict) and a.get("arm_id") == "per_date_kospi_ensemble"
                ),
                None,
            ),
        },
        "blocked_walkforward_gt_audit": {"arms": arms_out},
        "best_by_gt_fraction": best_gt,
        "ledger_line": (
            f"Post lens-gt multilens WF gt audit: best={best_gt.get('arm_id')} "
            f"gt_frac={best_gt.get('fraction_test_beats_always_bull_gt')}; "
            f"prod combo gt_frac={prod_gt_frac}; no oper promotion."
        ),
        "operator_lines": [],
    }
    out["operator_lines"] = [
        "- [MULTILENS-WF-GT] research_only; prod lens combo gt unchanged.",
        f"- [MULTILENS-WF-GT] best_gt={best_gt.get('arm_id')} gt_frac={best_gt.get('fraction_test_beats_always_bull_gt')} "
        f"mean_acc={best_gt.get('mean_test_accuracy')}.",
        f"- [MULTILENS-WF-GT] lens3_4ai gt_frac="
        f"{next((a.get('fraction_test_beats_always_bull_gt') for a in arms_out if a['arm_id']=='lens3_4ai_overlay'), None)} "
        f"pooled_dir="
        f"{next((a.get('pooled_test_directional_hit_rate') for a in arms_out if a['arm_id']=='lens3_4ai_overlay'), None)}.",
        f"- [MULTILENS-WF-GT] prod combo gt_frac={prod_gt_frac}; SEND_GATE HOLD.",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in out["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
