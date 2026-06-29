#!/usr/bin/env python3
"""P3 Root Generator full chain v0: build candidate → bench → gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_p3_root_candidate_lexicon_v1.py"
BENCH = ROOT / "scripts/run_p3_root_generator_bench_v1.py"
GATE = ROOT / "scripts/check_p3_root_generator_bench_gate_v1.py"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/p3_root_extension_probe_v1.jsonl"
DEFAULT_ALIAS = ROOT / "tests/fixtures/herbs_formulas_alias_table_minimal_v1.json"
BUILD_REPORT = ROOT / "reports/p3_root_candidate_lexicon_build_v1_latest.json"


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", default="v0_probe")
    ap.add_argument("--overlay-lexicon", action="append", default=[], type=Path)
    ap.add_argument("--extension-jsonl", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--alias-table", type=Path, default=DEFAULT_ALIAS)
    ap.add_argument("--skip-alias-table", action="store_true")
    ap.add_argument("--compression-sample", type=int, default=5)
    ap.add_argument("--include-pytest", action="store_true")
    args = ap.parse_args()

    build_cmd = [sys.executable, str(BUILD), "--slug", args.slug]
    for p in args.overlay_lexicon:
        build_cmd.extend(["--overlay-lexicon", str(p)])
    if args.extension_jsonl.is_file():
        build_cmd.extend(["--extension-jsonl", str(args.extension_jsonl)])
    if not args.skip_alias_table and args.alias_table.is_file():
        build_cmd.extend(["--alias-table", str(args.alias_table)])

    if _run(build_cmd) != 0:
        return 1

    if not BUILD_REPORT.is_file():
        print("ABORT: build report missing")
        return 1
    candidate = json.loads(BUILD_REPORT.read_text(encoding="utf-8")).get("candidate_path")
    if not candidate:
        print("ABORT: candidate_path missing from build report")
        return 1
    candidate_path = ROOT / str(candidate)

    bench_cmd = [
        sys.executable,
        str(BENCH),
        "--profile",
        "extension",
        "--candidate-lexicon",
        str(candidate_path),
        "--compression-sample",
        str(args.compression_sample),
    ]
    if _run(bench_cmd) != 0:
        return 1
    if _run([sys.executable, str(GATE)]) != 0:
        return 1
    if args.include_pytest:
        return _run([sys.executable, "-m", "pytest", "tests/test_p3_root_generator_bench_v1.py", "-q"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
