# -*- coding: utf-8 -*-
"""Smoke: optional ephemeris B-1 + mandatory B-2 cohort at exact_match_rate >= gate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_WS = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Manseryeok validation smoke (B-1 optional, B-2 required).")
    ap.add_argument(
        "--skip-ephemeris",
        action="store_true",
        help="Skip validate_ephemeris_baseline.py (requires pyswisseph + reference JSON)",
    )
    ap.add_argument(
        "--cohort",
        type=Path,
        default=_WS / "docs/final/artifacts/ganji_mapping_validate_cohort_v1.json",
    )
    ap.add_argument(
        "--reference-b",
        type=Path,
        default=_WS / "docs/final/artifacts/ephemeris_reference_b_lichun_stub_v1.json",
    )
    ap.add_argument(
        "--min-exact-rate",
        type=float,
        default=1.0,
        help="Exit 2 if B-2 aggregate exact_match_rate falls below this",
    )
    args = ap.parse_args()

    py = sys.executable

    if not args.skip_ephemeris:
        r = subprocess.run(
            [
                py,
                str(_WS / "scripts/validate_ephemeris_baseline.py"),
                "--reference-b-file",
                str(args.reference_b),
                "--output",
                str(_WS / "docs/final/artifacts/ephemeris_baseline_report_latest.json"),
            ],
            cwd=_WS,
        )
        if r.returncode != 0:
            return r.returncode

    if not args.cohort.exists():
        print(f"Cohort missing: {args.cohort} — run scripts/build_ganji_validation_cohort_v1.py", file=sys.stderr)
        return 1

    r2 = subprocess.run(
        [
            py,
            str(_WS / "scripts/validate_ganji_mapping.py"),
            "--input",
            str(args.cohort),
            "--output",
            str(_WS / "docs/final/artifacts/ganji_mapping_report_cohort_latest.json"),
            "--fail-exact-match-rate-below",
            str(args.min_exact_rate),
        ],
        cwd=_WS,
    )
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
