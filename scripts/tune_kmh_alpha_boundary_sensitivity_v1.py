#!/usr/bin/env python3
"""Tune alpha by maximizing boundary decision-change sensitivity."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "emotion_state_kmh_alpha_tuning_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frange(start: float, stop: float, step: float) -> list[float]:
    vals: list[float] = []
    x = start
    while x <= stop + 1e-12:
        vals.append(round(x, 10))
        x += step
    return vals


def _run_boundary(alpha: float, tau0: float, tau_min: float, tau_max: float) -> dict[str, Any]:
    out_json = ART / f"_tmp_kmh_boundary_alpha_{str(alpha).replace('.', 'p')}.json"
    cmd = [
        "py",
        str(ROOT / "scripts" / "run_kmh_single_variable_boundary_sweep_v1.py"),
        "--tau0",
        str(tau0),
        "--alpha",
        str(alpha),
        "--tau-min",
        str(tau_min),
        "--tau-max",
        str(tau_max),
        "--z-start",
        "-1.0",
        "--z-stop",
        "1.0",
        "--z-step",
        "0.2",
        "--fpr-start",
        "0.04",
        "--fpr-stop",
        "0.06",
        "--fpr-step",
        "0.002",
        "--output-json",
        str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"alpha": alpha, "ok": False, "error": proc.stdout + proc.stderr}
    try:
        doc = json.loads(out_json.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover
        return {"alpha": alpha, "ok": False, "error": str(exc)}
    finally:
        if out_json.exists():
            out_json.unlink()
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    return {
        "alpha": alpha,
        "ok": True,
        "decision_change_points": int(summary.get("decision_change_points") or 0),
        "total_points": int(summary.get("total_points") or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tau0", type=float, default=0.05)
    ap.add_argument("--tau-min", type=float, default=0.03)
    ap.add_argument("--tau-max", type=float, default=0.08)
    ap.add_argument("--alpha-start", type=float, default=0.005)
    ap.add_argument("--alpha-stop", type=float, default=0.03)
    ap.add_argument("--alpha-step", type=float, default=0.005)
    ap.add_argument("--baseline-alpha", type=float, default=0.01)
    args = ap.parse_args()

    alphas = _frange(args.alpha_start, args.alpha_stop, args.alpha_step)
    rows = [_run_boundary(a, args.tau0, args.tau_min, args.tau_max) for a in alphas]
    valid = [r for r in rows if r.get("ok")]
    if not valid:
        raise SystemExit("no valid alpha runs")

    best = max(valid, key=lambda r: int(r.get("decision_change_points") or 0))
    baseline = next((r for r in valid if abs(float(r["alpha"]) - float(args.baseline_alpha)) < 1e-12), None)
    uplift = None
    if baseline is not None:
        uplift = int(best["decision_change_points"]) - int(baseline["decision_change_points"])

    out = {
        "schema": "emotion_state_kmh_alpha_tuning_v1",
        "generated_at_utc": _iso_now(),
        "params": {
            "tau0": float(args.tau0),
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "alpha_start": float(args.alpha_start),
            "alpha_stop": float(args.alpha_stop),
            "alpha_step": float(args.alpha_step),
            "baseline_alpha": float(args.baseline_alpha),
        },
        "results": rows,
        "best": best,
        "baseline": baseline,
        "uplift_vs_baseline_change_points": uplift,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "best_alpha": best["alpha"], "uplift": uplift}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
