#!/usr/bin/env python3
"""One-click P3-Root-Generator bench + gate (+ optional pytest)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "scripts/run_p3_root_generator_bench_v1.py"
GATE = ROOT / "scripts/check_p3_root_generator_bench_gate_v1.py"


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="Baseline-only smoke (default path)")
    ap.add_argument("--candidate-lexicon", type=Path, default=None)
    ap.add_argument("--profile", choices=("extension", "replacement"), default="extension")
    ap.add_argument("--include-pytest", action="store_true")
    args = ap.parse_args()

    bench_cmd = [sys.executable, str(BENCH), "--profile", args.profile]
    if args.candidate_lexicon is not None:
        bench_cmd.extend(["--candidate-lexicon", str(args.candidate_lexicon)])
    if _run(bench_cmd) != 0:
        return 1
    if _run([sys.executable, str(GATE)]) != 0:
        return 1
    if args.include_pytest:
        return _run([sys.executable, "-m", "pytest", "tests/test_p3_root_generator_bench_v1.py", "-q"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
