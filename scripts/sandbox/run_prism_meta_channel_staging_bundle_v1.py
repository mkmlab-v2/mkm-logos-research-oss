#!/usr/bin/env python3
"""[HYPO] One-shot: wire bench → archive strict → staging readiness."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prism meta channel staging bundle.")
    ap.add_argument("--skip-wire-bench", action="store_true")
    ap.add_argument("--skip-archive", action="store_true")
    ap.add_argument("--run-pytest", action="store_true")
    ap.add_argument("--require-staging-enable", action="store_true")
    ap.add_argument("--live-smoke", action="store_true", help="Run env=ON live smoke after readiness pass")
    ap.add_argument("--live-smoke-max-cases", type=int, default=5)
    args = ap.parse_args()

    py = sys.executable
    if not args.skip_wire_bench:
        rc = _run([py, str(ROOT / "scripts/sandbox/run_prism_proxy_meta_wire_bench_v1.py")])
        if rc != 0:
            return rc

    if not args.skip_archive:
        rc = _run(
            [
                py,
                str(ROOT / "scripts/sandbox/build_archive_limitless_trilogy_report_v1.py"),
                "--strict",
                "--require-phase2",
            ]
        )
        if rc != 0:
            return rc

    cmd = [
        py,
        str(ROOT / "scripts/sandbox/check_prism_meta_channel_staging_readiness_v1.py"),
        "--strict",
    ]
    if args.run_pytest:
        cmd.append("--run-pytest")
    if args.require_staging_enable:
        cmd.append("--require-staging-enable")
    rc = _run(cmd)
    if rc != 0:
        return rc

    if args.live_smoke:
        live_cmd = [
            py,
            str(ROOT / "scripts/sandbox/run_prism_meta_channel_staging_live_smoke_v1.py"),
            "--strict",
            "--max-cases",
            str(max(1, int(args.live_smoke_max_cases))),
        ]
        return _run(live_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
