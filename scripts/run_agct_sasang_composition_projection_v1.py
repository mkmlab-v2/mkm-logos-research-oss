#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.84, K:0.66, M:0.46}
# Balance: 88
# Purpose: Project AGCT composition signals onto Sasang interpretation axes (B-track).
# Keywords: agct, composition, sasang, projection, btrack, research_only
"""Project AGCT composition patterns onto Sasang interpretation axes.

This script is deliberately B-track only:
- works without personal raw genome files
- does not claim clinical validity
- focuses on structural composition/projection diagnostics
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")

# Heuristic projection profile (research-only prior).
DEFAULT_BASE_AXIS_WEIGHTS: dict[str, dict[str, float]] = {
    "A": {"TY": 1.0, "SY": 0.2, "TE": 0.1, "SE": 0.4},
    "C": {"TY": 0.2, "SY": 1.0, "TE": 0.4, "SE": 0.1},
    "G": {"TY": 0.1, "SY": 0.4, "TE": 1.0, "SE": 0.2},
    "T": {"TY": 0.4, "SY": 0.1, "TE": 0.2, "SE": 1.0},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    den = (den_x * den_y) ** 0.5
    if den <= 0:
        return None
    return num / den


def _load_optional_risk_map(path: Path | None, sample_col: str, risk_col: str) -> dict[str, float]:
    if path is None or not path.is_file():
        return {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if sample_col not in fields or risk_col not in fields:
            return {}
        out: dict[str, float] = {}
        for row in reader:
            sid = str(row.get(sample_col) or "").strip()
            risk = _safe_float(row.get(risk_col))
            if sid and risk is not None:
                out[sid] = risk
        return out


def _load_axis_weights(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None or not path.is_file():
        return DEFAULT_BASE_AXIS_WEIGHTS
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return DEFAULT_BASE_AXIS_WEIGHTS

    out: dict[str, dict[str, float]] = {}
    for base in BASES:
        row_obj = obj.get(base)
        if not isinstance(row_obj, dict):
            return DEFAULT_BASE_AXIS_WEIGHTS
        row: dict[str, float] = {}
        for axis in AXES:
            value = _safe_float(row_obj.get(axis))
            if value is None:
                return DEFAULT_BASE_AXIS_WEIGHTS
            row[axis] = float(value)
        out[base] = row
    return out


def _normalize(v: dict[str, float]) -> dict[str, float]:
    s = sum(v.values())
    if s <= 0:
        return {k: 0.0 for k in v}
    return {k: (float(x) / s) for k, x in v.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="AGCT composition -> Sasang axis projection (B-track only).")
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--cohort-csv", type=Path, default=None, help="Optional. Used only for exploratory risk correlation.")
    ap.add_argument("--risk-col", type=str, default="risk_score")
    ap.add_argument("--axis-weights-json", type=Path, default=None)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_sasang_composition_projection_v1_latest.json"),
    )
    ns = ap.parse_args()

    risk_map = _load_optional_risk_map(ns.cohort_csv, ns.sample_col, ns.risk_col)
    axis_weights = _load_axis_weights(ns.axis_weights_json)

    with ns.genotype_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if ns.sample_col not in fields or ns.genotype_col not in fields:
            raise SystemExit(f"genotype CSV must include {ns.sample_col} and {ns.genotype_col}")
        rows = list(reader)

    counts_by_sample: dict[str, dict[str, int]] = {}
    for row in rows:
        sid = str(row.get(ns.sample_col) or "").strip()
        if not sid:
            continue
        geno = str(row.get(ns.genotype_col) or "").strip().upper()
        if not geno:
            continue
        counts = counts_by_sample.setdefault(sid, {b: 0 for b in BASES})
        for ch in geno:
            if ch in counts:
                counts[ch] += 1

    if not counts_by_sample:
        raise SystemExit("No AGCT counts could be aggregated from genotype input.")

    sample_rows: list[dict[str, Any]] = []
    axis_values: dict[str, list[float]] = {a: [] for a in AXES}
    base_ratios_by_base: dict[str, list[float]] = {b: [] for b in BASES}
    risk_pairs: dict[str, tuple[list[float], list[float]]] = {a: ([], []) for a in AXES}

    for sid, counts_i in sorted(counts_by_sample.items()):
        counts = {b: float(counts_i[b]) for b in BASES}
        total = sum(counts.values())
        if total <= 0:
            continue
        ratios = {b: counts[b] / total for b in BASES}
        gc_ratio = ratios["G"] + ratios["C"]
        at_ratio = ratios["A"] + ratios["T"]
        purine_ratio = ratios["A"] + ratios["G"]
        pyrimidine_ratio = ratios["C"] + ratios["T"]

        raw_axis = {
            axis: sum(ratios[base] * axis_weights[base][axis] for base in BASES)
            for axis in AXES
        }
        axis_proj = _normalize(raw_axis)
        top_axis = sorted(axis_proj.items(), key=lambda kv: (-kv[1], AXES.index(kv[0])))[0][0]

        for axis in AXES:
            axis_values[axis].append(axis_proj[axis])
        for base in BASES:
            base_ratios_by_base[base].append(ratios[base])

        risk = risk_map.get(sid)
        if risk is not None:
            for axis in AXES:
                xs, ys = risk_pairs[axis]
                xs.append(axis_proj[axis])
                ys.append(risk)

        sample_rows.append(
            {
                "sample_id": sid,
                "base_counts": {k: int(v) for k, v in counts.items()},
                "base_ratios": ratios,
                "composition_metrics": {
                    "gc_ratio": gc_ratio,
                    "at_ratio": at_ratio,
                    "purine_ratio": purine_ratio,
                    "pyrimidine_ratio": pyrimidine_ratio,
                },
                "axis_projection": axis_proj,
                "top_axis": top_axis,
                "risk_value": risk,
            }
        )

    n = len(sample_rows)
    axis_summary = {
        axis: {
            "mean_projection": (sum(vals) / len(vals)) if vals else 0.0,
            "min_projection": min(vals) if vals else 0.0,
            "max_projection": max(vals) if vals else 0.0,
        }
        for axis, vals in axis_values.items()
    }
    axis_top_counts = {axis: 0 for axis in AXES}
    for row in sample_rows:
        axis_top_counts[row["top_axis"]] += 1

    composition_correlations: dict[str, dict[str, float | None]] = {}
    for axis in AXES:
        axis_vec = axis_values[axis]
        composition_correlations[axis] = {}
        for base in BASES:
            composition_correlations[axis][f"corr_{base}_ratio"] = _pearson(axis_vec, base_ratios_by_base[base])

    risk_correlations: dict[str, dict[str, float | int | None]] = {}
    for axis in AXES:
        xs, ys = risk_pairs[axis]
        risk_correlations[axis] = {
            "n_pairs": len(xs),
            "pearson_corr_with_risk": _pearson(xs, ys),
        }

    payload = {
        "schema": "agct_sasang_composition_projection_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "sample_col": ns.sample_col,
            "genotype_col": ns.genotype_col,
            "cohort_csv": str(ns.cohort_csv.resolve()) if ns.cohort_csv and ns.cohort_csv.is_file() else None,
            "risk_col": ns.risk_col,
            "axis_weights_json": str(ns.axis_weights_json.resolve()) if ns.axis_weights_json and ns.axis_weights_json.is_file() else None,
            "axis_weights": axis_weights,
        },
        "summary": {
            "samples_used": n,
            "axis_top_counts": axis_top_counts,
            "axis_summary": axis_summary,
        },
        "composition_axis_correlations": composition_correlations,
        "risk_axis_correlations": risk_correlations,
        "sample_projection_preview": sample_rows[:20],
        "notes": [
            "This projection is a structural AGCT composition analysis only.",
            "No clinical or diagnostic claim is made.",
            "Do not auto-promote to A-track/live decisioning.",
        ],
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} samples={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
