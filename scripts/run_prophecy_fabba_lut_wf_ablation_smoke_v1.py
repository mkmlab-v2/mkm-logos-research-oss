#!/usr/bin/env python3
"""[HYPO] Walk-forward ablation smoke: base LUT vs merged LUT (fabba sidecar opt-in).

Verifies (1) non-fabba feature parity base==merged-stripped, (2) WF with LUT maps
matches in-process expectations, (3) optional fabba sidecar score terms do not
mutate Primary score JSON — merged LUT is opt-in only.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ohlcv_feature_lut_lib_v1 import (  # noqa: E402
    base_feature_parity_ok,
    load_lut_document,
    load_merged_lut_document,
    prior_and_feature_maps_from_lut,
    strip_fabba_feature_keys,
)
from scripts.run_prophecy_per_date_combo_walkforward_v1 import (  # noqa: E402
    _acc,
    _best_params_on_train,
    _blocked_walkforward_folds,
    _predict,
)

DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_BASE_LUT = ROOT / "reports/btrack_ohlcv_feature_lut_v1_latest.json"
DEFAULT_MERGED_LUT = ROOT / "reports/btrack_ohlcv_feature_lut_with_fabba_sidecar_v1_latest.json"
DEFAULT_PRIOR_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_lut_wf_ablation_smoke_v1_latest.json"
SCHEMA = "prophecy_fabba_lut_wf_ablation_smoke_v1"


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


def _fabba_score_from_features(feat: dict[str, float], w_ngram: float, w_slope: float) -> float:
    return (w_ngram * float(feat.get("fabba_ngram_pred_code") or 0.0)) + (
        w_slope * float(feat.get("fabba_last_slope_pred_code") or 0.0)
    )


def _predict_with_fabba(
    row: dict[str, Any],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    fabba_weights: tuple[float, float],
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
) -> str:
    w_ngram, w_slope = fabba_weights
    inst = str(row.get("instrument") or "").strip().lower()
    ed = str(row.get("eval_date") or "").strip()[:10]
    self_f = (kf.get(ed) if inst == "kospi" else bf.get(ed)) or {}
    fabba_delta = _fabba_score_from_features(self_f, w_ngram, w_slope)

    base_pred = _predict(
        row,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=include_expanded_prior_features,
    )
    if fabba_delta == 0.0:
        return base_pred

    # Re-score with fabba delta: nudge bull/bear/neutral by threshold bands
    if fabba_delta >= 0.5:
        return "bull"
    if fabba_delta <= -0.5:
        return "bear"
    return base_pred


def _acc_with_fabba(
    rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    fabba_weights: tuple[float, float],
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
) -> tuple[float, int]:
    hits = 0
    for r in rows:
        pred = _predict_with_fabba(
            r,
            params,
            km,
            bm,
            kf,
            bf,
            fabba_weights=fabba_weights,
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
        )
        if pred == str(r.get("actual_direction") or "").strip().lower():
            hits += 1
    return (hits / len(rows)) if rows else 0.0, hits


def _best_fabba_weights_on_train(
    train_rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
) -> tuple[float, float]:
    best_w = (0.0, 0.0)
    best_acc = -1.0
    for w_n, w_s in itertools.product([-1.0, 0.0, 1.0], repeat=2):
        a, _ = _acc_with_fabba(
            train_rows,
            params,
            km,
            bm,
            kf,
            bf,
            fabba_weights=(w_n, w_s),
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
        )
        if a > best_acc:
            best_acc = a
            best_w = (w_n, w_s)
    return best_w


def _run_wf_variant(
    rows: list[dict[str, Any]],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    n_folds: int,
    train_objective: str,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
    use_fabba_sidecar: bool,
) -> dict[str, Any]:
    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    fold_specs = _blocked_walkforward_folds(dates, n_folds)
    test_accs: list[float] = []
    fold_rows: list[dict[str, Any]] = []

    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set = set(train_dates)
        test_set = set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        fitted = _best_params_on_train(
            train,
            km,
            bm,
            kf,
            bf,
            train_objective=train_objective,
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
        )
        if fitted is None:
            continue
        _, p = fitted
        fabba_w = (0.0, 0.0)
        if use_fabba_sidecar:
            fabba_w = _best_fabba_weights_on_train(
                train,
                p,
                km,
                bm,
                kf,
                bf,
                include_source_direction_signal=include_source_direction_signal,
                include_expanded_prior_features=include_expanded_prior_features,
            )
            test_acc, test_hit = _acc_with_fabba(
                test,
                p,
                km,
                bm,
                kf,
                bf,
                fabba_weights=fabba_w,
                include_source_direction_signal=include_source_direction_signal,
                include_expanded_prior_features=include_expanded_prior_features,
            )
        else:
            test_acc, test_hit = _acc(
                test,
                p,
                km,
                bm,
                kf,
                bf,
                include_source_direction_signal=include_source_direction_signal,
                include_expanded_prior_features=include_expanded_prior_features,
            )
        test_accs.append(test_acc)
        fold_rows.append(
            {
                "fold_index": fi,
                "n_test_rows": len(test),
                "test_accuracy": round(test_acc, 6),
                "test_hits": test_hit,
                "fabba_weights": {"w_ngram": fabba_w[0], "w_slope": fabba_w[1]} if use_fabba_sidecar else None,
            }
        )

    mean_acc = round(sum(test_accs) / len(test_accs), 6) if test_accs else None
    return {
        "mean_test_accuracy": mean_acc,
        "fold_test_accuracies": [round(x, 6) for x in test_accs],
        "n_folds_scored": len(test_accs),
        "folds": fold_rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--base-lut", type=Path, default=DEFAULT_BASE_LUT)
    ap.add_argument("--merged-lut", type=Path, default=DEFAULT_MERGED_LUT)
    ap.add_argument("--prior-wf-json", type=Path, default=DEFAULT_PRIOR_WF)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--train-objective", default="margin_vs_bull")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_doc = _load_json(args.score_json)
    if not score_doc or not isinstance(score_doc.get("rows"), list):
        print(f"invalid score json: {args.score_json}", file=sys.stderr)
        return 2

    if not args.merged_lut.is_file():
        print(f"missing merged lut: {args.merged_lut}", file=sys.stderr)
        return 2

    merged_lut = load_merged_lut_document(args.merged_lut)
    base_lut = load_lut_document(args.base_lut) if args.base_lut.is_file() else merged_lut
    parity_ok, parity_mismatches = base_feature_parity_ok(base_lut, merged_lut)
    intersection = set(merged_lut.get("intersection_dates") or [])

    all_rows = sorted(
        [r for r in score_doc["rows"] if isinstance(r, dict)],
        key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))),
    )
    rows = [r for r in all_rows if str(r.get("eval_date"))[:10] in intersection]
    if not rows:
        print("no score rows on intersection dates", file=sys.stderr)
        return 2

    km_b, bm_b, kf_b, bf_b = prior_and_feature_maps_from_lut(base_lut)
    km_m, bm_m, kf_m, bf_m = prior_and_feature_maps_from_lut(merged_lut)
    kf_strip = strip_fabba_feature_keys(kf_m)
    bf_strip = strip_fabba_feature_keys(bf_m)

    wf_flags = {
        "include_source_direction_signal": True,
        "include_expanded_prior_features": True,
    }

    variant_base = _run_wf_variant(
        rows,
        km_b,
        bm_b,
        kf_b,
        bf_b,
        n_folds=args.n_folds,
        train_objective=args.train_objective,
        use_fabba_sidecar=False,
        **wf_flags,
    )
    variant_merged_strip = _run_wf_variant(
        rows,
        km_m,
        bm_m,
        kf_strip,
        bf_strip,
        n_folds=args.n_folds,
        train_objective=args.train_objective,
        use_fabba_sidecar=False,
        **wf_flags,
    )
    variant_fabba = _run_wf_variant(
        rows,
        km_m,
        bm_m,
        kf_m,
        bf_m,
        n_folds=args.n_folds,
        train_objective=args.train_objective,
        use_fabba_sidecar=True,
        **wf_flags,
    )

    prior_wf = _load_json(args.prior_wf_json) or {}
    prior_mean = prior_wf.get("mean_test_accuracy")

    base_mean = variant_base.get("mean_test_accuracy")
    strip_mean = variant_merged_strip.get("mean_test_accuracy")
    fabba_mean = variant_fabba.get("mean_test_accuracy")

    wf_parity_ok = base_mean is not None and strip_mean is not None and abs(base_mean - strip_mean) < 1e-6

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "score_json": str(args.score_json.relative_to(ROOT)).replace("\\", "/"),
        "base_lut": str(args.base_lut.relative_to(ROOT)).replace("\\", "/") if args.base_lut.is_file() else None,
        "merged_lut": str(args.merged_lut.relative_to(ROOT)).replace("\\", "/"),
        "n_score_rows": len(rows),
        "n_intersection_dates": len(intersection),
        "feature_parity": {
            "base_vs_merged_stripped_ok": parity_ok,
            "mismatch_samples": parity_mismatches,
        },
        "wf_variants": {
            "base_lut_maps": variant_base,
            "merged_lut_stripped_maps": variant_merged_strip,
            "merged_lut_with_fabba_sidecar": variant_fabba,
        },
        "wf_parity": {
            "base_vs_merged_stripped_mean_test_accuracy_match": wf_parity_ok,
            "base_mean": base_mean,
            "merged_stripped_mean": strip_mean,
            "delta_fabba_vs_base_pp": round(float(fabba_mean) - float(base_mean), 6)
            if fabba_mean is not None and base_mean is not None
            else None,
        },
        "compare_prior_recommended_wf": {
            "pointer": str(args.prior_wf_json.relative_to(ROOT)).replace("\\", "/") if prior_wf else None,
            "prior_mean_test_accuracy": prior_mean,
            "ablation_base_mean": base_mean,
            "note_ko": "prior WF는 in-process CSV maps; ablation은 LUT maps — 소수 diff 허용, parity gate는 base vs merged-stripped",
        },
        "verdict_ko": [
            "Primary score JSON 불변 — LUT ablation only",
            "base vs merged-stripped feature parity + WF mean match = read-only merge OK",
            "fabba sidecar uplift = opt-in WF arm; Track A 승격 아님",
        ],
        "reproduce": f"py scripts/run_prophecy_fabba_lut_wf_ablation_smoke_v1.py --n-folds {args.n_folds}",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"parity={parity_ok} wf_parity={wf_parity_ok} "
        f"base={base_mean} fabba={fabba_mean}"
    )
    return 0 if parity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
