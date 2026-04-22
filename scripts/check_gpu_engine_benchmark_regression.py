#!/usr/bin/env python3
"""Check GPU benchmark bundle against locked regression baseline."""

from __future__ import annotations

import argparse
import json
from statistics import median
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = ROOT / "docs" / "final" / "artifacts" / "gpu_engine_benchmark_baseline_v1.json"
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "gpu_engine_benchmark_bundle_v1_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_from_bundle(bundle: dict[str, Any], run_name: str, metric_name: str) -> float | None:
    runs = bundle.get("runs")
    if not isinstance(runs, dict):
        return None
    run_doc = runs.get(run_name)
    if not isinstance(run_doc, dict):
        return None
    perf = run_doc.get("performance")
    if not isinstance(perf, dict):
        return None
    v = perf.get(metric_name)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _metric_values_from_bundles(bundles: list[dict[str, Any]], run_name: str, metric_name: str) -> list[float]:
    vals: list[float] = []
    for bundle in bundles:
        v = _metric_from_bundle(bundle, run_name, metric_name)
        if v is not None:
            vals.append(float(v))
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(description="Check GPU benchmark regression vs baseline.")
    ap.add_argument("--bundle", action="append", default=[])
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--max-regression-pct", type=float, default=None)
    args = ap.parse_args()

    bundle_args = args.bundle or [str(DEFAULT_BUNDLE)]
    bundle_paths = [_abs(x) for x in bundle_args]
    baseline_path = _abs(args.baseline)
    for p in [*bundle_paths, baseline_path]:
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    bundles = [_jread(p) for p in bundle_paths]
    baseline = _jread(baseline_path)

    policy_default = baseline.get("max_regression_pct_default")
    if args.max_regression_pct is not None:
        max_regression_pct = float(args.max_regression_pct)
    elif isinstance(policy_default, (int, float)):
        max_regression_pct = float(policy_default)
    else:
        max_regression_pct = 20.0

    targets = baseline.get("targets")
    if not isinstance(targets, dict) or not targets:
        print("ERROR: baseline targets missing/empty")
        return 2

    failures: list[str] = []
    print("GPU benchmark regression check")
    print(f"- bundles: {[str(p) for p in bundle_paths]}")
    print(f"- baseline: {baseline_path}")
    print(f"- max_regression_pct: {max_regression_pct}")

    for run_name, rule in targets.items():
        if not isinstance(rule, dict):
            failures.append(f"{run_name}: invalid target rule")
            continue
        metric_name = str(rule.get("metric_name", ""))
        baseline_value = rule.get("baseline_value")
        if not metric_name or not isinstance(baseline_value, (int, float)):
            failures.append(f"{run_name}: missing metric_name/baseline_value")
            continue
        sample_values = _metric_values_from_bundles(bundles, run_name, metric_name)
        if not sample_values:
            failures.append(f"{run_name}: current metric missing ({metric_name})")
            continue
        current_value = float(median(sample_values))
        sample_min = min(sample_values)
        sample_max = max(sample_values)
        sample_values_str = ", ".join(f"{x:.6f}" for x in sample_values)
        target_regression_pct_raw = rule.get("max_regression_pct")
        if isinstance(target_regression_pct_raw, (int, float)):
            target_regression_pct = float(target_regression_pct_raw)
        else:
            target_regression_pct = max_regression_pct
        min_allowed_pct = float(baseline_value) * (1.0 - (target_regression_pct / 100.0))
        abs_floor_raw = rule.get("absolute_min")
        abs_floor = float(abs_floor_raw) if isinstance(abs_floor_raw, (int, float)) else None
        min_allowed = max(min_allowed_pct, abs_floor) if abs_floor is not None else min_allowed_pct
        print(
            f"- {run_name}.{metric_name}: current={current_value:.6f} "
            f"sample_min={sample_min:.6f} "
            f"sample_max={sample_max:.6f} "
            f"samples=[{sample_values_str}] "
            f"baseline={float(baseline_value):.6f} "
            f"max_regression_pct={target_regression_pct:.3f} "
            f"min_allowed={min_allowed:.6f}"
        )
        if current_value < min_allowed:
            failures.append(
                f"{run_name}.{metric_name} regressed: current={current_value:.6f} < min_allowed={min_allowed:.6f}"
            )

    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
