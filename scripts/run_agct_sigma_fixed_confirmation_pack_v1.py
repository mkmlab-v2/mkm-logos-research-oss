#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> None:
    t0 = time.perf_counter()
    print(f"[RUN] {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=False, text=True, check=False)
    dt = time.perf_counter() - t0
    if r.returncode != 0:
        raise RuntimeError(f"step_failed returncode={r.returncode} elapsed_sec={dt:.1f}")
    print(f"[DONE] elapsed_sec={dt:.1f}", flush=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Fixed-sigma confirmation pack (stress-tail transition + daily chain).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sigma", type=float, default=0.0315)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--daily-seed", type=int, default=20260505)
    ap.add_argument("--drift-runs", type=int, default=20)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sigma_fixed_confirmation_pack_v1_latest.json",
    )
    ns = ap.parse_args()

    scan_script = root / "scripts" / "run_agct_stress_tail_transition_gate_scan_v1.py"
    daily_drift_script = root / "scripts" / "run_agct_daily_formula_drift_chain_v1.py"
    scan_out = root / "reports" / "agct_stress_tail_transition_gate_scan_v1_fixed_latest.json"
    daily_out = root / "reports" / "agct_daily_formula_drift_chain_v1_latest.json"

    print("[STEP] stress_tail_transition_scan", flush=True)
    _run(
        [
            sys.executable,
            str(scan_script),
            "--sigmas",
            str(ns.sigma),
            "--trials",
            str(ns.trials),
            "--seed",
            str(ns.seed),
            "--output-json",
            str(scan_out),
        ],
        root,
    )

    print("[STEP] daily_formula_drift_chain", flush=True)
    _run(
        [
            sys.executable,
            str(daily_drift_script),
            "--seed",
            str(ns.daily_seed),
            "--drift-runs",
            str(ns.drift_runs),
            "--drift-start-seed",
            str(ns.seed),
        ],
        root,
    )

    scan = _read_json(scan_out)
    daily = _read_json(daily_out)
    row = (scan.get("rows") or [{}])[0]

    payload = {
        "schema": "agct_sigma_fixed_confirmation_pack_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "sigma": ns.sigma,
            "trials": ns.trials,
            "seed": ns.seed,
            "daily_seed": ns.daily_seed,
            "drift_runs": ns.drift_runs,
        },
        "fixed_sigma_scan": {
            "sigma": row.get("sigma"),
            "stress_tail_top_component_frequency": row.get("stress_tail_top_component_frequency", {}),
            "stress_tail_dominant_component": row.get("stress_tail_dominant_component"),
            "stress_tail_dominant_share": row.get("stress_tail_dominant_share"),
            "go_rate": row.get("go_rate"),
            "transition_intensity": row.get("transition_intensity"),
            "report": str(scan_out.resolve()),
        },
        "daily_chain": {
            "decision_before": daily.get("daily", {}).get("decision_before"),
            "decision_after": daily.get("daily", {}).get("decision_after"),
            "recovered": daily.get("daily", {}).get("recovered"),
            "best_candidate_source": daily.get("daily", {}).get("best_candidate_source"),
            "report": str(daily_out.resolve()),
        },
        "notes": [
            "Fixed-sigma confirmation pack is B-track diagnostics only.",
            "No A-track/live deployment authority is implied.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
