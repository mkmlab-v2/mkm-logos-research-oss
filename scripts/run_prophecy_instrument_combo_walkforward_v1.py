# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.86, K:0.44, M:0.32}
# Balance: 91
# Purpose: Blocked walk-forward for instrument-combo (KOSPI mode + BTC thresholds)
# Keywords: prophecy, walkforward, instrument, combo, btc
#!/usr/bin/env python3
"""Walk-forward for the instrument-combo family (same policy as ``run_prophecy_instrument_combo_sweep_v1``).

Each fold fits ``(kospi_mode, btc_low_thr, btc_high_thr)`` on the train date block only,
then scores the test block. Requires a **dual-leg** score panel (KOSPI + BTC rows per eval_date)
and a readable BTC daily CSV for prior returns.

Output aggregate keys match ``prophecy_per_date_combo_walkforward_v1`` so promotion gates can reuse them.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_walkforward_v1_latest.json"
SCHEMA = "prophecy_instrument_combo_walkforward_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _prior_map(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _pred_from_prior(pr: float | None, *, low: float, high: float, fallback: str) -> str:
    if pr is None:
        return fallback
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _metrics(rows: list[dict[str, Any]], preds: list[str]) -> dict[str, Any]:
    n = 0
    h = 0
    for r, p in zip(rows, preds):
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            h += 1
    return {"price_directional_hit_rate": round(h / n, 6) if n else None, "n_evaluated": n, "price_hits": h}


def _acc(rows: list[dict[str, Any]], preds: list[str]) -> tuple[float, int]:
    m = _metrics(rows, preds)
    rate = float(m["price_directional_hit_rate"] or 0.0)
    return rate, int(m.get("price_hits") or 0)


def _instrument_preds(
    rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    kospi_mode: str,
    b_lo: float,
    b_hi: float,
) -> list[str]:
    preds: list[str] = []
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        old = str(r.get("predicted_direction") or "").strip().lower()
        if inst == "kospi":
            if kospi_mode == "causal":
                p = _pred_from_prior(km.get(ed), low=-0.06, high=-0.05, fallback=old if old in VALID else "neutral")
            else:
                p = kospi_mode
        else:
            p = _pred_from_prior(bm.get(ed), low=b_lo, high=b_hi, fallback=old if old in VALID else "neutral")
        preds.append(p)
    return preds


def _threshold_pairs(grid: list[float]) -> list[tuple[float, float]]:
    return [(lo, hi) for lo, hi in itertools.product(grid, grid) if lo < hi]


def _always_bull_baseline_acc(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    bull_preds = ["bull"] * len(rows)
    a, _ = _acc(rows, bull_preds)
    return a


def _train_selection_key(
    accuracy: float,
    bull_baseline: float,
    *,
    train_objective: str,
    beat_bull_train_weight: float,
    stability_penalty: float,
) -> tuple[float, ...]:
    """Lexicographic train score (higher is better)."""
    margin = accuracy - bull_baseline
    beats = 1.0 if accuracy > bull_baseline else 0.0
    stab = max(0.0, float(stability_penalty))
    obj = train_objective
    if obj == "beat_bull_first":
        return (beats, margin, accuracy)
    if obj == "margin_vs_bull":
        return (margin, accuracy, 0.0)
    if obj == "stability_margin":
        # Penalize train acc far from always-bull without a clear margin edge (regime proxy).
        dist = abs(accuracy - bull_baseline)
        score = margin - stab * dist
        return (beats, score, margin, accuracy)
    if obj == "accuracy" and beat_bull_train_weight > 0:
        return (beats * 10.0 + accuracy + beat_bull_train_weight * max(0.0, margin), accuracy, 0.0)
    if obj == "accuracy":
        return (accuracy, margin, 0.0)
    raise ValueError(f"unsupported train_objective: {train_objective}")


def _ensure_sweep_best_candidates(
    kospi_modes: list[str],
    pairs: list[tuple[float, float]],
    *,
    inject: bool,
    sweep_best_kospi: str,
    sweep_best_btc_lo: float,
    sweep_best_btc_hi: float,
) -> tuple[list[str], list[tuple[float, float]]]:
    modes = list(kospi_modes)
    prs = list(pairs)
    if not inject:
        return modes, prs
    if sweep_best_kospi not in modes:
        modes.append(sweep_best_kospi)
    anchor = (float(sweep_best_btc_lo), float(sweep_best_btc_hi))
    if anchor not in prs and anchor[0] < anchor[1]:
        prs.append(anchor)
    return modes, prs


def _train_dates_from_rows(train_rows: list[dict[str, Any]]) -> list[str]:
    return sorted({str(r.get("eval_date") or "")[:10] for r in train_rows if str(r.get("eval_date") or "").strip()})


def _combo_inner_cv_metrics(
    train_rows: list[dict[str, Any]],
    train_dates_sorted: list[str],
    *,
    k_mode: str,
    b_lo: float,
    b_hi: float,
    km: dict[str, float],
    bm: dict[str, float],
    inner_folds: int,
) -> tuple[float, float, int]:
    """Blocked inner CV on the outer-train block only (combo params fixed)."""
    if len(train_dates_sorted) < 2:
        return 0.0, 0.0, 0
    n_eff = max(2, min(int(inner_folds), len(train_dates_sorted)))
    specs = _blocked_walkforward_folds(train_dates_sorted, n_eff)
    inner_accs: list[float] = []
    inner_beats: list[bool] = []
    for _inner_train, inner_test_dates in specs:
        test_set = set(inner_test_dates)
        inner_test = [r for r in train_rows if str(r.get("eval_date"))[:10] in test_set]
        if not inner_test:
            continue
        preds = _instrument_preds(
            inner_test, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi
        )
        acc, _ = _acc(inner_test, preds)
        bull_frac = (
            sum(1 for r in inner_test if str(r.get("actual_direction") or "").strip().lower() == "bull")
            / len(inner_test)
        )
        inner_accs.append(acc)
        inner_beats.append(acc > bull_frac)
    if not inner_accs:
        return 0.0, 0.0, 0
    mean_inner = sum(inner_accs) / len(inner_accs)
    bull_beat_frac = sum(1 for b in inner_beats if b) / len(inner_beats)
    return mean_inner, bull_beat_frac, len(inner_accs)


def _rank_combos_on_train(
    train_rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    kospi_modes: list[str],
    pairs: list[tuple[float, float]],
    train_objective: str,
    beat_bull_train_weight: float,
    stability_penalty: float,
    selection_mode: str = "full-train",
    inner_folds: int = 3,
) -> list[tuple[str, float, float, float, tuple[float, ...], dict[str, Any]]]:
    """Return combos sorted (best first): (k_mode, b_lo, b_hi, full_train_acc, key, meta)."""
    bull_base = _always_bull_baseline_acc(train_rows)
    w = max(0.0, float(beat_bull_train_weight))
    obj = str(train_objective or "beat_bull_first").strip().lower()
    if obj not in ("accuracy", "margin_vs_bull", "beat_bull_first", "stability_margin"):
        raise ValueError(f"unsupported train_objective: {train_objective}")
    sel = str(selection_mode or "full-train").strip().lower()
    if sel not in ("full-train", "inner-cv"):
        raise ValueError(f"unsupported selection_mode: {selection_mode}")
    train_dates = _train_dates_from_rows(train_rows)
    ranked: list[tuple[str, float, float, float, tuple[float, ...], dict[str, Any]]] = []
    for k_mode, (b_lo, b_hi) in itertools.product(kospi_modes, pairs):
        preds = _instrument_preds(train_rows, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        a, _ = _acc(train_rows, preds)
        base_key = _train_selection_key(
            a,
            bull_base,
            train_objective=obj,
            beat_bull_train_weight=w,
            stability_penalty=stability_penalty,
        )
        meta: dict[str, Any] = {"selection_mode": sel}
        if sel == "inner-cv":
            mean_inner, inner_bull_frac, n_inner = _combo_inner_cv_metrics(
                train_rows,
                train_dates,
                k_mode=k_mode,
                b_lo=b_lo,
                b_hi=b_hi,
                km=km,
                bm=bm,
                inner_folds=inner_folds,
            )
            meta.update(
                {
                    "inner_cv_mean_test_accuracy": round(mean_inner, 6),
                    "inner_cv_fraction_beats_always_bull": round(inner_bull_frac, 6),
                    "inner_cv_n_folds": n_inner,
                }
            )
            # Lexicographic: inner bull-beat fraction, inner mean acc, then full-train objective.
            key = (inner_bull_frac, mean_inner, *base_key)
        else:
            key = base_key
        ranked.append((k_mode, b_lo, b_hi, a, key, meta))
    ranked.sort(key=lambda x: x[4], reverse=True)
    return ranked


def _best_combo_on_train(
    train_rows: list[dict[str, Any]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
    kospi_modes: list[str],
    pairs: list[tuple[float, float]],
    train_objective: str = "beat_bull_first",
    beat_bull_train_weight: float = 0.0,
    stability_penalty: float = 0.1,
) -> tuple[str, float, float] | None:
    ranked = _rank_combos_on_train(
        train_rows,
        km=km,
        bm=bm,
        kospi_modes=kospi_modes,
        pairs=pairs,
        train_objective=train_objective,
        beat_bull_train_weight=beat_bull_train_weight,
        stability_penalty=stability_penalty,
        selection_mode="full-train",
        inner_folds=3,
    )
    if not ranked:
        return None
    k_mode, b_lo, b_hi, _, _, _ = ranked[0]
    return (k_mode, b_lo, b_hi)


def _ensemble_majority_preds(
    rows: list[dict[str, Any]],
    combos: list[tuple[str, float, float]],
    *,
    km: dict[str, float],
    bm: dict[str, float],
) -> list[str]:
    if not combos:
        return []
    per_combo: list[list[str]] = []
    for k_mode, b_lo, b_hi in combos:
        per_combo.append(_instrument_preds(rows, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi))
    out: list[str] = []
    for i in range(len(rows)):
        votes: dict[str, int] = {}
        for preds in per_combo:
            p = preds[i]
            votes[p] = votes.get(p, 0) + 1
        best_p = max(votes.keys(), key=lambda k: (votes[k], k))
        out.append(best_p)
    return out


def _blocked_walkforward_folds(dates_sorted: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates_sorted)
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates_sorted[idx : idx + sz])
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


def _dual_leg_dates(rows: list[dict[str, Any]]) -> tuple[list[str], int]:
    by_date: dict[str, set[str]] = {}
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "").strip().lower()
        act = str(r.get("actual_direction") or "").strip().lower()
        if not ed or inst not in ("kospi", "btc") or act not in VALID:
            continue
        by_date.setdefault(ed, set()).add(inst)
    all_dates = sorted(by_date.keys())
    dual_dates = [d for d in all_dates if by_date[d] >= {"kospi", "btc"}]
    return dual_dates, len(all_dates)


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward for instrument-combo policy family (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--threshold-grid",
        type=str,
        default="-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.00,0.01,0.02,0.03,0.04,0.05",
    )
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument(
        "--train-objective",
        choices=("accuracy", "margin_vs_bull", "beat_bull_first", "stability_margin"),
        default="beat_bull_first",
        help="Train-block combo selection (default beat_bull_first: beat always-bull on train, then margin).",
    )
    ap.add_argument(
        "--stability-penalty",
        type=float,
        default=0.1,
        help="When --train-objective=stability_margin: penalize |train_acc - always_bull|.",
    )
    ap.add_argument(
        "--beat-bull-train-weight",
        type=float,
        default=0.0,
        help="Legacy: only when --train-objective=accuracy. Weight on train margin vs always-bull.",
    )
    ap.add_argument(
        "--test-policy",
        choices=("single", "ensemble-top3"),
        default="single",
        help="Test scoring: single best train combo, or majority vote of top-3 train combos.",
    )
    ap.add_argument(
        "--inject-sweep-best",
        action="store_true",
        help="Always include sweep-best anchor (kospi=bull, btc 3%%/4%%) in the candidate grid.",
    )
    ap.add_argument(
        "--selection-mode",
        choices=("full-train", "inner-cv"),
        default="full-train",
        help="Combo selection on outer-train block: full-train grid argmax or inner blocked CV.",
    )
    ap.add_argument(
        "--inner-folds",
        type=int,
        default=3,
        help="Inner blocked folds when --selection-mode=inner-cv (clamped to train date count).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.n_folds < 2:
        raise SystemExit("--n-folds must be >= 2")
    if not args.btc_csv.is_file():
        raise SystemExit(f"BTC CSV required for instrument-combo walk-forward: {args.btc_csv}")

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = sorted(
        [r for r in doc["rows"] if isinstance(r, dict)],
        key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))),
    )
    dates, all_dates_count = _dual_leg_dates(rows)
    if len(dates) < 2:
        raise SystemExit("need at least 2 distinct eval_dates with both kospi+btc legs")

    n_folds_requested = int(args.n_folds)
    n_folds_effective = max(2, min(n_folds_requested, len(dates)))
    n_folds_clamped = n_folds_effective != n_folds_requested

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv)

    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]
    pairs = _threshold_pairs(grid)
    kospi_modes = ["bull", "bear", "neutral", "causal"]
    kospi_modes, pairs = _ensure_sweep_best_candidates(
        kospi_modes,
        pairs,
        inject=bool(args.inject_sweep_best),
        sweep_best_kospi="bull",
        sweep_best_btc_lo=0.03,
        sweep_best_btc_hi=0.04,
    )

    fold_specs = _blocked_walkforward_folds(dates, n_folds_effective)
    fold_rows_out: list[dict[str, Any]] = []
    test_accs: list[float] = []
    beats_bull_flags: list[bool] = []

    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set = set(train_dates)
        test_set = set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        ranked = _rank_combos_on_train(
            train,
            km=km,
            bm=bm,
            kospi_modes=kospi_modes,
            pairs=pairs,
            train_objective=str(args.train_objective),
            beat_bull_train_weight=float(args.beat_bull_train_weight),
            stability_penalty=float(args.stability_penalty),
            selection_mode=str(args.selection_mode),
            inner_folds=int(args.inner_folds),
        )
        if not ranked:
            raise SystemExit(f"fold {fi}: no combo candidate")
        k_mode, b_lo, b_hi, _, _, best_meta = ranked[0]
        top3 = [(r[0], r[1], r[2]) for r in ranked[:3]]
        test_policy = str(args.test_policy or "single").strip().lower()
        if test_policy == "ensemble-top3":
            preds_tr = _ensemble_majority_preds(train, top3, km=km, bm=bm)
            preds_te = _ensemble_majority_preds(test, top3, km=km, bm=bm)
        else:
            preds_tr = _instrument_preds(train, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
            preds_te = _instrument_preds(test, km=km, bm=bm, kospi_mode=k_mode, b_lo=b_lo, b_hi=b_hi)
        train_acc, train_hit = _acc(train, preds_tr)
        test_acc, test_hit = _acc(test, preds_te)
        bull_test = sum(1 for r in test if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test) if test else 0.0
        beats = test_acc > bull_test
        test_accs.append(test_acc)
        beats_bull_flags.append(beats)
        fold_rows_out.append(
            {
                "fold_index": fi,
                "train_dates": train_dates,
                "test_dates": test_dates,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "best_params_from_train": {
                    "kospi_mode": k_mode,
                    "btc": {"low_thr": b_lo, "high_thr": b_hi},
                },
                "selection_meta": best_meta,
                "ensemble_top3_from_train": [
                    {"kospi_mode": t[0], "btc": {"low_thr": t[1], "high_thr": t[2]}} for t in top3
                ],
                "train": {"accuracy": round(train_acc, 6), "hits": train_hit, "n": len(train)},
                "test": {
                    "accuracy": round(test_acc, 6),
                    "hits": test_hit,
                    "n": len(test),
                    "always_bull_control": round(bull_test, 6),
                },
                "test_beats_always_bull": beats,
            }
        )

    mean_test = sum(test_accs) / len(test_accs) if test_accs else 0.0
    var = sum((x - mean_test) ** 2 for x in test_accs) / len(test_accs) if test_accs else 0.0
    stdev_test = math.sqrt(var) if test_accs else 0.0

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "threshold_grid": grid,
            "n_folds": n_folds_effective,
            "n_folds_requested": n_folds_requested,
            "n_folds_effective": n_folds_effective,
            "n_folds_clamped": n_folds_clamped,
            "n_distinct_eval_dates": len(dates),
            "n_distinct_eval_dates_in_score": all_dates_count,
            "n_dropped_non_dual_leg_dates": max(0, all_dates_count - len(dates)),
            "n_walkforward_folds": len(fold_specs),
            "note": "Instrument-combo walk-forward; fit (kospi_mode, btc thresholds) on train blocks only. Non-dual-leg dates are dropped.",
            "train_objective": str(args.train_objective),
            "stability_penalty": float(args.stability_penalty),
            "beat_bull_train_weight": float(args.beat_bull_train_weight),
            "test_policy": str(args.test_policy),
            "inject_sweep_best": bool(args.inject_sweep_best),
            "selection_mode": str(args.selection_mode),
            "inner_folds": int(args.inner_folds),
            "beat_always_bull_policy": "test_accuracy_gt_control",
        },
        "folds": fold_rows_out,
        "aggregate": {
            "mean_test_accuracy": round(mean_test, 6),
            "stdev_test_accuracy": round(stdev_test, 6),
            "min_test_accuracy": round(min(test_accs), 6) if test_accs else None,
            "max_test_accuracy": round(max(test_accs), 6) if test_accs else None,
            "fraction_test_beats_always_bull": round(sum(1 for x in beats_bull_flags if x) / len(beats_bull_flags), 6)
            if beats_bull_flags
            else None,
        },
        "note": "Same candidate family as prophecy_instrument_combo_sweep_v1; blocked chronological folds.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"folds={len(fold_rows_out)} mean_test_acc={out['aggregate']['mean_test_accuracy']} "
        f"stdev={out['aggregate']['stdev_test_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
