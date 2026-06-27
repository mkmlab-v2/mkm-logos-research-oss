# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.86, K:0.44, M:0.32}
# Balance: 91
# Purpose: Blocked chronological walk-forward for per-date lens combo family
# Keywords: prophecy, walkforward, validation, per-date, combo
#!/usr/bin/env python3
"""Blocked chronological walk-forward for the per-date causal lens combo family.

Same search grid and ``_predict`` rule as ``run_prophecy_per_date_combo_holdout_v1.py``:
for each fold, fit best params on the train date set only, then evaluate on the next
contiguous date block (test). B-track / research-only / not live routing.

Example: ``--n-folds 5`` splits unique eval_dates into five contiguous blocks
B0..B4 (oldest..newest). Folds are (train=B0, test=B1), (train=B0∪B1, test=B2), ...
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_walkforward_v1_latest.json"
SCHEMA = "prophecy_per_date_combo_walkforward_v1"


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
        if c2:
            out[ed] = (c1 - c2) / c2
    return out


def _feature_map(csv_path: Path) -> dict[str, dict[str, float]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, dict[str, float]] = {}
    closes: list[float] = []
    dates: list[str] = []
    for r in rows:
        try:
            closes.append(float(r["close"]))
            dates.append(str(r["date"])[:10])
        except (TypeError, ValueError):
            continue

    for i in range(1, len(closes)):
        d = dates[i]
        c0 = closes[i - 1]
        if c0 == 0:
            continue
        ret_1 = (closes[i] - c0) / c0
        ret_3 = 0.0
        ret_5 = 0.0
        ret_10 = 0.0
        if i >= 3 and closes[i - 3] != 0:
            ret_3 = (closes[i - 1] - closes[i - 3]) / closes[i - 3]
        if i >= 5 and closes[i - 5] != 0:
            ret_5 = (closes[i - 1] - closes[i - 5]) / closes[i - 5]
        if i >= 10 and closes[i - 10] != 0:
            ret_10 = (closes[i - 1] - closes[i - 10]) / closes[i - 10]

        def _mean_abs_ret(k: int) -> float:
            if i < k:
                return 0.0
            vals: list[float] = []
            for j in range(i - k + 1, i + 1):
                pc = closes[j - 1]
                cc = closes[j]
                if pc == 0:
                    continue
                vals.append(abs((cc - pc) / pc))
            return (sum(vals) / len(vals)) if vals else 0.0

        out[d] = {
            "ret_1": ret_1,
            "ret_3": ret_3,
            "ret_5": ret_5,
            "ret_10": ret_10,
            "vol_3": _mean_abs_ret(3),
            "vol_10": _mean_abs_ret(10),
        }
    return out


def _sign(x: float | None, dz: float) -> int:
    if x is None:
        return 0
    if x >= dz:
        return 1
    if x <= -dz:
        return -1
    return 0


def _dir_sign(v: Any) -> int:
    d = str(v or "").strip().lower()
    if d == "bull":
        return 1
    if d == "bear":
        return -1
    return 0


def _source_direction_value(row: dict[str, Any], field: str | None) -> Any:
    if field:
        return row.get(field)
    return row.get("predicted_direction")


def _predict(
    row: dict[str, Any],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
    source_direction_field: str | None = None,
) -> str:
    if include_source_direction_signal and include_expanded_prior_features:
        (
            dz_self,
            dz_cross,
            w_self,
            w_cross,
            w_source,
            w_self_mom,
            w_cross_mom,
            w_vol_spread,
            k_bias,
            up_thr,
            down_thr,
        ) = params
    elif include_source_direction_signal:
        dz_self, dz_cross, w_self, w_cross, w_source, k_bias, up_thr, down_thr = params
        w_self_mom = w_cross_mom = 0.0
        w_vol_spread = 0.0
    else:
        dz_self, dz_cross, w_self, w_cross, k_bias, up_thr, down_thr = params
        w_source = 0.0
        w_self_mom = w_cross_mom = 0.0
        w_vol_spread = 0.0
    inst = str(row.get("instrument") or "").strip().lower()
    ed = str(row.get("eval_date") or "").strip()[:10]
    if inst == "kospi":
        self_r, cross_r, bias = km.get(ed), bm.get(ed), k_bias
        self_f = kf.get(ed) or {}
        cross_f = bf.get(ed) or {}
    else:
        self_r, cross_r, bias = bm.get(ed), km.get(ed), 0.0
        self_f = bf.get(ed) or {}
        cross_f = kf.get(ed) or {}
    src_sig = (
        _dir_sign(_source_direction_value(row, source_direction_field))
        if include_source_direction_signal
        else 0
    )
    score = (w_self * _sign(self_r, dz_self)) + (w_cross * _sign(cross_r, dz_cross)) + (w_source * src_sig) + bias
    if include_expanded_prior_features:
        self_mom_sig = (
            _sign(self_f.get("ret_3"), dz_self)
            + _sign(self_f.get("ret_5"), dz_self)
            + _sign(self_f.get("ret_10"), dz_self)
        )
        cross_mom_sig = (
            _sign(cross_f.get("ret_3"), dz_cross)
            + _sign(cross_f.get("ret_5"), dz_cross)
            + _sign(cross_f.get("ret_10"), dz_cross)
        )
        score += w_self_mom * self_mom_sig
        score += w_cross_mom * cross_mom_sig
        score += w_vol_spread * _sign((self_f.get("vol_3") or 0.0) - (cross_f.get("vol_3") or 0.0), 0.0)
    if score >= up_thr:
        return "bull"
    if score <= down_thr:
        return "bear"
    return "neutral"


def _acc(
    rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
    source_direction_field: str | None = None,
) -> tuple[float, int]:
    h = 0
    for r in rows:
        if _predict(
            r,
            params,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
            source_direction_field=source_direction_field,
        ) == str(r.get("actual_direction") or "").strip().lower():
            h += 1
    return (h / len(rows)) if rows else 0.0, h


def _param_grid(*, include_source_direction_signal: bool, include_expanded_prior_features: bool) -> itertools.product:
    dz_vals = [0.0, 0.01, 0.02, 0.03]
    w_vals = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    src_w_vals = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    b_vals = [0.0, 0.5, 1.0]
    up_vals = [0.5, 1.0, 1.5]
    dn_vals = [-0.5, -1.0, -1.5]
    ext_w_vals = [-0.5, 0.0, 0.5]
    if include_source_direction_signal:
        if include_expanded_prior_features:
            dz_vals_exp = [0.0, 0.02]
            w_vals_exp = [-1.0, 0.0, 1.0]
            src_w_vals_exp = [-1.0, 0.0, 1.0]
            b_vals_exp = [0.0, 0.5]
            up_vals_exp = [0.5, 1.0]
            dn_vals_exp = [-0.5, -1.0]
            for p in itertools.product(
                dz_vals_exp,
                dz_vals_exp,
                w_vals_exp,
                w_vals_exp,
                src_w_vals_exp,
                ext_w_vals,
                ext_w_vals,
                ext_w_vals,
                b_vals_exp,
                up_vals_exp,
                dn_vals_exp,
            ):
                if p[10] >= p[9]:
                    continue
                yield p
        else:
            for p in itertools.product(dz_vals, dz_vals, w_vals, w_vals, src_w_vals, b_vals, up_vals, dn_vals):
                if p[7] >= p[6]:
                    continue
                yield p
    else:
        for p in itertools.product(dz_vals, dz_vals, w_vals, w_vals, b_vals, up_vals, dn_vals):
            if p[6] >= p[5]:
                continue
            yield p


def _best_params_on_train(
    train_rows: list[dict[str, Any]],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    train_objective: str,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
    source_direction_field: str | None = None,
) -> tuple[float, tuple[float, ...]] | None:
    best: tuple[float, float, tuple[float, ...] | None] = (-1.0, -1.0, None)
    bull_train = sum(1 for r in train_rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(train_rows) if train_rows else 0.0
    for p in _param_grid(
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=include_expanded_prior_features,
    ):
        a, _ = _acc(
            train_rows,
            p,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
            source_direction_field=source_direction_field,
        )
        if train_objective == "margin_vs_bull":
            primary = a - bull_train
            secondary = a
        else:
            primary = a
            secondary = a - bull_train
        if primary > best[0] or (primary == best[0] and secondary > best[1]):
            best = (primary, secondary, p)
    return (best[1], best[2]) if best[2] is not None else None


def _params_to_dict(
    p: tuple[float, ...],
    *,
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
) -> dict[str, float]:
    if include_source_direction_signal and include_expanded_prior_features and len(p) >= 11:
        return {
            "dz_self": p[0],
            "dz_cross": p[1],
            "w_self": p[2],
            "w_cross": p[3],
            "w_source_direction": p[4],
            "w_self_mom": p[5],
            "w_cross_mom": p[6],
            "w_vol_spread": p[7],
            "kospi_bull_bias": p[8],
            "up_thr": p[9],
            "down_thr": p[10],
        }
    if include_source_direction_signal:
        return {
            "dz_self": p[0],
            "dz_cross": p[1],
            "w_self": p[2],
            "w_cross": p[3],
            "w_source_direction": p[4],
            "kospi_bull_bias": p[5],
            "up_thr": p[6],
            "down_thr": p[7],
        }
    return {
        "dz_self": p[0],
        "dz_cross": p[1],
        "w_self": p[2],
        "w_cross": p[3],
        "kospi_bull_bias": p[4],
        "up_thr": p[5],
        "down_thr": p[6],
    }


def _blocked_walkforward_folds(dates_sorted: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    """Return list of (train_dates, test_dates) as sorted lists. Train = all blocks before test block."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward blocked validation for per-date lens combo family.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--target-instrument",
        choices=("btc", "kospi", "all"),
        default="btc",
        help="Primary training/eval target. btc keeps KOSPI only as cross-assist signal.",
    )
    ap.add_argument(
        "--train-objective",
        choices=("accuracy", "margin_vs_bull"),
        default="margin_vs_bull",
        help="How to pick params on train block before scoring test block.",
    )
    ap.add_argument("--n-folds", type=int, default=5, help="Contiguous date blocks (oldest..newest); folds = n_folds-1.")
    ap.add_argument(
        "--include-source-direction-signal",
        action="store_true",
        help="Include row.predicted_direction as an additional signed feature in grid search.",
    )
    ap.add_argument(
        "--include-expanded-prior-features",
        action="store_true",
        help="Include multi-horizon returns and vol spread features in grid search.",
    )
    ap.add_argument(
        "--source-direction-field",
        default=None,
        help="Score row field for source-direction signal (default predicted_direction).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    source_direction_field = str(args.source_direction_field).strip() or None

    if args.n_folds < 2:
        raise SystemExit("--n-folds must be >= 2")

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    all_rows = sorted(
        [r for r in doc["rows"] if isinstance(r, dict)],
        key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))),
    )
    if args.target_instrument == "all":
        rows = all_rows
    else:
        rows = [r for r in all_rows if str(r.get("instrument") or "").strip().lower() == args.target_instrument]
    if not rows:
        raise SystemExit(f"no rows after target-instrument filter: {args.target_instrument}")
    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    if len(dates) < 2:
        raise SystemExit(f"need at least 2 distinct eval_dates for walk-forward, got {len(dates)}")

    n_folds_requested = int(args.n_folds)
    n_folds_effective = max(2, min(n_folds_requested, len(dates)))
    n_folds_clamped = n_folds_effective != n_folds_requested

    km = _prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_map(args.btc_csv) if args.btc_csv.is_file() else {}
    kf = _feature_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bf = _feature_map(args.btc_csv) if args.btc_csv.is_file() else {}

    fold_specs = _blocked_walkforward_folds(dates, n_folds_effective)
    fold_rows_out: list[dict[str, Any]] = []
    test_accs: list[float] = []
    beats_bull_flags: list[bool] = []

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
            train_objective=args.train_objective,
            include_source_direction_signal=bool(args.include_source_direction_signal),
            include_expanded_prior_features=bool(args.include_expanded_prior_features),
            source_direction_field=source_direction_field,
        )
        if fitted is None:
            raise SystemExit(f"fold {fi}: no candidate params")
        _, p = fitted
        train_acc, train_hit = _acc(
            train,
            p,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=bool(args.include_source_direction_signal),
            include_expanded_prior_features=bool(args.include_expanded_prior_features),
            source_direction_field=source_direction_field,
        )
        test_acc, test_hit = _acc(
            test,
            p,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=bool(args.include_source_direction_signal),
            include_expanded_prior_features=bool(args.include_expanded_prior_features),
            source_direction_field=source_direction_field,
        )
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
                "best_params_from_train": _params_to_dict(
                    p,
                    include_source_direction_signal=bool(args.include_source_direction_signal),
                    include_expanded_prior_features=bool(args.include_expanded_prior_features),
                ),
                "train": {
                    "accuracy": round(train_acc, 6),
                    "hits": train_hit,
                    "n": len(train),
                },
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
            "target_instrument": args.target_instrument,
            "train_objective": args.train_objective,
            "include_source_direction_signal": bool(args.include_source_direction_signal),
            "include_expanded_prior_features": bool(args.include_expanded_prior_features),
            "source_direction_field": source_direction_field,
            "n_rows_after_target_filter": len(rows),
            "n_folds": n_folds_effective,
            "n_folds_requested": n_folds_requested,
            "n_folds_effective": n_folds_effective,
            "n_folds_clamped": n_folds_clamped,
            "n_distinct_eval_dates": len(dates),
            "n_walkforward_folds": len(fold_specs),
            "note": "Blocked chronological walk-forward: test block f uses only params fit on dates strictly before that block.",
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
        "note": "Same grid as prophecy_per_date_combo_holdout_v1; multiple contiguous test blocks for stability read.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"folds={len(fold_rows_out)} mean_test_acc={out['aggregate']['mean_test_accuracy']} "
        f"stdev={out['aggregate']['stdev_test_accuracy']} beat_bull_frac={out['aggregate']['fraction_test_beats_always_bull']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
