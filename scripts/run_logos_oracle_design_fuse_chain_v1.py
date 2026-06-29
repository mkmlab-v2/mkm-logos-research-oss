#!/usr/bin/env python3
"""Oracle+Design fuse chain — graph bloom slice + mkmlife build smoke."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-mkmlife-build", action="store_true")
    args = parser.parse_args()

    steps = [
        [sys.executable, "scripts/check_logos_theory_implementation_wiring_v1.py"],
        [sys.executable, "scripts/run_logos_dynamic_tuning_chain_v1.py"],
        [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bloom_slice_v1.py"],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {' '.join(cmd[1:])} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {cmd[1]}")

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_mkmlife_cosmic_anchor_graph_bloom_bridge_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest graph bloom bridge")

    if not args.skip_mkmlife_build:
        mkmlife = ROOT / "projects/mkm/mkm-life"
        proc = subprocess.run(["npm", "run", "build"], cwd=mkmlife, check=False, shell=True)
        if proc.returncode != 0:
            print("FAIL: npm run build (mkmlife)", file=sys.stderr)
            return proc.returncode
        print("OK: mkmlife npm run build")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
