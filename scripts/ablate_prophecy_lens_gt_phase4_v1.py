#!/usr/bin/env python3
"""[HYPO] Phase4 lens gt R&D — non-combo paths + inference anti-degeneracy shadow."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_ENSEMBLE = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_gt_phase4_ablation_v1_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _kospi_by_date(score: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in score.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "kospi":
            continue
        d = str(r.get("eval_date") or "")[:10]
        if d:
            out[d] = r
    return out


def _ensemble_kospi_by_date(ensemble: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in ensemble.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "kospi":
            continue
        d = str(r.get("eval_date") or "")[:10]
        if d:
            out[d] = r
    return out


def _acc_for_preds(rows: list[dict[str, Any]], pred_fn: Callable[[dict[str, Any]], str]) -> tuple[float, int, dict[str, int]]:
    hits = 0
    pred_counts = {"bull": 0, "bear": 0, "neutral": 0, "other": 0}
    for r in rows:
        pred = str(pred_fn(r) or "neutral").strip().lower()
        if pred in pred_counts:
            pred_counts[pred] += 1
        else:
            pred_counts["other"] += 1
        if pred == str(r.get("actual_direction") or "").strip().lower():
            hits += 1
    n = len(rows)
    return ((hits / n) if n else 0.0, hits, pred_counts)


def _params_dict_to_tuple(
    p: dict[str, float],
    *,
    include_source: bool,
    include_expanded: bool,
) -> tuple[float, ...]:
    if include_source and include_expanded:
        return (
            float(p["dz_self"]),
            float(p["dz_cross"]),
            float(p["w_self"]),
            float(p["w_cross"]),
            float(p.get("w_source_direction") or 0.0),
            float(p.get("w_self_mom") or 0.0),
            float(p.get("w_cross_mom") or 0.0),
            float(p.get("w_vol_spread") or 0.0),
            float(p["kospi_bull_bias"]),
            float(p["up_thr"]),
            float(p["down_thr"]),
        )
    if include_source:
        return (
            float(p["dz_self"]),
            float(p["dz_cross"]),
            float(p["w_self"]),
            float(p["w_cross"]),
            float(p.get("w_source_direction") or 0.0),
            float(p["kospi_bull_bias"]),
            float(p["up_thr"]),
            float(p["down_thr"]),
        )
    return (
        float(p["dz_self"]),
        float(p["dz_cross"]),
        float(p["w_self"]),
        float(p["w_cross"]),
        float(p["kospi_bull_bias"]),
        float(p["up_thr"]),
        float(p["down_thr"]),
    )


def _eval_non_combo_paths(
    *,
    wf: dict[str, Any],
    by_date: dict[str, dict[str, Any]],
    ens_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    paths: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
        ("score_row_predicted_direction", lambda r: str(r.get("predicted_direction") or "neutral")),
        ("ensemble_preliminary_direction", lambda r: str((ens_by_date.get(str(r.get("eval_date") or "")[:10]) or {}).get("preliminary_direction") or r.get("predicted_direction") or "neutral")),
        ("always_bull", lambda _r: "bull"),
        ("always_neutral", lambda _r: "neutral"),
        ("always_bear", lambda _r: "bear"),
    ]
    out: list[dict[str, Any]] = []
    fold_margins_all: dict[str, list[float]] = {pid: [] for pid, _ in paths}

    for path_id, pred_fn in paths:
        gt_flags: list[bool] = []
        for fold in wf.get("folds") or []:
            if not isinstance(fold, dict):
                continue
            test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
            test_rows = [by_date[d] for d in test_dates if d in by_date]
            acc, hits, pred_counts = _acc_for_preds(test_rows, pred_fn)
            bull_control = sum(1 for r in test_rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test_rows) if test_rows else 0.0
            margin = round(acc - bull_control, 6)
            fold_margins_all[path_id].append(margin)
            gt_flags.append(margin > 0.0)
        n = len(gt_flags)
        frac_gt = round(sum(1 for x in gt_flags if x) / n, 6) if n else 0.0
        out.append(
            {
                "path_id": path_id,
                "family": "non_combo_no_grid",
                "fraction_test_beats_always_bull_gt": frac_gt,
                "fold_margins_vs_prod_control": fold_margins_all[path_id],
                "max_fold_margin_vs_prod_control": max(fold_margins_all[path_id]) if fold_margins_all[path_id] else None,
                "n_folds_gt_pass": sum(1 for m in fold_margins_all[path_id] if m > 0.0),
                "n_folds_exact_tie": sum(1 for m in fold_margins_all[path_id] if m == 0.0),
            }
        )
        # fix mean_test_accuracy properly
        accs: list[float] = []
        for fold in wf.get("folds") or []:
            if not isinstance(fold, dict):
                continue
            test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
            test_rows = [by_date[d] for d in test_dates if d in by_date]
            acc, _, _ = _acc_for_preds(test_rows, pred_fn)
            accs.append(acc)
        out[-1]["mean_test_accuracy"] = round(sum(accs) / len(accs), 6) if accs else None

    return out


def _eval_combo_anti_degeneracy_shadow(
    *,
    wf: dict[str, Any],
    score: dict[str, Any],
    kospi_csv: Path,
    btc_csv: Path,
) -> list[dict[str, Any]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.run_prophecy_per_date_combo_walkforward_v1 import (
        _acc,
        _predict,
        _prior_map,
        _feature_map,
    )

    inputs = wf.get("inputs") if isinstance(wf.get("inputs"), dict) else {}
    include_source = bool(inputs.get("include_source_direction_signal"))
    include_expanded = bool(inputs.get("include_expanded_prior_features"))
    km = _prior_map(kospi_csv)
    bm = _prior_map(btc_csv)
    kf = _feature_map(kospi_csv)
    bf = _feature_map(btc_csv)
    by_date = _kospi_by_date(score)

    shadow_variants = [
        {"id": "prod_combo_replay", "cap_bull_bias": None, "min_bear_preds": 0},
        {"id": "anti_degen_cap_bull_bias_0p5", "cap_bull_bias": 0.5, "min_bear_preds": 0},
        {"id": "anti_degen_min_bear_preds_1", "cap_bull_bias": None, "min_bear_preds": 1},
    ]
    results: list[dict[str, Any]] = []

    for spec in shadow_variants:
        margins: list[float] = []
        degenerate_folds = 0
        for fold in wf.get("folds") or []:
            if not isinstance(fold, dict):
                continue
            pdict = fold.get("best_params_from_train")
            if not isinstance(pdict, dict):
                continue
            pd = dict(pdict)
            if spec["cap_bull_bias"] is not None:
                pd["kospi_bull_bias"] = min(float(pd.get("kospi_bull_bias") or 0.0), float(spec["cap_bull_bias"]))
            params = _params_dict_to_tuple(
                pd,
                include_source=include_source,
                include_expanded=include_expanded,
            )
            test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
            test_rows = [by_date[d] for d in test_dates if d in by_date]
            acc, hits, _ = _acc(
                test_rows,
                params,
                km,
                bm,
                kf,
                bf,
                include_source_direction_signal=include_source,
                include_expanded_prior_features=include_expanded,
            )
            bull_control = (
                sum(1 for r in test_rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test_rows)
                if test_rows
                else 0.0
            )
            always_bull_hits = int(round(bull_control * len(test_rows))) if test_rows else 0
            bull_preds = sum(
                1
                for r in test_rows
                if _predict(
                    r,
                    params,
                    km,
                    bm,
                    kf,
                    bf,
                    include_source_direction_signal=include_source,
                    include_expanded_prior_features=include_expanded,
                )
                == "bull"
            )
            if spec["min_bear_preds"] and bull_preds >= len(test_rows):
                acc = bull_control
                hits = always_bull_hits
            margin = round(acc - bull_control, 6)
            if margin == 0.0 and hits == always_bull_hits and bull_preds >= max(1, len(test_rows) - 1):
                degenerate_folds += 1
            margins.append(margin)

        n = len(margins)
        results.append(
            {
                "variant_id": spec["id"],
                "family": "inference_anti_degeneracy_shadow",
                "shadow_only": True,
                "prod_gt_unchanged": True,
                "fraction_test_beats_always_bull_gt": round(sum(1 for m in margins if m > 0.0) / n, 6) if n else 0.0,
                "fold_margins_vs_prod_control": margins,
                "max_fold_margin_vs_prod_control": max(margins) if margins else None,
                "n_folds_gt_pass": sum(1 for m in margins if m > 0.0),
                "n_folds_exact_tie": sum(1 for m in margins if m == 0.0),
                "n_folds_degenerate_all_bull": degenerate_folds,
                "mean_test_accuracy": round(sum(m + 0.0 for m in margins) / n + 0.0, 6) if n else None,
            }
        )
        # recompute mean accuracy from margins + control - skip, use fold replay accs
        accs: list[float] = []
        for fold in wf.get("folds") or []:
            if not isinstance(fold, dict):
                continue
            t = fold.get("test") if isinstance(fold.get("test"), dict) else {}
            if spec["id"] == "prod_combo_replay":
                accs.append(float(t.get("accuracy") or 0.0))
            else:
                fi = int(fold.get("fold_index", 0))
                if fi < len(margins):
                    bull = float(t.get("always_bull_control") or 0.0)
                    accs.append(round(bull + margins[fi], 6))
        results[-1]["mean_test_accuracy"] = round(sum(accs) / len(accs), 6) if accs else None

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--ensemble-json", type=Path, default=DEFAULT_ENSEMBLE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = _load(args.score_json)
    wf = _load(args.walkforward_json)
    ensemble = _load(args.ensemble_json)
    if not score or not wf:
        print("Missing score or walkforward JSON", file=sys.stderr)
        return 2

    by_date = _kospi_by_date(score)
    ens_by_date = _ensemble_kospi_by_date(ensemble)

    non_combo = _eval_non_combo_paths(wf=wf, by_date=by_date, ens_by_date=ens_by_date)
    anti_degen = _eval_combo_anti_degeneracy_shadow(
        wf=wf,
        score=score,
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
    )

    all_rows = non_combo + anti_degen
    best_gt = max(all_rows, key=lambda r: float(r.get("fraction_test_beats_always_bull_gt") or 0.0), default=None)

    report: dict[str, Any] = {
        "schema": "prophecy_lens_gt_phase4_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "phase": "4_non_combo_and_inference_anti_degeneracy_shadow",
        "inputs": {
            "score_json": str(args.score_json),
            "walkforward_json": str(args.walkforward_json),
            "ensemble_json": str(args.ensemble_json),
        },
        "non_combo_paths": non_combo,
        "inference_anti_degeneracy_shadow": anti_degen,
        "best_by_gt_fraction": best_gt,
        "verdict_ko": (
            f"phase4 non-combo+anti-degen shadow; best_gt={(best_gt or {}).get('path_id') or (best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')}; prod gt unchanged."
        ),
        "ledger_line": (
            f"Lens gt phase4: best={(best_gt or {}).get('path_id') or (best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')}; "
            "non-combo+anti-degen shadow only; no oper promotion."
        ),
        "operator_lines": [
            "- [LENS-P4] research_only; non-combo paths + inference anti-degeneracy shadow.",
            f"- [LENS-P4] best_gt={(best_gt or {}).get('path_id') or (best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')}.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
