#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _parse_sigmas(s: str) -> list[float]:
    out = []
    for p in s.split(","):
        p = p.strip()
        if not p:
            continue
        out.append(float(p))
    if not out:
        raise ValueError("No sigma values provided.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Sigma grid sweep for formula contribution perturbation stability.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sigmas", type=str, default="0.01,0.02,0.03,0.05")
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_formula_contribution_sigma_grid_v1_latest.json",
    )
    ns = ap.parse_args()

    sigmas = _parse_sigmas(ns.sigmas)
    sweep_script = root / "scripts" / "run_agct_formula_contribution_perturbation_sweep_v1.py"
    work = root / "tmp" / "agct_formula_sigma_grid_v1"
    work.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, sigma in enumerate(sigmas):
        out = work / f"perturbation_sigma_{str(sigma).replace('.', '_')}.json"
        _run(
            [
                sys.executable,
                str(sweep_script),
                "--base-weights-json",
                str(ns.base_weights_json),
                "--trials",
                str(ns.trials),
                "--sigma",
                str(sigma),
                "--seed",
                str(ns.seed + i * 1000),
                "--output-json",
                str(out),
            ]
        )
        rep = json.loads(out.read_text(encoding="utf-8"))
        seg = rep.get("summary", {}).get("segment_rank_stability", {})
        rows.append(
            {
                "sigma": sigma,
                "report": str(out.resolve()),
                "segment_rank_stability": seg,
            }
        )

    threshold_summary = {}
    segment_names = ("full", "stress_tail", "recovery_stability")
    for sname in segment_names:
        first_flip_sigma = None
        base_dom = None
        for r in rows:
            dom = (r.get("segment_rank_stability", {}).get(sname, {}) or {}).get("dominant_component")
            if base_dom is None:
                base_dom = dom
            if dom != base_dom and first_flip_sigma is None:
                first_flip_sigma = r["sigma"]
        threshold_summary[sname] = {
            "baseline_dominant_component": base_dom,
            "first_dominant_flip_sigma": first_flip_sigma,
        }

    payload = {
        "schema": "agct_formula_contribution_sigma_grid_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "sigmas": sigmas,
            "trials": ns.trials,
            "seed": ns.seed,
            "base_weights_json": str(ns.base_weights_json.resolve()),
        },
        "rows": rows,
        "threshold_summary": threshold_summary,
        "notes": [
            "Dominant component flip threshold is a heuristic robustness indicator.",
            "B-track diagnostics only; not causal/clinical evidence.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} sigmas={len(sigmas)} trials={ns.trials}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
