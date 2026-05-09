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
    ap = argparse.ArgumentParser(description="Run daily auto-recovery chain then refresh formula drift report.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--micro-sweep-radius", type=int, default=2)
    ap.add_argument("--drift-runs", type=int, default=20)
    ap.add_argument("--drift-start-seed", type=int, default=20260505)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_daily_formula_drift_chain_v1_latest.json",
    )
    ns = ap.parse_args()

    daily_script = root / "scripts" / "run_agct_daily_with_auto_recovery_v1.py"
    drift_script = root / "scripts" / "run_agct_sasang_formula_drift_report_v1.py"
    daily_report = root / "reports" / "agct_daily_auto_recovery_v1_latest.json"
    drift_report = root / "reports" / "agct_sasang_formula_drift_report_v1_latest.json"

    print("[STEP] daily_auto_recovery", flush=True)
    _run(
        [
            sys.executable,
            str(daily_script),
            "--seed",
            str(ns.seed),
            "--max-retries",
            str(ns.max_retries),
            "--micro-sweep-radius",
            str(ns.micro_sweep_radius),
        ],
        root,
    )

    print("[STEP] formula_drift_report", flush=True)
    _run(
        [
            sys.executable,
            str(drift_script),
            "--runs",
            str(ns.drift_runs),
            "--start-seed",
            str(ns.drift_start_seed),
        ],
        root,
    )

    daily = _read_json(daily_report)
    drift = _read_json(drift_report)
    payload = {
        "schema": "agct_daily_formula_drift_chain_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "seed": ns.seed,
            "max_retries": ns.max_retries,
            "micro_sweep_radius": ns.micro_sweep_radius,
            "drift_runs": ns.drift_runs,
            "drift_start_seed": ns.drift_start_seed,
        },
        "daily": {
            "decision_before": daily.get("before", {}).get("decision"),
            "decision_after": daily.get("after", {}).get("decision"),
            "recovered": bool(daily.get("recovery_executed", False)),
            "best_candidate_source": daily.get("best_candidate_source"),
            "daily_report": str(daily_report.resolve()),
        },
        "drift": {
            "n_runs": drift.get("summary", {}).get("n_runs"),
            "segments": drift.get("summary", {}).get("segments", {}),
            "drift_report": str(drift_report.resolve()),
        },
        "notes": [
            "Operational B-track chain only.",
            "No A-track/live trading authority is implied.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
