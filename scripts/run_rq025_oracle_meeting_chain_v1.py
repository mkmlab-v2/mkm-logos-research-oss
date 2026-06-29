#!/usr/bin/env python3
"""[HYPO] Oracle meeting one-click: discover → 3-arm → A/B summary → WTT deck appendix."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_rq025_upstream_intake_v1.py"
VALIDATE = ROOT / "scripts/validate_rq025_upstream_lambda_csv_v1.py"
DISCOVER = ROOT / "scripts/discover_rq025_upstream_csv_candidates_v1.py"
AUTO = ROOT / "scripts/run_rq025_upstream_csv_auto_resolve_and_three_arm_v1.py"
AB = ROOT / "scripts/build_rq025_lambda_ab_summary_v1.py"
DECK = ROOT / "scripts/build_wtt_stress_certified_deck_v1.py"
INTAKE_CSV = ROOT / "data/rq025/intake/upstream_lambda_certified.csv"


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}\n{proc.stdout}")
    if proc.stdout.strip():
        print(proc.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-discovery", action="store_true")
    ap.add_argument("--skip-three-arm", action="store_true")
    ap.add_argument("--skip-deck", action="store_true")
    args = ap.parse_args(argv)

    _run([sys.executable, str(BOOTSTRAP)])
    if INTAKE_CSV.is_file():
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), str(INTAKE_CSV)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise SystemExit(f"intake csv validation failed\n{proc.stderr}\n{proc.stdout}")
        if proc.stdout.strip():
            print(proc.stdout.strip())
    if not args.skip_discovery:
        _run([sys.executable, str(DISCOVER), "--validate-candidates"])
    if not args.skip_three_arm:
        _run([sys.executable, str(AUTO)])
    _run([sys.executable, str(AB)])
    if not args.skip_deck:
        _run([sys.executable, str(DECK), "--include-rq025-appendix"])
    print("OK: rq025 oracle meeting chain complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
