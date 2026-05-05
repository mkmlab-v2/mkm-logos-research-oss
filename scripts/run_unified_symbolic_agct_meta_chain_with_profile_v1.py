#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.9, K:0.66, M:0.49}
# Balance: 90
# Purpose: Run unified meta chain using predefined gate profile.
# Keywords: unified, profile, gate, agct, symbolic
"""Run unified symbolic+AGCT meta chain with named profile."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run unified meta chain with gate profile.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-input-csv", type=Path, required=True)
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument(
        "--profile-json",
        type=Path,
        default=Path("docs/final/artifacts/unified_meta_gate_profiles_v1.json"),
    )
    ap.add_argument("--profile", type=str, default="neutral", choices=["conservative", "neutral", "aggressive"])
    ap.add_argument("--runtime-enabled", action="store_true")
    ap.add_argument("--permutation-repeats", type=int, default=2000)
    ns = ap.parse_args()

    profiles = _load_json(ns.profile_json).get("profiles", {})
    p = profiles.get(ns.profile)
    if not isinstance(p, dict):
        raise SystemExit(f"missing profile: {ns.profile}")

    chain = Path(__file__).resolve().parents[1] / "scripts" / "run_unified_symbolic_agct_meta_chain_v1.py"
    cmd = [
        sys.executable,
        str(chain),
        "--cohort-csv",
        str(ns.cohort_csv),
        "--genotype-input-csv",
        str(ns.genotype_input_csv),
        "--mapping-coverage-report",
        str(ns.mapping_coverage_report),
        "--permutation-repeats",
        str(ns.permutation_repeats),
        "--min-holdout-n",
        str(int(p["min_holdout_n"])),
        "--min-holdout-accuracy",
        str(float(p["min_holdout_accuracy"])),
        "--max-generalization-gap",
        str(float(p["max_generalization_gap"])),
        "--max-holdout-pvalue",
        str(float(p["max_holdout_pvalue"])),
        "--symbolic-max-mean-loss",
        str(float(p["symbolic_max_mean_loss"])),
        "--symbolic-max-drift",
        str(float(p["symbolic_max_drift"])),
    ]
    if ns.runtime_enabled:
        cmd.append("--runtime-enabled")

    print("RUN[profile_chain] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, check=False)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
