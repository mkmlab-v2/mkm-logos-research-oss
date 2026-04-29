# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.83, L:0.90, K:0.58, M:0.82}
# Balance: 91
# Purpose: Evaluate weekly contribution of emotion-weighted memory signals.
# Keywords: weekly, evaluation, memory, sentiment, pnl, calibration
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _bucket(v: float) -> str:
    if v < -0.33:
        return "neg"
    if v > 0.33:
        return "pos"
    return "mid"


def _evaluate_usable_rows(
    usable: List[tuple[float, float, float, float]],
    *,
    n_total: int,
    min_samples_gate: int,
    min_coverage_gate: float,
    corr_gate: float,
) -> Dict[str, Any]:
    coverage_ratio = (len(usable) / n_total) if n_total else 0.0
    if not usable:
        return {
            "n_total": n_total,
            "n_usable": 0,
            "coverage_ratio": coverage_ratio,
            "metrics": {
                "corr_valence_vs_forward_pnl_1d": 0.0,
                "corr_arousal_vs_forward_pnl_1d": 0.0,
                "corr_confidence_vs_abs_forward_pnl_1d": 0.0,
                "mean_forward_pnl_1d": 0.0,
                "mean_forward_pnl_1d_by_valence_bucket": {"neg": 0.0, "mid": 0.0, "pos": 0.0},
            },
            "recommended": "shadow_only",
        }
    valences = [x[0] for x in usable]
    arousals = [x[1] for x in usable]
    uncertainties = [x[2] for x in usable]
    pnls = [x[3] for x in usable]
    confidence = [1.0 - u for u in uncertainties]
    buckets: Dict[str, List[float]] = {"neg": [], "mid": [], "pos": []}
    for v, pnl in zip(valences, pnls):
        buckets[_bucket(v)].append(pnl)
    corr_v = _corr(valences, pnls)
    recommended = (
        "shadow_only"
        if (len(usable) < min_samples_gate or coverage_ratio < min_coverage_gate or corr_v < corr_gate)
        else "candidate_for_btrack_promotion"
    )
    return {
        "n_total": n_total,
        "n_usable": len(usable),
        "coverage_ratio": coverage_ratio,
        "metrics": {
            "corr_valence_vs_forward_pnl_1d": corr_v,
            "corr_arousal_vs_forward_pnl_1d": _corr(arousals, pnls),
            "corr_confidence_vs_abs_forward_pnl_1d": _corr(confidence, [abs(x) for x in pnls]),
            "mean_forward_pnl_1d": _mean(pnls),
            "mean_forward_pnl_1d_by_valence_bucket": {k: _mean(v) for k, v in buckets.items()},
        },
        "recommended": recommended,
    }


def evaluate(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    usable: List[tuple[float, float, float, float]] = []
    usable_by_source: Dict[str, List[tuple[float, float, float, float]]] = {}
    total_by_source: Dict[str, int] = {}
    for e in events:
        src = str(e.get("source") or "unknown")
        total_by_source[src] = total_by_source.get(src, 0) + 1
        emo = e.get("emotion") or {}
        labels = e.get("labels") or {}
        pnl = labels.get("forward_pnl_1d")
        valence = emo.get("valence")
        arousal = emo.get("arousal")
        uncertainty = emo.get("uncertainty")
        if pnl is None or valence is None or arousal is None or uncertainty is None:
            continue
        row = (float(valence), float(arousal), float(uncertainty), float(pnl))
        usable.append(row)
        usable_by_source.setdefault(src, []).append(row)

    min_samples_gate = 30
    min_coverage_gate = 0.80
    corr_gate = 0.05
    overall = _evaluate_usable_rows(
        usable,
        n_total=len(events),
        min_samples_gate=min_samples_gate,
        min_coverage_gate=min_coverage_gate,
        corr_gate=corr_gate,
    )
    metrics_by_source: Dict[str, Any] = {}
    for src, src_total in sorted(total_by_source.items()):
        metrics_by_source[src] = _evaluate_usable_rows(
            usable_by_source.get(src, []),
            n_total=src_total,
            min_samples_gate=min_samples_gate,
            min_coverage_gate=min_coverage_gate,
            corr_gate=corr_gate,
        )
    allowed_primary_sources = {"atproto_operational_heuristic_v1", "kpi_derived_sentiment_proxy_v1"}
    min_primary_samples_gate = 30
    preferred_primary_candidates = [k for k in metrics_by_source if k in allowed_primary_sources]
    if preferred_primary_candidates:
        primary_source = max(
            preferred_primary_candidates,
            key=lambda k: metrics_by_source[k].get("n_usable", 0),
        )
    elif metrics_by_source:
        primary_source = "unknown"
    else:
        primary_source = "unknown"
    overall_recommended = overall["recommended"]
    primary_n_usable = int(metrics_by_source.get(primary_source, {}).get("n_usable", 0))
    primary_recommended_raw = metrics_by_source.get(primary_source, {}).get("recommended", "shadow_only")
    primary_recommended = (
        primary_recommended_raw if primary_n_usable >= min_primary_samples_gate else "shadow_only"
    )
    primary_gap_to_gate = max(0, min_primary_samples_gate - primary_n_usable)
    combined_recommended = (
        "candidate_for_btrack_promotion"
        if (overall_recommended == "candidate_for_btrack_promotion" and primary_recommended == "candidate_for_btrack_promotion")
        else "shadow_only"
    )
    if overall["n_usable"] == 0:
        return {
            "schema_version": "emotion_weight_memory_weekly_report_v1",
            "n_total": overall["n_total"],
            "n_usable": 0,
            "coverage_ratio": overall["coverage_ratio"],
            "note": "No rows contained valence/arousal/uncertainty + forward_pnl_1d.",
            "metrics_by_source": metrics_by_source,
            "source_gate": {
                "primary_source": primary_source,
                "overall_recommended": overall_recommended,
                "primary_source_recommended": primary_recommended,
                "primary_source_recommended_raw": primary_recommended_raw,
                "primary_n_usable": primary_n_usable,
                "min_primary_samples_gate": min_primary_samples_gate,
                "primary_gap_to_gate": primary_gap_to_gate,
                "allowed_primary_sources": sorted(allowed_primary_sources),
                "combined_recommended": combined_recommended,
            },
        }

    return {
        "schema_version": "emotion_weight_memory_weekly_report_v1",
        "n_total": overall["n_total"],
        "n_usable": overall["n_usable"],
        "coverage_ratio": overall["coverage_ratio"],
        "metrics": overall["metrics"],
        "metrics_by_source": metrics_by_source,
        "gate_hint": {
            "recommended": combined_recommended,
            "rule": "Need n_usable>=30, coverage_ratio>=0.80, corr_valence_vs_forward_pnl_1d>=0.05",
            "thresholds": {
                "min_samples": min_samples_gate,
                "min_coverage_ratio": min_coverage_gate,
                "min_corr_valence_vs_forward_pnl_1d": corr_gate,
            },
            "components": {
                "overall_recommended": overall_recommended,
                "primary_source_recommended": primary_recommended,
                "primary_source_recommended_raw": primary_recommended_raw,
                "primary_source": primary_source,
                "primary_n_usable": primary_n_usable,
                "min_primary_samples_gate": min_primary_samples_gate,
                "primary_gap_to_gate": primary_gap_to_gate,
                "allowed_primary_sources": sorted(allowed_primary_sources),
            },
        },
        "source_gate": {
            "primary_source": primary_source,
            "overall_recommended": overall_recommended,
            "primary_source_recommended": primary_recommended,
            "primary_source_recommended_raw": primary_recommended_raw,
            "primary_n_usable": primary_n_usable,
            "min_primary_samples_gate": min_primary_samples_gate,
            "primary_gap_to_gate": primary_gap_to_gate,
            "allowed_primary_sources": sorted(allowed_primary_sources),
            "combined_recommended": combined_recommended,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate emotion-weighted memory weekly impact.")
    p.add_argument("--events-jsonl", type=Path, required=True, help="emotion_weighted_memory_event_v1 jsonl")
    p.add_argument("--out-json", type=Path, required=True, help="weekly report output json")
    args = p.parse_args()

    events = list(_iter_jsonl(args.events_jsonl))
    report = evaluate(events)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

