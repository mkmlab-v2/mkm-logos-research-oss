#!/usr/bin/env python3
"""Synthetic boundary sweep for kmh single-variable control."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "emotion_state_kmh_single_variable_boundary_sweep_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _frange(start: float, stop: float, step: float) -> list[float]:
    vals: list[float] = []
    x = start
    while x <= stop + 1e-12:
        vals.append(round(x, 10))
        x += step
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tau0", type=float, default=0.05)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--tau-min", type=float, default=0.03)
    ap.add_argument("--tau-max", type=float, default=0.08)
    ap.add_argument("--z-start", type=float, default=-1.0)
    ap.add_argument("--z-stop", type=float, default=1.0)
    ap.add_argument("--z-step", type=float, default=0.2)
    ap.add_argument("--fpr-start", type=float, default=0.04)
    ap.add_argument("--fpr-stop", type=float, default=0.06)
    ap.add_argument("--fpr-step", type=float, default=0.002)
    args = ap.parse_args()

    z_values = _frange(args.z_start, args.z_stop, args.z_step)
    fpr_values = _frange(args.fpr_start, args.fpr_stop, args.fpr_step)

    rows = []
    decision_change_points = 0
    for fpr in fpr_values:
        for z in z_values:
            tau_a = float(args.tau0)
            tau_b = _clip(tau_a + float(args.alpha) * z, float(args.tau_min), float(args.tau_max))
            decision_a = "GO_LIVE_CANDIDATE" if fpr <= tau_a else "HOLD_PRECHECK_FAILED"
            decision_b = "GO_LIVE_CANDIDATE" if fpr <= tau_b else "HOLD_PRECHECK_FAILED"
            changed = decision_a != decision_b
            if changed:
                decision_change_points += 1
            rows.append(
                {
                    "synthetic_layer5_fpr": fpr,
                    "z_km": z,
                    "tau_a": tau_a,
                    "tau_b": tau_b,
                    "decision_a": decision_a,
                    "decision_b": decision_b,
                    "decision_changed": changed,
                }
            )

    out = {
        "schema": "emotion_state_kmh_single_variable_boundary_sweep_v1",
        "generated_at_utc": _iso_now(),
        "formula": "tau_prime = clip(tau0 + alpha * z_km, tau_min, tau_max)",
        "params": {
            "tau0": float(args.tau0),
            "alpha": float(args.alpha),
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "z_start": float(args.z_start),
            "z_stop": float(args.z_stop),
            "z_step": float(args.z_step),
            "fpr_start": float(args.fpr_start),
            "fpr_stop": float(args.fpr_stop),
            "fpr_step": float(args.fpr_step),
        },
        "summary": {
            "z_points": len(z_values),
            "fpr_points": len(fpr_values),
            "total_points": len(rows),
            "decision_change_points": decision_change_points,
        },
        "points": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "total_points": len(rows),
                "decision_change_points": decision_change_points,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
