#!/usr/bin/env python3
"""L1-A Design fuse chain — 4D RAG inference graph overlay + showroom slice + fuse gate."""

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
    parser.add_argument("--skip-fuse-base", action="store_true")
    args = parser.parse_args()

    steps: list[list[str]] = [
        [sys.executable, "scripts/build_logos_oracle_inference_graph_overlay_v1.py"],
        [sys.executable, "scripts/build_showroom_meaning_topology_graph_slice_v1.py"],
    ]
    if not args.skip_fuse_base:
        steps.insert(0, [sys.executable, "scripts/check_logos_theory_implementation_wiring_v1.py"])

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
                "tests/test_build_logos_oracle_inference_graph_overlay_v1.py",
                "tests/test_build_showroom_meaning_topology_graph_slice_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest L1-A overlay + showroom slice")

    if not args.skip_fuse_base and not args.skip_mkmlife_build:
        fuse = subprocess.run(
            [
                sys.executable,
                "scripts/run_logos_oracle_design_fuse_chain_v1.py",
                "--skip-pytest",
            ],
            cwd=ROOT,
            check=False,
        )
        if fuse.returncode != 0:
            return fuse.returncode
        print("OK: design fuse chain (wiring + bloom + mkmlife build)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
