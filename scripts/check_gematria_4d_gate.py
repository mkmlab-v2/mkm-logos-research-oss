#!/usr/bin/env python3
"""Fail-fast gate for symbol-gematria alignment and uplift artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALIGN = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_gematria_alignment_test_nonzero.json"
UPLIFT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_UPLIFT_AB_V1.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: object, default: float = 0.0) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate check for gematria-4d pipeline")
    ap.add_argument("--align", default=str(ALIGN))
    ap.add_argument("--uplift", default=str(UPLIFT))
    ap.add_argument("--min-resonance-rate", type=float, default=0.80)
    ap.add_argument("--min-mean-axis-pearson", type=float, default=-0.20)
    ap.add_argument("--min-saving-delta", type=float, default=-0.20)
    args = ap.parse_args()

    align_path = _abs(args.align)
    uplift_path = _abs(args.uplift)
    for p in (align_path, uplift_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    align = _jread(align_path)
    uplift = _jread(uplift_path)
    summary = align.get("summary", {})
    deltas = uplift.get("deltas_on_minus_off", {})
    gate_off = uplift.get("quality_gate_off", {})
    gate_on = uplift.get("quality_gate_on", {})

    resonance_rate = _f(summary.get("resonance_rate"))
    mean_axis_pearson = _f(summary.get("mean_axis_pearson"), default=-1.0)
    saving_delta = _f(deltas.get("global_token_saving_rate"))

    failures: list[str] = []
    if resonance_rate < args.min_resonance_rate:
        failures.append(
            f"resonance_rate below min: current={resonance_rate:.6f} min={args.min_resonance_rate:.6f}"
        )
    if mean_axis_pearson < args.min_mean_axis_pearson:
        failures.append(
            f"mean_axis_pearson below min: current={mean_axis_pearson:.6f} min={args.min_mean_axis_pearson:.6f}"
        )
    if saving_delta < args.min_saving_delta:
        failures.append(
            f"saving_delta below min: current={saving_delta:.6f} min={args.min_saving_delta:.6f}"
        )
    if not bool(gate_off.get("jaccard_guardrail_ok", False)):
        failures.append("quality_gate_off.jaccard_guardrail_ok must be true")
    if not bool(gate_on.get("jaccard_guardrail_ok", False)):
        failures.append("quality_gate_on.jaccard_guardrail_ok must be true")

    print("Gematria-4D gate check")
    print(
        f"- thresholds: resonance>={args.min_resonance_rate:.6f}, "
        f"mean_axis_pearson>={args.min_mean_axis_pearson:.6f}, saving_delta>={args.min_saving_delta:.6f}"
    )
    print(f"- resonance_rate: {resonance_rate:.6f}")
    print(f"- mean_axis_pearson: {mean_axis_pearson:.6f}")
    print(f"- saving_delta_on_minus_off: {saving_delta:.6f}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
