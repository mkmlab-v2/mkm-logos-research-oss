#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_JSONL = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_market_proxy_events_latest.jsonl"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_symptom_transition_eval_latest.json"


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _ece(y: List[int], p: List[float], bins: int = 10) -> tuple[float, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    n = len(y)
    if n == 0:
        return 0.0, rows
    e = 0.0
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        idx = [i for i, pv in enumerate(p) if lo <= pv < hi or (b == bins - 1 and pv == hi)]
        if not idx:
            rows.append({"bin": b, "lo": lo, "hi": hi, "count": 0, "acc": None, "conf": None, "abs_gap": None})
            continue
        by = [y[i] for i in idx]
        bp = [p[i] for i in idx]
        acc = _mean([float(v) for v in by])
        conf = _mean(bp)
        gap = abs(acc - conf)
        e += (len(idx) / n) * gap
        rows.append({"bin": b, "lo": lo, "hi": hi, "count": len(idx), "acc": acc, "conf": conf, "abs_gap": gap})
    return e, rows


def _corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0.0 or dy == 0.0:
        return 0.0
    return num / (dx * dy)


def _brier(y: List[int], p: List[float]) -> float:
    return _mean([(pp - float(yy)) ** 2 for yy, pp in zip(y, p)]) if y else 0.0


def _temperature_scale(p: List[float], t: float) -> List[float]:
    eps = 1e-6
    out: List[float] = []
    for pv in p:
        pv = max(eps, min(1.0 - eps, pv))
        logit = math.log(pv / (1.0 - pv))
        z = logit / max(1e-6, t)
        q = 1.0 / (1.0 + math.exp(-z))
        out.append(max(0.0, min(1.0, q)))
    return out


def _fit_temperature(y: List[int], p: List[float]) -> tuple[float, List[float], float, float]:
    if not y:
        return 1.0, p, 0.0, 0.0
    best_t = 1.0
    best_p = p
    best_ece, _ = _ece(y, p, bins=10)
    best_brier = _brier(y, p)
    # Small bounded grid to keep behavior deterministic and robust.
    for i in range(50, 301):
        t = i / 100.0
        cand = _temperature_scale(p, t)
        ece, _ = _ece(y, cand, bins=10)
        brier = _brier(y, cand)
        if (ece < best_ece) or (ece == best_ece and brier < best_brier):
            best_t = t
            best_p = cand
            best_ece = ece
            best_brier = brier
    return best_t, best_p, best_ece, best_brier


def _fit_monotonic_bin_calibrator(y: List[int], p: List[float], bins: int = 10) -> tuple[List[float], List[Dict[str, Any]]]:
    if not y:
        return p, []
    bucket_rows: List[Dict[str, Any]] = []
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        idx = [i for i, pv in enumerate(p) if lo <= pv < hi or (b == bins - 1 and pv == hi)]
        if not idx:
            bucket_rows.append({"bin": b, "lo": lo, "hi": hi, "count": 0, "raw_rate": None, "cal_rate": None})
            continue
        rate = _mean([float(y[i]) for i in idx])
        bucket_rows.append({"bin": b, "lo": lo, "hi": hi, "count": len(idx), "raw_rate": rate, "cal_rate": rate})

    # Isotonic-lite via pooled adjacent violators on non-empty buckets.
    compact = [r for r in bucket_rows if r["count"] > 0]
    stack: List[Dict[str, Any]] = []
    for row in compact:
        row = dict(row)
        row["weight"] = float(row["count"])
        stack.append(row)
        while len(stack) >= 2 and stack[-2]["cal_rate"] > stack[-1]["cal_rate"]:
            b2 = stack.pop()
            b1 = stack.pop()
            w = b1["weight"] + b2["weight"]
            merged = {
                "bin": b1["bin"],
                "lo": b1["lo"],
                "hi": b2["hi"],
                "count": int(w),
                "raw_rate": None,
                "cal_rate": ((b1["cal_rate"] * b1["weight"]) + (b2["cal_rate"] * b2["weight"])) / w,
                "weight": w,
            }
            stack.append(merged)

    cal_lookup: Dict[int, float] = {}
    for block in stack:
        for b in range(int(block["lo"] * bins), int(block["hi"] * bins + 1e-9)):
            if 0 <= b < bins:
                cal_lookup[b] = float(block["cal_rate"])
    calibrated: List[float] = []
    for pv in p:
        b = min(bins - 1, max(0, int(pv * bins)))
        calibrated.append(float(cal_lookup.get(b, pv)))
    return calibrated, bucket_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate sasang symptom transition probabilistic forecast.")
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS_JSONL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--decision-threshold", type=float, default=0.5)
    args = ap.parse_args()

    total = 0
    usable = 0
    y_true: List[int] = []
    y_prob: List[float] = []
    severity: List[float] = []
    label_mode_counts: Dict[str, int] = {}

    for e in _iter_jsonl(args.events_jsonl):
        total += 1
        l4 = e.get("layer_4_transition_forecast") if isinstance(e.get("layer_4_transition_forecast"), dict) else {}
        l2 = e.get("layer_2_symptom_state") if isinstance(e.get("layer_2_symptom_state"), dict) else {}
        labels = e.get("labels") if isinstance(e.get("labels"), dict) else {}
        fw = labels.get("future_worsened")
        wp = l4.get("worsening_prob")
        sev = l2.get("state_severity")
        if not isinstance(fw, bool) or not isinstance(wp, (int, float)):
            continue
        usable += 1
        meta = e.get("meta") if isinstance(e.get("meta"), dict) else {}
        label_mode = str(meta.get("label_mode", "unknown"))
        label_mode_counts[label_mode] = label_mode_counts.get(label_mode, 0) + 1
        y_true.append(1 if fw else 0)
        y_prob.append(max(0.0, min(1.0, float(wp))))
        severity.append(float(sev) if isinstance(sev, (int, float)) else 0.0)

    coverage = (usable / total) if total else 0.0
    preds = [1 if p >= args.decision_threshold else 0 for p in y_prob]
    correct = sum(1 for t, p in zip(y_true, preds) if t == p)
    accuracy = (correct / usable) if usable else 0.0
    positive_count = sum(y_true)
    negative_count = usable - positive_count
    positive_rate = (positive_count / usable) if usable else 0.0
    brier = _mean([(p - t) ** 2 for p, t in zip(y_prob, y_true)]) if usable else 0.0
    ece, ece_bins = _ece(y_true, y_prob, bins=10)
    corr_prob_vs_realized = _corr(y_prob, [float(v) for v in y_true])
    best_t, p_temp, ece_temp, brier_temp = _fit_temperature(y_true, y_prob)
    p_iso, iso_bins = _fit_monotonic_bin_calibrator(y_true, p_temp, bins=10)
    ece_iso, ece_iso_bins = _ece(y_true, p_iso, bins=10)
    brier_iso = _brier(y_true, p_iso)

    report = {
        "schema_version": "sasang_symptom_transition_eval_v1",
        "n_total": total,
        "n_usable": usable,
        "coverage_ratio": coverage,
        "label_mode_summary": {
            "counts": label_mode_counts,
            "primary_label_mode": (
                max(label_mode_counts.items(), key=lambda kv: kv[1])[0]
                if label_mode_counts
                else "unknown"
            ),
        },
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "metrics": {
            "decision_threshold": args.decision_threshold,
            "accuracy": accuracy,
            "brier_worsening": brier,
            "ece_worsening": ece,
            "corr_worsening_prob_vs_realized": corr_prob_vs_realized,
            "mean_worsening_prob": _mean(y_prob) if y_prob else 0.0,
            "mean_state_severity": _mean(severity) if severity else 0.0,
            "positive_label_count": positive_count,
            "negative_label_count": negative_count,
            "positive_label_rate": positive_rate,
        },
        "calibration": {
            "raw": {
                "ece_worsening": ece,
                "brier_worsening": brier,
            },
            "temperature_scaling": {
                "best_temperature": best_t,
                "ece_worsening": ece_temp,
                "brier_worsening": brier_temp,
            },
            "isotonic_lite_after_temperature": {
                "ece_worsening": ece_iso,
                "brier_worsening": brier_iso,
            },
        },
        "calibration_bins": ece_bins,
        "calibration_bins_isotonic": ece_iso_bins,
        "isotonic_bucket_fit": iso_bins,
        "gate_hint": {
            "recommended": (
                "candidate_for_btrack_shadow_promotion"
                if (
                    usable >= 30
                    and coverage >= 0.95
                    and brier_iso <= 0.20
                    and ece_iso <= 0.12
                    and positive_count >= 5
                    and negative_count >= 5
                )
                else "shadow_only"
            ),
            "rule": "Need n_usable>=30, coverage_ratio>=0.95, calibrated_brier<=0.20, calibrated_ece<=0.12, positive>=5, negative>=5",
        },
        "notes": [
            "Probabilistic trajectory only; deterministic price prediction forbidden.",
            "B-track shadow artifact; A-track autobind forbidden.",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
