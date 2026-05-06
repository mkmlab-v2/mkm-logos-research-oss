#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROFILES = ("conservative", "neutral", "aggressive")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-profile adversarial robustness grid.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--n-samples", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--noise-grid", type=str, default="0.1,0.2,0.35,0.5,0.7")
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_adversarial_profile_grid_v1_latest.json")
    ns = ap.parse_args()

    sweep_script = root / "scripts" / "run_agct_adversarial_robustness_sweep_v1.py"
    # Isolate profile sweep outputs per invocation to avoid cross-run file clobbering.
    run_id = uuid.uuid4().hex[:12]
    run_work = root / "tmp" / "agct_adversarial_profile_grid_v1" / f"run_{run_id}"
    run_work.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, p in enumerate(PROFILES):
        out = run_work / f"agct_adversarial_robustness_{p}.json"
        _run(
            [
                sys.executable,
                str(sweep_script),
                "--weights-json",
                str(ns.weights_json),
                "--n-samples",
                str(ns.n_samples),
                "--seed",
                str(ns.seed + i * 1000),
                "--noise-grid",
                ns.noise_grid,
                "--prior-profile",
                p,
                "--output-json",
                str(out),
            ]
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        s = data["summary"]
        rows.append(
            {
                "prior_profile": p,
                "robustness_score": _safe_float(s.get("robustness_score")),
                "worst_case_accuracy": _safe_float(s.get("worst_case_accuracy")),
                "worst_case_risk_corr": _safe_float(s.get("worst_case_risk_corr")),
                "n_valid_levels": int(s.get("n_valid_levels") or 0),
                "n_failed_levels": int(s.get("n_failed_levels") or 0),
                "report": str(out.resolve()),
            }
        )

    avg_rob = sum(r["robustness_score"] for r in rows) / len(rows) if rows else 0.0
    payload = {
        "schema": "agct_adversarial_profile_grid_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "weights_json": str(ns.weights_json.resolve()),
            "profiles": list(PROFILES),
            "noise_grid": ns.noise_grid,
            "n_samples": ns.n_samples,
            "run_work_dir": str(run_work.resolve()),
        },
        "summary": {
            "avg_robustness_score": avg_rob,
            "worst_profile_by_robustness": min(rows, key=lambda x: x["robustness_score"])["prior_profile"] if rows else None,
            "worst_case_accuracy_global": min(r["worst_case_accuracy"] for r in rows) if rows else None,
            "worst_case_risk_corr_global": min(r["worst_case_risk_corr"] for r in rows) if rows else None,
        },
        "profiles": rows,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} avg_robustness={avg_rob:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
