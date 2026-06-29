#!/usr/bin/env python3
"""Chain: fusion (if needed) → parallel advisory brief."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run MKM parallel advisory chain v1")
    ap.add_argument("--domain", default="finance")
    ap.add_argument("--session-date", default=None)
    ap.add_argument("--exclude-lens", action="append", default=[], dest="exclude_lenses")
    ap.add_argument("--skip-fusion", action="store_true")
    args = ap.parse_args()

    if not args.skip_fusion:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_kospi_four_lens_graphrag_fusion_v1.py")],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            return r.returncode

    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_mkm_parallel_advisory_brief_v1.py"),
        "--domain",
        args.domain,
        "--skip-fusion-build",
    ]
    if args.session_date:
        cmd.extend(["--session-date", args.session_date])
    for ex in args.exclude_lenses:
        cmd.extend(["--exclude-lens", ex])

    return subprocess.run(cmd, cwd=str(ROOT)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
