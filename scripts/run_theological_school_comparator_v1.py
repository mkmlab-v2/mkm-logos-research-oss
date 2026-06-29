#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI entry: anchor in -> comparative theology panorama out (curated seeds, no live LLM)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "docs/final/artifacts/comparative_theology_seeds/job_1_6_satan_v1.json"
BUILDER = ROOT / "scripts/build_comparative_theology_panorama_v1.py"

ANCHOR_TO_SEED = {
    "Job.1.6": DEFAULT_SEED,
    "job.1.6": DEFAULT_SEED,
    "욥기 1:6": DEFAULT_SEED,
    "Job.2.3": ROOT / "docs/final/artifacts/comparative_theology_seeds/job_2_3_blameless_permission_v1.json",
    "job.2.3": ROOT / "docs/final/artifacts/comparative_theology_seeds/job_2_3_blameless_permission_v1.json",
    "욥기 2:3": ROOT / "docs/final/artifacts/comparative_theology_seeds/job_2_3_blameless_permission_v1.json",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Theological school comparator v1 (curated panorama).")
    ap.add_argument("--anchor", type=str, default="Job.1.6", help="Canon anchor ref")
    ap.add_argument("--seed-json", type=Path, default=None)
    ap.add_argument("--out-artifact", type=Path, default=None)
    args = ap.parse_args()

    seed = args.seed_json
    if seed is None:
        seed = ANCHOR_TO_SEED.get(args.anchor.strip(), DEFAULT_SEED)
    seed = seed if seed.is_absolute() else ROOT / seed

    cmd = [sys.executable, str(BUILDER), "--seed-json", str(seed)]
    if args.out_artifact:
        out = args.out_artifact if args.out_artifact.is_absolute() else ROOT / args.out_artifact
        cmd.extend(["--out-artifact", str(out)])

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    print(proc.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
