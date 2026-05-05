#!/usr/bin/env python3
"""Sweep z_km for single-variable tolerance control and export sensitivity report."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SIGNOFF = ART / "emotion_state_release_human_signoff_latest.json"
DEFAULT_DRIFT = ART / "layer1_layer5_baseline_drift_check_latest.json"
DEFAULT_L5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_OUT = ART / "emotion_state_kmh_single_variable_sweep_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ab(
    signoff_json: Path,
    drift_json: Path,
    l5_json: Path,
    tau0: float,
    alpha: float,
    z_km: float,
    tau_min: float,
    tau_max: float,
    out_json: Path,
) -> dict[str, Any]:
    cmd = [
        "py",
        str(ROOT / "scripts" / "run_kmh_single_variable_ab_v1.py"),
        "--human-signoff-json",
        str(signoff_json),
        "--baseline-drift-json",
        str(drift_json),
        "--layer5-json",
        str(l5_json),
        "--tau0",
        str(tau0),
        "--alpha",
        str(alpha),
        "--z-km",
        str(z_km),
        "--tau-min",
        str(tau_min),
        "--tau-max",
        str(tau_max),
        "--output-json",
        str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"ok": False, "z_km": z_km, "error": proc.stdout + proc.stderr}
    try:
        doc = json.loads(out_json.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "z_km": z_km, "error": str(exc)}
    return {
        "ok": True,
        "z_km": z_km,
        "tau_prime": ((doc.get("params") or {}).get("tau_prime")),
        "decision_a": (((doc.get("ab_result") or {}).get("A_static") or {}).get("decision")),
        "decision_b": (((doc.get("ab_result") or {}).get("B_kmh_dynamic") or {}).get("decision")),
        "layer5_fpr": ((doc.get("current") or {}).get("layer5_fpr")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--baseline-drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tau0", type=float, default=0.05)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--tau-min", type=float, default=0.03)
    ap.add_argument("--tau-max", type=float, default=0.08)
    ap.add_argument("--start", type=float, default=-1.0)
    ap.add_argument("--stop", type=float, default=1.0)
    ap.add_argument("--step", type=float, default=0.2)
    args = ap.parse_args()

    if args.step <= 0:
        raise SystemExit("step must be > 0")

    tmp = ART / "_tmp_kmh_ab_sweep_latest.json"
    rows: list[dict[str, Any]] = []
    z = float(args.start)
    while z <= float(args.stop) + 1e-12:
        rows.append(
            _run_ab(
                args.human_signoff_json,
                args.baseline_drift_json,
                args.layer5_json,
                float(args.tau0),
                float(args.alpha),
                round(z, 10),
                float(args.tau_min),
                float(args.tau_max),
                tmp,
            )
        )
        z += float(args.step)

    valid = [r for r in rows if r.get("ok")]
    decision_changes = sum(
        1 for r in valid if (str(r.get("decision_a")) != str(r.get("decision_b")))
    )
    out = {
        "schema": "emotion_state_kmh_single_variable_sweep_v1",
        "generated_at_utc": _iso_now(),
        "params": {
            "tau0": float(args.tau0),
            "alpha": float(args.alpha),
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "start": float(args.start),
            "stop": float(args.stop),
            "step": float(args.step),
        },
        "summary": {
            "total_points": len(rows),
            "valid_points": len(valid),
            "decision_change_points": decision_changes,
        },
        "points": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if tmp.exists():
        tmp.unlink()
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "total_points": len(rows),
                "decision_change_points": decision_changes,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
