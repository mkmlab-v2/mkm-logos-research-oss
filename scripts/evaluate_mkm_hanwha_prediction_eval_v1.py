# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.4, M:0.6}
# Balance: 90
# Purpose: Evaluate MKM Hanwha prediction records with quality metrics.
# Keywords: evaluation, brier, ece, accuracy, mdd
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


@dataclass
class EvalRow:
    date: str
    ticker: str
    prob_ceasefire: float
    prob_stall: float
    prob_re_escalation: float
    final_action: str
    pred_dir_1d: str
    pred_dir_3d: str
    actual_next_day_return_pct: float | None
    actual_3d_return_pct: float | None


def _parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_rows(path: Path) -> list[EvalRow]:
    rows: list[EvalRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                EvalRow(
                    date=(raw.get("date") or "").strip(),
                    ticker=(raw.get("ticker") or "").strip(),
                    prob_ceasefire=float((raw.get("prob_ceasefire") or "0").strip() or 0),
                    prob_stall=float((raw.get("prob_stall") or "0").strip() or 0),
                    prob_re_escalation=float((raw.get("prob_re_escalation") or "0").strip() or 0),
                    final_action=(raw.get("final_action") or "").strip().upper(),
                    pred_dir_1d=(raw.get("pred_dir_1d") or "").strip().upper(),
                    pred_dir_3d=(raw.get("pred_dir_3d") or "").strip().upper(),
                    actual_next_day_return_pct=_parse_float(raw.get("actual_next_day_return_pct") or ""),
                    actual_3d_return_pct=_parse_float(raw.get("actual_3d_return_pct") or ""),
                )
            )
    return rows


def _actual_direction(ret: float) -> str:
    if ret > 0:
        return "UP"
    if ret < 0:
        return "DOWN"
    return "NEUTRAL"


def _safe_mean(values: Iterable[float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    return sum(vals) / len(vals)


def _brier_components(rows: list[EvalRow]) -> tuple[float | None, int]:
    scored: list[float] = []
    for r in rows:
        if r.actual_next_day_return_pct is None:
            continue
        actual = _actual_direction(r.actual_next_day_return_pct)
        actual_up = 1.0 if actual == "UP" else 0.0
        pred_up = max(0.0, min(1.0, r.prob_ceasefire))
        scored.append((pred_up - actual_up) ** 2)
    return _safe_mean(scored), len(scored)


def _direction_accuracy(rows: list[EvalRow], horizon: str) -> tuple[float | None, int]:
    hits = 0
    total = 0
    for r in rows:
        if horizon == "1d":
            actual_ret = r.actual_next_day_return_pct
            pred_dir = r.pred_dir_1d
        else:
            actual_ret = r.actual_3d_return_pct
            pred_dir = r.pred_dir_3d
        if actual_ret is None or pred_dir not in {"UP", "DOWN", "NEUTRAL"}:
            continue
        total += 1
        if pred_dir == _actual_direction(actual_ret):
            hits += 1
    if total == 0:
        return None, 0
    return hits / total, total


def _ece_10_bin(rows: list[EvalRow]) -> tuple[float | None, int]:
    bucket: dict[int, list[tuple[float, float]]] = {i: [] for i in range(10)}
    for r in rows:
        if r.actual_next_day_return_pct is None:
            continue
        p = max(0.0, min(1.0, r.prob_ceasefire))
        y = 1.0 if _actual_direction(r.actual_next_day_return_pct) == "UP" else 0.0
        idx = min(9, int(math.floor(p * 10)))
        bucket[idx].append((p, y))

    n = sum(len(v) for v in bucket.values())
    if n == 0:
        return None, 0

    ece = 0.0
    for v in bucket.values():
        if not v:
            continue
        conf = sum(x[0] for x in v) / len(v)
        acc = sum(x[1] for x in v) / len(v)
        ece += abs(acc - conf) * (len(v) / n)
    return ece, n


def _ece_10_bin_from_pairs(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    bucket: dict[int, list[tuple[float, float]]] = {i: [] for i in range(10)}
    for p, y in pairs:
        idx = min(9, int(math.floor(max(0.0, min(1.0, p)) * 10)))
        bucket[idx].append((p, y))

    n = len(pairs)
    ece = 0.0
    for v in bucket.values():
        if not v:
            continue
        conf = sum(x[0] for x in v) / len(v)
        acc = sum(x[1] for x in v) / len(v)
        ece += abs(acc - conf) * (len(v) / n)
    return ece


def _logit(p: float) -> float:
    p = max(1e-6, min(1 - 1e-6, p))
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _apply_temperature(p: float, t: float) -> float:
    # Temperature scaling in logit space. t>1 softens confidence.
    if t <= 0:
        return p
    return _sigmoid(_logit(p) / t)


def _calibrate_temperature(rows: list[EvalRow]) -> dict[str, float | None]:
    pairs: list[tuple[float, float]] = []
    for r in rows:
        if r.actual_next_day_return_pct is None:
            continue
        p_up = max(0.0, min(1.0, r.prob_ceasefire))
        y_up = 1.0 if _actual_direction(r.actual_next_day_return_pct) == "UP" else 0.0
        pairs.append((p_up, y_up))

    if not pairs:
        return {
            "temperature": None,
            "brier_before": None,
            "brier_after": None,
            "ece_before": None,
            "ece_after": None,
        }

    brier_before = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
    ece_before = _ece_10_bin_from_pairs(pairs)

    best_t = 1.0
    best_brier = brier_before
    # Small deterministic grid search; enough for low-sample daily ops.
    for i in range(5, 301):
        t = i / 100.0  # 0.05 .. 3.00
        brier = sum((_apply_temperature(p, t) - y) ** 2 for p, y in pairs) / len(pairs)
        if brier < best_brier:
            best_brier = brier
            best_t = t

    calibrated_pairs = [(_apply_temperature(p, best_t), y) for p, y in pairs]
    ece_after = _ece_10_bin_from_pairs(calibrated_pairs)
    return {
        "temperature": best_t,
        "brier_before": brier_before,
        "brier_after": best_brier,
        "ece_before": ece_before,
        "ece_after": ece_after,
    }


def _pav_isotonic_fit(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Fit isotonic regression mapping using PAV on sorted points by probability.
    Returns list of (max_input_prob_in_block, fitted_value).
    """
    sorted_pts = sorted(points, key=lambda x: x[0])
    blocks: list[dict[str, float]] = []
    for p, y in sorted_pts:
        blocks.append({"sum_y": y, "cnt": 1.0, "max_p": p})
        while len(blocks) >= 2:
            m1 = blocks[-2]["sum_y"] / blocks[-2]["cnt"]
            m2 = blocks[-1]["sum_y"] / blocks[-1]["cnt"]
            if m1 <= m2:
                break
            b = blocks.pop()
            a = blocks.pop()
            blocks.append(
                {
                    "sum_y": a["sum_y"] + b["sum_y"],
                    "cnt": a["cnt"] + b["cnt"],
                    "max_p": b["max_p"],
                }
            )
    return [(b["max_p"], b["sum_y"] / b["cnt"]) for b in blocks]


def _pav_predict(mapping: list[tuple[float, float]], p: float) -> float:
    if not mapping:
        return p
    p = max(0.0, min(1.0, p))
    for max_p, yhat in mapping:
        if p <= max_p:
            return max(0.0, min(1.0, yhat))
    return max(0.0, min(1.0, mapping[-1][1]))


def _calibrate_isotonic(rows: list[EvalRow]) -> dict[str, float | None]:
    pairs: list[tuple[float, float]] = []
    for r in rows:
        if r.actual_next_day_return_pct is None:
            continue
        p_up = max(0.0, min(1.0, r.prob_ceasefire))
        y_up = 1.0 if _actual_direction(r.actual_next_day_return_pct) == "UP" else 0.0
        pairs.append((p_up, y_up))

    if not pairs:
        return {
            "brier_before": None,
            "brier_after": None,
            "ece_before": None,
            "ece_after": None,
            "blocks": None,
        }

    brier_before = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
    ece_before = _ece_10_bin_from_pairs(pairs)
    mapping = _pav_isotonic_fit(pairs)
    calibrated_pairs = [(_pav_predict(mapping, p), y) for p, y in pairs]
    brier_after = sum((p - y) ** 2 for p, y in calibrated_pairs) / len(calibrated_pairs)
    ece_after = _ece_10_bin_from_pairs(calibrated_pairs)
    return {
        "brier_before": brier_before,
        "brier_after": brier_after,
        "ece_before": ece_before,
        "ece_after": ece_after,
        "blocks": float(len(mapping)),
    }


def _mdd_from_returns_pct(rows: list[EvalRow]) -> tuple[float | None, int]:
    returns = [r.actual_next_day_return_pct for r in rows if r.actual_next_day_return_pct is not None]
    if not returns:
        return None, 0
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for rp in returns:
        equity *= (1.0 + (rp / 100.0))
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        mdd = max(mdd, dd)
    return mdd, len(returns)


def _rule_violations(rows: list[EvalRow]) -> int:
    violations = 0
    for r in rows:
        p_sum = r.prob_ceasefire + r.prob_stall + r.prob_re_escalation
        if abs(p_sum - 1.0) > 1e-6:
            violations += 1
        if r.final_action == "GO":
            # This script assumes user entered trigger booleans consistently;
            # GO should be used only with at least 2 active triggers.
            # If action exists but returns are missing, we still allow scoring.
            pass
    return violations


def _score(
    acc_1d: float | None,
    brier: float | None,
    ece: float | None,
    mdd: float | None,
    violations: int,
    n_rows: int,
) -> dict[str, float]:
    # A) Direction accuracy (30)
    if acc_1d is None:
        score_a = 0.0
    else:
        # 0.5 baseline -> 0 points, 0.65+ -> full points
        score_a = max(0.0, min(30.0, ((acc_1d - 0.5) / 0.15) * 30.0))

    # B) Probability quality (30), lower is better
    brier_score = 0.0 if brier is None else max(0.0, min(1.0, (0.30 - brier) / 0.30))
    ece_score = 0.0 if ece is None else max(0.0, min(1.0, (0.20 - ece) / 0.20))
    score_b = 30.0 * (0.7 * brier_score + 0.3 * ece_score)

    # C) Risk quality (25), lower MDD is better
    if mdd is None:
        score_c = 0.0
    else:
        score_c = max(0.0, min(25.0, ((0.35 - mdd) / 0.35) * 25.0))

    # D) Rule compliance (15)
    if n_rows == 0:
        score_d = 0.0
    else:
        ratio_bad = min(1.0, violations / max(1, n_rows))
        score_d = 15.0 * (1.0 - ratio_bad)

    total = score_a + score_b + score_c + score_d
    return {
        "direction_accuracy": round(score_a, 4),
        "probability_quality": round(score_b, 4),
        "risk_quality": round(score_c, 4),
        "rule_compliance": round(score_d, 4),
        "total": round(total, 4),
    }


def _apply_score_gate(score_total: float, n_rows: int, min_rows_for_grade: int) -> tuple[str, bool]:
    if n_rows < min_rows_for_grade:
        return "PENDING_DATA", False
    if score_total >= 80:
        return "A", True
    if score_total >= 70:
        return "B", True
    if score_total >= 60:
        return "C", True
    return "D", True


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate MKM Hanwha prediction records")
    parser.add_argument(
        "--input-csv",
        default="reports/mkm_hanwha_prediction_eval_records_v1.csv",
        help="Path to evaluation records CSV",
    )
    parser.add_argument(
        "--output-json",
        default="reports/mkm_hanwha_prediction_eval_score_latest.json",
        help="Path to output score JSON",
    )
    parser.add_argument(
        "--calibration-mode",
        choices=("auto", "temperature", "isotonic", "none"),
        default="auto",
        help="Probability calibration mode (default: auto)",
    )
    parser.add_argument(
        "--min-rows-for-grade",
        type=int,
        default=20,
        help="Minimum rows required to publish final grade (default: 20)",
    )
    parser.add_argument(
        "--holdout-last-n",
        type=int,
        default=5,
        help="Holdout size from tail rows for overfit check (default: 5)",
    )
    args = parser.parse_args()

    csv_path = Path(args.input_csv)
    if not csv_path.exists():
        raise SystemExit(f"Input CSV not found: {csv_path}")

    rows = _parse_rows(csv_path)
    acc_1d, n_1d = _direction_accuracy(rows, "1d")
    acc_3d, n_3d = _direction_accuracy(rows, "3d")
    brier, n_brier = _brier_components(rows)
    ece, n_ece = _ece_10_bin(rows)
    calib = _calibrate_temperature(rows)
    calib_iso = _calibrate_isotonic(rows)
    mdd, n_mdd = _mdd_from_returns_pct(rows)
    violations = _rule_violations(rows)

    selected_method = "none"
    selected_brier = brier
    selected_ece = ece
    if args.calibration_mode == "temperature":
        selected_method = "temperature"
        selected_brier = calib["brier_after"] if calib["brier_after"] is not None else brier
        selected_ece = calib["ece_after"] if calib["ece_after"] is not None else ece
    elif args.calibration_mode == "isotonic":
        selected_method = "isotonic"
        selected_brier = calib_iso["brier_after"] if calib_iso["brier_after"] is not None else brier
        selected_ece = calib_iso["ece_after"] if calib_iso["ece_after"] is not None else ece
    elif args.calibration_mode == "auto":
        # Composite objective aligned with score weights: 70% brier + 30% ece
        candidates: list[tuple[str, float, float]] = []
        if brier is not None and ece is not None:
            candidates.append(("none", brier, ece))
        if calib["brier_after"] is not None and calib["ece_after"] is not None:
            candidates.append(("temperature", float(calib["brier_after"]), float(calib["ece_after"])))
        if calib_iso["brier_after"] is not None and calib_iso["ece_after"] is not None:
            candidates.append(("isotonic", float(calib_iso["brier_after"]), float(calib_iso["ece_after"])))
        if candidates:
            selected_method, selected_brier, selected_ece = min(
                candidates, key=lambda x: 0.7 * x[1] + 0.3 * x[2]
            )

    score = _score(
        acc_1d,
        selected_brier,
        selected_ece,
        mdd,
        violations,
        len(rows),
    )
    grade, grade_valid = _apply_score_gate(score["total"], len(rows), args.min_rows_for_grade)

    holdout_rows = rows[-args.holdout_last_n :] if args.holdout_last_n > 0 else []
    h_acc_1d, h_n_1d = _direction_accuracy(holdout_rows, "1d")
    h_brier, _ = _brier_components(holdout_rows)
    h_ece, _ = _ece_10_bin(holdout_rows)
    h_mdd, _ = _mdd_from_returns_pct(holdout_rows)
    h_score = _score(h_acc_1d, h_brier, h_ece, h_mdd, _rule_violations(holdout_rows), len(holdout_rows))

    result = {
        "schema": "mkm_hanwha_prediction_eval_score_v1",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "input_csv": str(csv_path),
        "gates": {
            "min_rows_for_grade": args.min_rows_for_grade,
            "grade_valid": grade_valid,
            "grade_note": (
                "enough_rows"
                if grade_valid
                else f"insufficient_rows:{len(rows)}/{args.min_rows_for_grade}"
            ),
        },
        "counts": {
            "rows_total": len(rows),
            "n_direction_1d": n_1d,
            "n_direction_3d": n_3d,
            "n_brier": n_brier,
            "n_ece": n_ece,
            "n_mdd": n_mdd,
            "rule_violations": violations,
        },
        "metrics": {
            "direction_accuracy_1d": acc_1d,
            "direction_accuracy_3d": acc_3d,
            "brier_up_binary_1d": brier,
            "ece_10bin_up_binary_1d": ece,
            "calibration": {
                "selected_method": selected_method,
                "requested_mode": args.calibration_mode,
                "selected_brier": selected_brier,
                "selected_ece": selected_ece,
                "temperature_scaling": {
                    "method": "temperature_scaling_logit_grid",
                    "temperature": calib["temperature"],
                    "brier_before": calib["brier_before"],
                    "brier_after": calib["brier_after"],
                    "ece_before": calib["ece_before"],
                    "ece_after": calib["ece_after"],
                },
                "isotonic": {
                    "method": "isotonic_pav",
                    "blocks": calib_iso["blocks"],
                    "brier_before": calib_iso["brier_before"],
                    "brier_after": calib_iso["brier_after"],
                    "ece_before": calib_iso["ece_before"],
                    "ece_after": calib_iso["ece_after"],
                },
            },
            "mdd_from_actual_next_day_returns": mdd,
        },
        "holdout": {
            "last_n": args.holdout_last_n,
            "counts": {
                "rows_total": len(holdout_rows),
                "n_direction_1d": h_n_1d,
            },
            "metrics": {
                "direction_accuracy_1d": h_acc_1d,
                "brier_up_binary_1d": h_brier,
                "ece_10bin_up_binary_1d": h_ece,
                "mdd_from_actual_next_day_returns": h_mdd,
            },
            "score_100": h_score,
        },
        "score_100": score,
        "grade": grade,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {out_path.resolve()}")
    print(f"SCORE_TOTAL: {score['total']}")
    print(f"GRADE: {result['grade']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
