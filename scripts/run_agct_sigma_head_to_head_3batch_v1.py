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


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if not xs:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser(description="Head-to-head sigma comparison with identical 3-batch seeds.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sigmas", type=str, default="0.0315,0.0325")
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--base-seed", type=int, default=20260505)
    ap.add_argument("--batch-gap", type=int, default=1000)
    ap.add_argument("--n-batches", type=int, default=3)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sigma_head_to_head_3batch_v1_latest.json",
    )
    ns = ap.parse_args()

    sigmas = [float(s.strip()) for s in ns.sigmas.split(",") if s.strip()]
    if len(sigmas) < 2:
        raise ValueError("Provide at least two sigma values.")

    repro_script = root / "scripts" / "run_agct_sigma_fixed_repro_3batch_v1.py"
    work = root / "tmp" / "agct_sigma_h2h_3batch_v1"
    work.mkdir(parents=True, exist_ok=True)

    rows = []
    for sigma in sigmas:
        print(f"[STEP] sigma={sigma}", flush=True)
        out = work / f"sigma_{str(sigma).replace('.', '_')}_repro.json"
        _run(
            [
                sys.executable,
                str(repro_script),
                "--sigma",
                str(sigma),
                "--trials",
                str(ns.trials),
                "--base-seed",
                str(ns.base_seed),
                "--batch-gap",
                str(ns.batch_gap),
                "--n-batches",
                str(ns.n_batches),
                "--output-json",
                str(out),
            ],
            root,
        )
        rep = _read_json(out)
        batches = rep.get("batches", [])
        go_rates = [float(b.get("go_rate", 0.0)) for b in batches]
        ti_vals = [float(b.get("transition_intensity", 0.0)) for b in batches]
        rows.append(
            {
                "sigma": sigma,
                "go_rate_mean": _mean(go_rates),
                "go_rate_std": _std(go_rates),
                "transition_intensity_mean": _mean(ti_vals),
                "transition_intensity_std": _std(ti_vals),
                "report": str(out.resolve()),
            }
        )

    # Priority: GO mean, then transition mean, then GO std lower.
    ranked = sorted(
        rows,
        key=lambda r: (
            -float(r["go_rate_mean"]),
            -float(r["transition_intensity_mean"]),
            float(r["go_rate_std"]),
        ),
    )
    winner = ranked[0] if ranked else None

    payload = {
        "schema": "agct_sigma_head_to_head_3batch_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "sigmas": sigmas,
            "trials": ns.trials,
            "base_seed": ns.base_seed,
            "batch_gap": ns.batch_gap,
            "n_batches": ns.n_batches,
        },
        "rows": rows,
        "ranking": ranked,
        "winner": {
            "sigma": (winner or {}).get("sigma"),
            "selection_rule": "maximize go_rate_mean, then transition_intensity_mean, then minimize go_rate_std",
        },
        "notes": [
            "Head-to-head comparison uses identical seed batches across candidates.",
            "B-track diagnostics only; no A-track/live authority.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} candidates={len(sigmas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
