#!/usr/bin/env python3
"""Compare latest B-Track results against locked verified baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_verified_baseline_lock_latest.json"
QUALITY = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quality_anchor_verified_only_latest.json"
GATE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_promotion_gate_anchor_verified_only_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Check B-Track regression against locked baseline")
    ap.add_argument("--baseline", default=str(BASELINE))
    ap.add_argument("--quality", default=str(QUALITY))
    ap.add_argument("--gate", default=str(GATE))
    args = ap.parse_args()

    baseline_path = _abs(args.baseline)
    quality_path = _abs(args.quality)
    gate_path = _abs(args.gate)
    for p in (baseline_path, quality_path, gate_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    baseline = _jread(baseline_path)
    quality = _jread(quality_path)
    gate = _jread(gate_path)

    policy = baseline.get("regression_policy", {})
    metrics = quality.get("metrics", {})

    req_decision = str(policy.get("require_decision", "pass"))
    min_repro = _as_float(policy.get("reproducibility_min"))
    min_resolution = _as_float(policy.get("resolution_min"))
    min_contam = _as_float(policy.get("contamination_min"))

    repro = _as_float(metrics.get("reproducibility_match_rate"))
    resolution = _as_float(metrics.get("resolution_confidence_delta_b_minus_a"))
    contam = _as_float(metrics.get("contamination_snr_delta_b_minus_a"))
    decision = str(gate.get("decision", ""))

    failures: list[str] = []
    if decision != req_decision:
        failures.append(f"decision mismatch: current={decision} required={req_decision}")
    if min_repro is not None and (repro is None or repro < min_repro):
        failures.append(f"reproducibility below min: current={repro} min={min_repro}")
    if min_resolution is not None and (resolution is None or resolution < min_resolution):
        failures.append(f"resolution below min: current={resolution} min={min_resolution}")
    if min_contam is not None and (contam is None or contam < min_contam):
        failures.append(f"contamination below min: current={contam} min={min_contam}")

    print("B-Track regression check")
    print(f"- decision: {decision}")
    print(f"- reproducibility: {repro}")
    print(f"- resolution: {resolution}")
    print(f"- contamination: {contam}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
