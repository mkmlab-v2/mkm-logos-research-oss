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


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if not vals:
        return 0.0
    m = _mean(vals)
    return (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser(description="3-batch reproducibility pack for fixed sigma confirmation.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sigma", type=float, default=0.0315)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--base-seed", type=int, default=20260505)
    ap.add_argument("--batch-gap", type=int, default=1000)
    ap.add_argument("--n-batches", type=int, default=3)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sigma_fixed_repro_3batch_v1_latest.json",
    )
    ns = ap.parse_args()

    pack_script = root / "scripts" / "run_agct_sigma_fixed_confirmation_pack_v1.py"
    work = root / "tmp" / "agct_sigma_fixed_repro_3batch_v1"
    work.mkdir(parents=True, exist_ok=True)

    batch_rows = []
    go_rates: list[float] = []
    transitions: list[float] = []
    for i in range(ns.n_batches):
        seed = ns.base_seed + i * ns.batch_gap
        print(f"[STEP] batch={i+1}/{ns.n_batches} seed={seed}", flush=True)
        out = work / f"sigma_fixed_pack_batch_{i+1:02d}.json"
        _run(
            [
                sys.executable,
                str(pack_script),
                "--sigma",
                str(ns.sigma),
                "--trials",
                str(ns.trials),
                "--seed",
                str(seed),
                "--daily-seed",
                str(seed),
                "--drift-runs",
                "20",
                "--output-json",
                str(out),
            ],
            root,
        )
        rep = _read_json(out)
        fx = rep.get("fixed_sigma_scan", {})
        row = {
            "batch": i + 1,
            "seed": seed,
            "go_rate": float(fx.get("go_rate", 0.0)),
            "transition_intensity": float(fx.get("transition_intensity", 0.0)),
            "stress_tail_dominant_component": fx.get("stress_tail_dominant_component"),
            "stress_tail_dominant_share": float(fx.get("stress_tail_dominant_share", 0.0)),
            "report": str(out.resolve()),
        }
        batch_rows.append(row)
        go_rates.append(row["go_rate"])
        transitions.append(row["transition_intensity"])

    payload = {
        "schema": "agct_sigma_fixed_repro_3batch_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "sigma": ns.sigma,
            "trials": ns.trials,
            "base_seed": ns.base_seed,
            "batch_gap": ns.batch_gap,
            "n_batches": ns.n_batches,
        },
        "batches": batch_rows,
        "summary": {
            "go_rate_mean": _mean(go_rates),
            "go_rate_std": _std(go_rates),
            "transition_intensity_mean": _mean(transitions),
            "transition_intensity_std": _std(transitions),
        },
        "notes": [
            "Batch reproducibility evaluates seed sensitivity at fixed sigma.",
            "B-track diagnostics only; no A-track authority.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} batches={ns.n_batches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
